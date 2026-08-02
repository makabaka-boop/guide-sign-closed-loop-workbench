from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json
from datetime import datetime

from database import get_db
from models import GuideSign, PositionRecord, IssueRecord, ReviewRecord, User, Anomaly
from auth import get_current_user
from schemas import (
    GuideSignCreate, GuideSignUpdate, GuideSignResponse,
    IssueSignRequest, RecycleSignRequest, PositionAdjustRequest, ReviewRequest
)

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

ISSUE_TYPE_LABEL = {
    "issue": "投放",
    "recycle": "回收"
}

REVIEW_CONCLUSION_LABEL = {
    "restore": "复核后可投放",
    "deactivate": "隔离停用",
    "reissue": "重新投放"
}


def _isoformat(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _build_flow_digest(sign: GuideSign, db: Session) -> str:
    digest = {
        "sign_number": sign.sign_number,
        "trace_code": sign.trace_code or "",
        "current_status": sign.status,
        "current_area": sign.current_area,
        "last_issue": None,
        "last_recycle": None,
        "last_position_adjust": None,
        "last_review": None,
        "issue_count": 0,
        "recycle_count": 0,
        "position_adjust_count": 0,
        "review_count": 0,
        "updated_at": _isoformat(sign.updated_at or sign.created_at)
    }

    last_issue = db.query(IssueRecord).filter(
        IssueRecord.sign_id == sign.id,
        IssueRecord.issue_type == "issue"
    ).order_by(IssueRecord.created_at.desc()).first()
    if last_issue:
        digest["last_issue"] = {
            "session": last_issue.session,
            "operator": last_issue.operator,
            "receiver": last_issue.receiver,
            "remark": last_issue.remark or "",
            "at": _isoformat(last_issue.created_at)
        }

    last_recycle = db.query(IssueRecord).filter(
        IssueRecord.sign_id == sign.id,
        IssueRecord.issue_type == "recycle"
    ).order_by(IssueRecord.created_at.desc()).first()
    if last_recycle:
        digest["last_recycle"] = {
            "operator": last_recycle.operator,
            "remark": last_recycle.remark or "",
            "at": _isoformat(last_recycle.created_at)
        }

    last_position = db.query(PositionRecord).filter(
        PositionRecord.sign_id == sign.id
    ).order_by(PositionRecord.created_at.desc()).first()
    if last_position:
        digest["last_position_adjust"] = {
            "from_area": last_position.from_area,
            "to_area": last_position.to_area,
            "operator": last_position.operator,
            "reason": last_position.reason or "",
            "at": _isoformat(last_position.created_at)
        }

    last_review = db.query(ReviewRecord).filter(
        ReviewRecord.sign_id == sign.id
    ).order_by(ReviewRecord.created_at.desc()).first()
    if last_review:
        digest["last_review"] = {
            "reviewer": last_review.reviewer,
            "conclusion": last_review.conclusion,
            "conclusion_label": REVIEW_CONCLUSION_LABEL.get(last_review.conclusion, last_review.conclusion),
            "reason": last_review.reason or "",
            "summary_meta": last_review.summary_meta or "",
            "review_digest": last_review.review_digest or "",
            "at": _isoformat(last_review.created_at)
        }

    digest["issue_count"] = db.query(func.count(IssueRecord.id)).filter(
        IssueRecord.sign_id == sign.id,
        IssueRecord.issue_type == "issue"
    ).scalar() or 0
    digest["recycle_count"] = db.query(func.count(IssueRecord.id)).filter(
        IssueRecord.sign_id == sign.id,
        IssueRecord.issue_type == "recycle"
    ).scalar() or 0
    digest["position_adjust_count"] = db.query(func.count(PositionRecord.id)).filter(
        PositionRecord.sign_id == sign.id
    ).scalar() or 0
    digest["review_count"] = db.query(func.count(ReviewRecord.id)).filter(
        ReviewRecord.sign_id == sign.id
    ).scalar() or 0

    return json.dumps(digest, ensure_ascii=False)


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
    trace_code: Optional[str] = None,
    scene_scope: Optional[str] = None,
    risk_level: Optional[str] = None,
    consistency_state: Optional[str] = None,
    applicable_session: Optional[str] = None,
    responsible_person: Optional[str] = None,
    keyword: Optional[str] = None,
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
    if trace_code:
        query = query.filter(GuideSign.trace_code.contains(trace_code))
    if scene_scope:
        query = query.filter(GuideSign.scene_scope == scene_scope)
    if risk_level:
        query = query.filter(GuideSign.risk_level == risk_level)
    if consistency_state:
        query = query.filter(GuideSign.consistency_state == consistency_state)
    if applicable_session:
        query = query.filter(GuideSign.applicable_session.contains(applicable_session))
    if responsible_person:
        query = query.filter(GuideSign.responsible_person.contains(responsible_person))
    if keyword:
        query = query.filter(
            GuideSign.sign_number.contains(keyword) |
            GuideSign.current_area.contains(keyword)
        )
    
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

    if request.handover_note and request.handover_note.strip():
        sign.handover_note = request.handover_note.strip()

    remark_parts = []
    if request.remark and request.remark.strip():
        remark_parts.append(request.remark.strip())
    if request.handover_note and request.handover_note.strip():
        remark_parts.append(f"[交接说明] {request.handover_note.strip()}")
    merged_remark = "\n".join(remark_parts)

    issue_record = IssueRecord(
        sign_id=sign.id,
        issue_type="issue",
        session=request.session,
        operator=request.operator,
        receiver=request.receiver,
        remark=merged_remark
    )
    db.add(issue_record)
    db.flush()

    sign.flow_digest = _build_flow_digest(sign, db)

    db.commit()
    db.refresh(sign)
    enrich_sign_with_anomaly(sign, db)
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

    summary_meta = (request.summary_meta or "").strip()
    if not summary_meta:
        raise HTTPException(status_code=400, detail="summary_meta 不能为空，请补全复核链路汇总后再提交")

    review_record = ReviewRecord(
        sign_id=sign.id,
        reviewer=request.reviewer,
        conclusion=request.conclusion,
        reason=request.reason,
        summary_meta=summary_meta,
        review_digest=request.review_digest or ""
    )
    db.add(review_record)

    if request.conclusion == "restore":
        sign.status = "restored"
    elif request.conclusion == "deactivate":
        sign.status = "deactivated"
    elif request.conclusion == "reissue":
        sign.status = "available"
    else:
        raise HTTPException(status_code=400, detail="无效的复核判定")

    sign.summary_meta = summary_meta
    db.flush()
    sign.flow_digest = _build_flow_digest(sign, db)

    db.commit()
    db.refresh(sign)
    enrich_sign_with_anomaly(sign, db)
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
