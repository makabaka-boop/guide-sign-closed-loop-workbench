from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import GuideSign, PositionRecord, IssueRecord, ReviewRecord, User, Anomaly
from auth import get_current_user
from schemas import (
    GuideSignCreate, GuideSignUpdate, GuideSignResponse,
    IssueSignRequest, RecycleSignRequest, PositionAdjustRequest, ReviewRequest
)
from routers.anomaly_router import append_flow_digest

router = APIRouter(prefix="/api/signs", tags=["导引位标"])

STATUS_MAP = {
    "pending_production": "待印制校样",
    "available": "待投放",
    "issued": "已投放",
    "pending_recycle": "待回收核验",
    "pending_review": "待防错复核",
    "restored": "复核后可投放",
    "deactivated": "隔离停用"
}


def enrich_sign_with_anomaly(sign: GuideSign, db: Session) -> GuideSign:
    active_anomalies = db.query(Anomaly).filter(
        Anomaly.sign_id == sign.id,
        Anomaly.current_status.in_(["pending", "processing", "pending_confirm"])
    ).all()
    
    sign.has_active_anomaly = len(active_anomalies) > 0
    sign.active_anomaly_count = len(active_anomalies)
    sign.active_anomaly_types = [a.anomaly_type for a in active_anomalies]
    
    return sign


