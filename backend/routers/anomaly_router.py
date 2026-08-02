from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Anomaly, AnomalyFlowRecord, GuideSign, User
from auth import get_current_user
from schemas import (
    AnomalyCreate, AnomalyUpdate, AnomalyResponse,
    AnomalyProcessRequest, AnomalyFlowRecordResponse
)
from routers.sign_router import _build_flow_digest

router = APIRouter(prefix="/api/anomalies", tags=["偏差闭环核销"])

ANOMALY_STATUS = {
    "pending": "待现场核查",
    "processing": "核查中",
    "pending_confirm": "待复核确认",
    "closed": "已核销闭环"
}

ANOMALY_TYPES = {
    "lost": "离场缺失",
    "damaged": "版面破损",
    "wrong_issue": "座区错配",
    "overdue": "散场超时未回收",
    "other": "其他"
}

ANOMALY_LEVELS = {
    "low": "低",
    "normal": "一般",
    "high": "高",
    "critical": "严重"
}

ACTIVE_ANOMALY_STATUSES = ("pending", "processing", "pending_confirm")


def _sync_trace_consistency(sign: GuideSign, db: Session):
    if not sign:
        return
    trace_code = (sign.trace_code or "").strip()
    affected_signs = [sign]
    if trace_code:
        affected_signs = db.query(GuideSign).filter(
            GuideSign.trace_code == trace_code
        ).all()

    active_sign_ids = [s.id for s in affected_signs]
    active_count = 0
    if active_sign_ids:
        active_count = db.query(func.count(Anomaly.id)).filter(
            Anomaly.sign_id.in_(active_sign_ids),
            Anomaly.current_status.in_(ACTIVE_ANOMALY_STATUSES)
        ).scalar() or 0

    new_state = "warn" if active_count > 0 else "ok"
    for affected in affected_signs:
        affected.consistency_state = new_state
        affected.flow_digest = _build_flow_digest(affected, db)


@router.get("", response_model=List[AnomalyResponse])
def list_anomalies(
    current_status: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    anomaly_level: Optional[str] = None,
    session: Optional[str] = None,
    responsible_person: Optional[str] = None,
    reporter: Optional[str] = None,
    trace_code: Optional[str] = None,
    keyword: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Anomaly).join(GuideSign)

    if current_status:
        query = query.filter(Anomaly.current_status == current_status)
    if anomaly_type:
        query = query.filter(Anomaly.anomaly_type == anomaly_type)
    if anomaly_level:
        query = query.filter(Anomaly.anomaly_level == anomaly_level)
    if session:
        query = query.filter(Anomaly.session.contains(session))
    if responsible_person:
        query = query.filter(Anomaly.responsible_person.contains(responsible_person))
    if reporter:
        query = query.filter(Anomaly.reporter.contains(reporter))
    if trace_code:
        query = query.filter(
            (Anomaly.trace_code.contains(trace_code)) |
            (GuideSign.trace_code.contains(trace_code))
        )
    if keyword:
        query = query.filter(
            GuideSign.sign_number.contains(keyword) |
            Anomaly.description.contains(keyword)
        )

    anomalies = query.order_by(Anomaly.created_at.desc()).offset(skip).limit(limit).all()
    return anomalies


@router.get("/{anomaly_id}", response_model=AnomalyResponse)
def get_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="偏差记录不存在")
    return anomaly


