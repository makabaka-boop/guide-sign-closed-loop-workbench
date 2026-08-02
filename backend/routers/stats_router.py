from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import GuideSign, PositionRecord, IssueRecord, User, Anomaly
from auth import get_current_user
from schemas import OverviewStats, SessionUsageItem, AreaConflictItem, PersonWorkloadItem, TraceBatchItem

router = APIRouter(prefix="/api/stats", tags=["现场闭环总览"])


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

    # 批次追踪概览：按 trace_code 聚合同组位标
    trace_signs = db.query(GuideSign).filter(
        GuideSign.trace_code.isnot(None),
        GuideSign.trace_code != ''
    ).all()

    active_anomaly_rows = db.query(
        GuideSign.trace_code,
        func.count(Anomaly.id).label('cnt')
    ).join(Anomaly, Anomaly.sign_id == GuideSign.id).filter(
        GuideSign.trace_code.isnot(None),
        GuideSign.trace_code != '',
        Anomaly.current_status.in_(["pending", "processing", "pending_confirm"])
    ).group_by(GuideSign.trace_code).all()
    active_anomaly_map = {row.trace_code: row.cnt for row in active_anomaly_rows}

    batch_groups = {}
    for sign in trace_signs:
        group = batch_groups.setdefault(sign.trace_code, [])
        group.append(sign)

    trace_batches = []
    for code, signs in batch_groups.items():
        latest_sign = max(signs, key=lambda s: (s.updated_at or s.created_at or 0, s.id))
        trace_batches.append(TraceBatchItem(
            trace_code=code,
            risk_level=latest_sign.risk_level or "",
            consistency_state=latest_sign.consistency_state or "",
            sign_count=len(signs),
            issued_count=sum(1 for s in signs if s.status == "issued"),
            pending_recycle_count=sum(1 for s in signs if s.status == "pending_recycle"),
            pending_review_count=sum(1 for s in signs if s.status == "pending_review"),
            active_anomaly_count=active_anomaly_map.get(code, 0),
            latest_flow_note=latest_sign.handover_note or latest_sign.flow_digest or ""
        ))
    trace_batches.sort(key=lambda b: b.trace_code)
    
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