@router.get("", response_model=List[GuideSignResponse])
def list_signs(
    status: Optional[str] = None,
    batch_code: Optional[str] = None,
    applicable_session: Optional[str] = None,
    responsible_person: Optional[str] = None,
    keyword: Optional[str] = None,
    trace_code: Optional[str] = None,
    scene_scope: Optional[str] = None,
    risk_level: Optional[str] = None,
    consistency_state: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(GuideSign)
    
    if status:
        query = query.filter(GuideSign.status == status)
    if batch_code:
        query = query.filter(GuideSign.batch_code.contains(batch_code))
    if applicable_session:
        query = query.filter(GuideSign.applicable_session.contains(applicable_session))
    if responsible_person:
        query = query.filter(GuideSign.responsible_person.contains(responsible_person))
    if keyword:
        query = query.filter(
            GuideSign.sign_number.contains(keyword) |
            GuideSign.current_area.contains(keyword)
        )
    if trace_code:
        query = query.filter(GuideSign.trace_code.contains(trace_code))
    if scene_scope:
        query = query.filter(GuideSign.scene_scope == scene_scope)
    if risk_level:
        query = query.filter(GuideSign.risk_level == risk_level)
    if consistency_state:
        query = query.filter(GuideSign.consistency_state == consistency_state)
    
    signs = query.order_by(GuideSign.id.desc()).offset(skip).limit(limit).all()
    for sign in signs:
        enrich_sign_with_anomaly(sign, db)
    return signs


@router.get("/{sign_id}", response_model=GuideSignResponse)
def get_sign(
    sign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    enrich_sign_with_anomaly(sign, db)
    return sign


@router.post("", response_model=GuideSignResponse)
def create_sign(
    sign_data: GuideSignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    existing = db.query(GuideSign).filter(GuideSign.sign_number == sign_data.sign_number).first()
    if existing:
        raise HTTPException(status_code=400, detail="位标编号已存在")
    
    sign = GuideSign(**sign_data.model_dump())
    db.add(sign)
    db.commit()
    db.refresh(sign)
    return sign


@router.put("/{sign_id}", response_model=GuideSignResponse)
def update_sign(
    sign_id: int,
    sign_data: GuideSignUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    
    update_data = sign_data.model_dump(exclude_unset=True)
    
    old_area = sign.current_area
    new_area = update_data.get("current_area")
    
    for key, value in update_data.items():
        setattr(sign, key, value)
    
    if new_area is not None and old_area != new_area:
        position_record = PositionRecord(
            sign_id=sign.id,
            from_area=old_area,
            to_area=new_area,
            operator=current_user.full_name or current_user.username,
            reason="编辑修改目标座区"
        )
        db.add(position_record)
    
    db.commit()
    db.refresh(sign)
    return sign


@router.delete("/{sign_id}")
def delete_sign(
    sign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    db.delete(sign)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{sign_id}/status/available", response_model=GuideSignResponse)
def mark_available(
    sign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.status not in ["pending_production", "deactivated"]:
        raise HTTPException(status_code=400, detail="当前状态不可设为待投放")
    
    sign.status = "available"
    db.commit()
    db.refresh(sign)
    return sign


@router.post("/{sign_id}/issue", response_model=GuideSignResponse)
def issue_sign(
    sign_id: int,
    request: IssueSignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.status not in ["available", "restored"]:
        raise HTTPException(status_code=400, detail="当前状态不可投放")
    
    sign.status = "issued"

    # 投放记录摘要并入批次交接备注
    remark_summary = request.remark or ""
    if sign.handover_note:
        remark_summary = f"{remark_summary}；交接备注：{sign.handover_note}" if remark_summary else f"交接备注：{sign.handover_note}"

    issue_record = IssueRecord(
        sign_id=sign.id,
        issue_type="issue",
        session=request.session,
        operator=request.operator,
        receiver=request.receiver,
        remark=remark_summary
    )
    db.add(issue_record)

    # 后端维护链路流转摘要，前端无需拼接历史文本
    digest_segment = f"{datetime.now().strftime('%Y-%m-%d %H:%M')} 投放至{request.session}，接场人{request.receiver}，执行人{request.operator}"
    sign.flow_digest = f"{sign.flow_digest}；{digest_segment}" if sign.flow_digest else digest_segment

    db.commit()
    db.refresh(sign)
    return sign


@router.post("/{sign_id}/pending-recycle", response_model=GuideSignResponse)
def mark_pending_recycle(
    sign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.status != "issued":
        raise HTTPException(status_code=400, detail="只有已投放状态才能标记待回收核验")
    
    sign.status = "pending_recycle"
    db.commit()
    db.refresh(sign)
    return sign


@router.post("/{sign_id}/recycle", response_model=GuideSignResponse)
def recycle_sign(
    sign_id: int,
    request: RecycleSignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.status not in ["pending_recycle", "issued"]:
        raise HTTPException(status_code=400, detail="当前状态不可回收")
    
    if request.to_pending_review:
        sign.status = "pending_review"
    else:
        sign.status = "available"
    
    recycle_record = IssueRecord(
        sign_id=sign.id,
        issue_type="recycle",
        operator=request.operator,
        remark=request.remark
    )
    db.add(recycle_record)
    db.commit()
    db.refresh(sign)
    return sign


@router.post("/{sign_id}/adjust-position", response_model=GuideSignResponse)
def adjust_position(
    sign_id: int,
    request: PositionAdjustRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.current_area == request.to_area:
        raise HTTPException(status_code=400, detail="校准前后座区相同")
    
    from_area = sign.current_area
    sign.current_area = request.to_area
    
    position_record = PositionRecord(
        sign_id=sign.id,
        from_area=from_area,
        to_area=request.to_area,
        operator=request.operator,
        reason=request.reason
    )
    db.add(position_record)
    db.commit()
    db.refresh(sign)
    return sign


@router.post("/{sign_id}/review", response_model=GuideSignResponse)
def review_sign(
    sign_id: int,
    request: ReviewRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.status != "pending_review":
        raise HTTPException(status_code=400, detail="只有待防错复核状态才能判定")
    
    review_record = ReviewRecord(
        sign_id=sign.id,
        reviewer=request.reviewer,
        conclusion=request.conclusion,
        reason=request.reason,
        summary_meta=request.summary_meta,
        review_digest=request.review_digest
    )
    db.add(review_record)
    
    conclusion_names = {"restore": "复核后可投放", "deactivate": "隔离停用", "reissue": "重新投放"}
    if request.conclusion == "restore":
        sign.status = "restored"
    elif request.conclusion == "deactivate":
        sign.status = "deactivated"
    elif request.conclusion == "reissue":
        sign.status = "available"
    else:
        raise HTTPException(status_code=400, detail="无效的复核判定")

    # 复核结论回写位标链路摘要
    digest_segment = f"防错复核（{conclusion_names.get(request.conclusion, request.conclusion)}）：{request.reason or '无判定依据'}"
    if request.review_digest:
        digest_segment += f"｜复核摘要：{request.review_digest}"
    append_flow_digest(sign, digest_segment)
    
    db.commit()
    db.refresh(sign)
    return sign


@router.post("/{sign_id}/restore", response_model=GuideSignResponse)
def restore_sign(
    sign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    sign = db.query(GuideSign).filter(GuideSign.id == sign_id).first()
    if not sign:
        raise HTTPException(status_code=404, detail="导引位标不存在")
    if sign.status == "pending_review":
        raise HTTPException(status_code=400, detail="待防错复核期间禁止直接恢复，请先完成复核")
    if sign.status not in ["deactivated"]:
        raise HTTPException(status_code=400, detail="当前状态不可恢复")
    
    sign.status = "restored"
    db.commit()
    db.refresh(sign)
    return sign