@router.post("", response_model=AnomalyResponse)
def create_anomaly(
    anomaly_data: AnomalyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == anomaly_data.sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")

    payload = anomaly_data.model_dump()
    payload["trace_code"] = (payload.get("trace_code") or sign.trace_code or "").strip()
    payload["scene_scope"] = payload.get("scene_scope") or sign.scene_scope or "private"
    payload["risk_level"] = payload.get("risk_level") or sign.risk_level or "green"
    payload["handover_note"] = payload.get("handover_note") or sign.handover_note or ""

    anomaly = Anomaly(**payload)
    anomaly.current_status = "pending"

    if not anomaly.session and sign.applicable_session:
        anomaly.session = sign.applicable_session

    flow_record = AnomalyFlowRecord(
        action="register",
        operator=anomaly_data.reporter,
        remark="偏差登记：" + (anomaly_data.description or ""),
        from_status=None,
        to_status="pending"
    )
    anomaly.flow_records.append(flow_record)

    sign._original_status = sign.status
    if anomaly_data.anomaly_type == "lost":
        sign.status = "deactivated"
        flow_record.remark += "；导引位标状态已联动变更为隔离停用"
    elif anomaly_data.anomaly_type == "damaged":
        sign.status = "pending_review"
        flow_record.remark += "；导引位标状态已联动变更为待防错复核"
    elif anomaly_data.anomaly_type == "overdue":
        if sign.status not in ["pending_review", "deactivated"]:
            sign.status = "pending_recycle"
            flow_record.remark += "；导引位标状态已联动变更为待回收核验"

    db.add(anomaly)
    db.flush()

    _sync_trace_consistency(sign, db)

    db.commit()
    db.refresh(anomaly)
    return anomaly


@router.put("/{anomaly_id}", response_model=AnomalyResponse)
def update_anomaly(
    anomaly_id: int,
    anomaly_data: AnomalyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="偏差记录不存在")
    if anomaly.current_status == "closed":
        raise HTTPException(status_code=400, detail="已核销闭环的偏差不能修改")
    
    update_data = anomaly_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(anomaly, key, value)
    
    db.commit()
    db.refresh(anomaly)
    return anomaly


@router.post("/{anomaly_id}/process", response_model=AnomalyResponse)
def process_anomaly(
    anomaly_id: int,
    request: AnomalyProcessRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="偏差记录不存在")
    
    action = request.action
    from_status = anomaly.current_status
    to_status = None
    sign = db.query(GuideSign).filter(GuideSign.id == anomaly.sign_id).first()
    
    if action == "reopen":
        if from_status != "closed":
            raise HTTPException(status_code=400, detail="只有已核销闭环状态才能重新纳入核查")
        to_status = "processing"
        anomaly.closed_at = None
        anomaly.final_result = ""
        if sign:
            if anomaly.anomaly_type == "lost":
                if sign.status == "deactivated":
                    sign.status = "available"
            elif anomaly.anomaly_type == "damaged":
                if sign.status == "deactivated":
                    sign.status = "available"
    else:
        if anomaly.current_status == "closed":
            raise HTTPException(status_code=400, detail="已核销闭环的偏差不能继续核查，请选择重新纳入核查")
        
        if action == "start_process":
            if from_status not in ["pending", "pending_confirm"]:
                raise HTTPException(status_code=400, detail="当前状态不能开始现场核查")
            to_status = "processing"
        elif action == "submit_confirm":
            if from_status != "processing":
                raise HTTPException(status_code=400, detail="只有核查中状态才能提交复核确认")
            to_status = "pending_confirm"
        elif action == "confirm_close":
            if from_status != "pending_confirm":
                raise HTTPException(status_code=400, detail="只有待复核确认状态才能核销闭环")
            to_status = "closed"
            anomaly.closed_at = datetime.now()
            anomaly.final_result = request.remark
            if sign:
                other_active = db.query(Anomaly).filter(
                    Anomaly.sign_id == sign.id,
                    Anomaly.id != anomaly.id,
                    Anomaly.current_status.in_(["pending", "processing", "pending_confirm"])
                ).count()
                if other_active == 0:
                    if anomaly.anomaly_type == "lost":
                        pass
                    elif anomaly.anomaly_type == "damaged":
                        if sign.status == "pending_review":
                            sign.status = "available"
                    elif anomaly.anomaly_type == "overdue":
                        if sign.status == "pending_recycle":
                            sign.status = "available"
                    elif anomaly.anomaly_type == "wrong_issue":
                        if sign.status not in ["deactivated", "pending_review"]:
                            sign.status = "available"
                    else:
                        if sign.status not in ["deactivated"]:
                            sign.status = "available"
        elif action == "reject":
            if from_status != "pending_confirm":
                raise HTTPException(status_code=400, detail="只有待复核确认状态才能退回复查")
            to_status = "processing"
        elif action == "add_remark":
            to_status = from_status
        else:
            raise HTTPException(status_code=400, detail="无效的操作类型")
    
    if to_status and to_status != from_status:
        anomaly.current_status = to_status

    flow_record = AnomalyFlowRecord(
        anomaly_id=anomaly.id,
        action=action,
        operator=request.operator,
        remark=request.remark,
        from_status=from_status,
        to_status=to_status
    )
    db.add(flow_record)
    db.flush()

    if sign:
        _sync_trace_consistency(sign, db)

    db.commit()
    db.refresh(anomaly)
    return anomaly


@router.get("/{anomaly_id}/flows", response_model=List[AnomalyFlowRecordResponse])
def get_anomaly_flows(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="偏差记录不存在")
    
    flows = db.query(AnomalyFlowRecord).filter(
        AnomalyFlowRecord.anomaly_id == anomaly_id
    ).order_by(AnomalyFlowRecord.created_at.asc()).all()
    return flows


@router.delete("/{anomaly_id}")
def delete_anomaly(
    anomaly_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    anomaly = db.query(Anomaly).filter(Anomaly.id == anomaly_id).first()
    if not anomaly:
        raise HTTPException(status_code=404, detail="偏差记录不存在")
    
    db.delete(anomaly)
    db.commit()
    return {"message": "删除成功"}


@router.get("/stats/summary")
def get_anomaly_stats_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total = db.query(Anomaly).count()
    pending = db.query(Anomaly).filter(Anomaly.current_status == "pending").count()
    processing = db.query(Anomaly).filter(Anomaly.current_status == "processing").count()
    pending_confirm = db.query(Anomaly).filter(Anomaly.current_status == "pending_confirm").count()
    closed = db.query(Anomaly).filter(Anomaly.current_status == "closed").count()
    
    type_stats = db.query(
        Anomaly.anomaly_type,
        func.count(Anomaly.id).label("count")
    ).filter(
        Anomaly.current_status.in_(["pending", "processing", "pending_confirm"])
    ).group_by(Anomaly.anomaly_type).all()
    
    return {
        "total": total,
        "pending": pending,
        "processing": processing,
        "pending_confirm": pending_confirm,
        "closed": closed,
        "total_active": pending + processing + pending_confirm,
        "type_stats": [
            {"anomaly_type": t, "count": c} for t, c in type_stats
        ]
    }
