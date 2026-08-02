from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import GuideSign, PositionRecord, IssueRecord, User, Anomaly
from auth import get_current_user
from schemas import OverviewStats, SessionUsageItem, AreaConflictItem, PersonWorkloadItem, TraceBatchItem

router = APIRouter(prefix="/api/stats", tags=["现场闭环总览"])

RISK_RANK = {"normal": 0, "yellow": 1, "red": 2}
CONSISTENCY_RANK = {"ok": 0, "warn": 1}


def _build_trace_batches(db: Session) -> List[TraceBatchItem]:
    signs = db.query(GuideSign).filter(
        GuideSign.trace_code.isnot(None),
        GuideSign.trace_code != ""
    ).all()
    if not signs:
        return []

    groups = {}
    for sign in signs:
        code = sign.trace_code
        if code not in groups:
            groups[code] = []
        groups[code].append(sign)

    batches = []
    for trace_code, sign_list in groups.items():
        sign_ids = [s.id for s in sign_list]
        sign_count = len(sign_list)
        issued_count = sum(1 for s in sign_list if s.status == "issued")
        pending_recycle_count = sum(1 for s in sign_list if s.status == "pending_recycle")
        pending_review_count = sum(1 for s in sign_list if s.status == "pending_review")

        active_anomaly_count = db.query(func.count(Anomaly.id)).filter(
            Anomaly.sign_id.in_(sign_ids),
            Anomaly.current_status.in_(["pending", "processing", "pending_confirm"])
        ).scalar() or 0

        max_risk = "normal"
        worst_consistency = "ok"
        for s in sign_list:
            if RISK_RANK.get(s.risk_level, 0) > RISK_RANK.get(max_risk, 0):
                max_risk = s.risk_level
            if CONSISTENCY_RANK.get(s.consistency_state, 0) > CONSISTENCY_RANK.get(worst_consistency, 0):
                worst_consistency = s.consistency_state

        latest_issue = db.query(IssueRecord).filter(
            IssueRecord.sign_id.in_(sign_ids)
        ).order_by(IssueRecord.created_at.desc()).first()

        latest_position = db.query(PositionRecord).filter(
            PositionRecord.sign_id.in_(sign_ids)
        ).order_by(PositionRecord.created_at.desc()).first()

        latest_flow_note = ""
        latest_dt = None
        if latest_issue:
            action_label = "投放" if latest_issue.issue_type == "issue" else "回收"
            latest_flow_note = f"{action_label}：{latest_issue.operator}"
            if latest_issue.remark:
                latest_flow_note += f"（{latest_issue.remark}）"
            latest_dt = latest_issue.created_at
        if latest_position and (latest_dt is None or latest_position.created_at > latest_dt):
            latest_flow_note = f"座区校准：{latest_position.from_area}→{latest_position.to_area}（{latest_position.operator}）"
            if latest_position.reason:
                latest_flow_note += f"，{latest_position.reason}"

        batches.append(TraceBatchItem(
            trace_code=trace_code,
            risk_level=max_risk,
            consistency_state=worst_consistency,
            sign_count=sign_count,
            issued_count=issued_count,
            pending_recycle_count=pending_recycle_count,
            pending_review_count=pending_review_count,
            active_anomaly_count=active_anomaly_count,
            latest_flow_note=latest_flow_note
        ))

    batches.sort(key=lambda b: (RISK_RANK.get(b.risk_level, 0), b.active_anomaly_count), reverse=True)
    return batches


@router.get("/overview", response_model=OverviewStats)
def get_overview_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    total_signs = db.query(GuideSign).count()
    
    pending_production = db.query(GuideSign).filter(GuideSign.status == "pending_production").count()
    available = db.query(GuideSign).filter(GuideSign.status == "available").count()
    issued = db.query(GuideSign).filter(GuideSign.status == "issued").count()
    pending_recycle = db.query(GuideSign).filter(GuideSign.status == "pending_recycle").count()
    pending_review = db.query(GuideSign).filter(GuideSign.status == "pending_review").count()
    restored = db.query(GuideSign).filter(GuideSign.status == "restored").count()
    deactivated = db.query(GuideSign).filter(GuideSign.status == "deactivated").count()
    
    session_usage_query = db.query(
        IssueRecord.session,
        func.count(IssueRecord.id).label('count')
    ).filter(
        IssueRecord.issue_type == 'issue',
        IssueRecord.session.isnot(None),
        IssueRecord.session != ''
    ).group_by(IssueRecord.session).order_by(func.count(IssueRecord.id).desc()).limit(10).all()
    
    session_usage = [
        SessionUsageItem(session=row.session, count=row.count)
        for row in session_usage_query
    ]
    
    area_conflicts_query = db.query(
        PositionRecord.to_area.label('area'),
        func.count(PositionRecord.id).label('conflict_count')
    ).group_by(PositionRecord.to_area).order_by(func.count(PositionRecord.id).desc()).limit(10).all()
    
    area_conflicts = [
        AreaConflictItem(area=row.area, conflict_count=row.conflict_count)
        for row in area_conflicts_query
    ]
    
    person_workload_query = db.query(
        IssueRecord.operator.label('person'),
        func.count(IssueRecord.id).label('count')
    ).group_by(IssueRecord.operator).order_by(func.count(IssueRecord.id).desc()).limit(10).all()
    
    person_workload = [
        PersonWorkloadItem(person=row.person, count=row.count)
        for row in person_workload_query
    ]
    
    pending_review_list = db.query(GuideSign).filter(
        GuideSign.status == "pending_review"
    ).order_by(GuideSign.updated_at.desc()).all()
    
    total_anomalies = db.query(Anomaly).count()
    pending_anomalies = db.query(Anomaly).filter(Anomaly.current_status == "pending").count()
    processing_anomalies = db.query(Anomaly).filter(Anomaly.current_status == "processing").count()
    pending_confirm_anomalies = db.query(Anomaly).filter(Anomaly.current_status == "pending_confirm").count()
    closed_anomalies = db.query(Anomaly).filter(Anomaly.current_status == "closed").count()
    
    recent_anomalies = db.query(Anomaly).filter(
        Anomaly.current_status != "closed"
    ).order_by(Anomaly.created_at.desc()).limit(5).all()
    
    trace_batches = _build_trace_batches(db)
    
    return OverviewStats(
        total_signs=total_signs,
        pending_production=pending_production,
        available=available,
        issued=issued,
        pending_recycle=pending_recycle,
        pending_review=pending_review,
        restored=restored,
        deactivated=deactivated,
        session_usage=session_usage,
        area_conflicts=area_conflicts,
        person_workload=person_workload,
        pending_review_list=pending_review_list,
        total_anomalies=total_anomalies,
        pending_anomalies=pending_anomalies,
        processing_anomalies=processing_anomalies,
        pending_confirm_anomalies=pending_confirm_anomalies,
        closed_anomalies=closed_anomalies,
        recent_anomalies=recent_anomalies,
        trace_batches=trace_batches
    )
