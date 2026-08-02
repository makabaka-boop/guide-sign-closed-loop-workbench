from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List

from database import get_db
from models import GuideSign, PositionRecord, IssueRecord, User, Anomaly
from auth import get_current_user
from schemas import OverviewStats, SessionUsageItem, AreaConflictItem, PersonWorkloadItem, TraceBatchItem

router = APIRouter(prefix="/api/stats", tags=["现场闭环总览"])


OPEN_ANOMALY_STATUSES = ["pending", "processing", "pending_confirm"]

# 风险等级排序，用于挑选组内最需要关注的风险口径
RISK_PRIORITY = {"red": 3, "yellow": 2, "none": 1, "": 0}
CONSISTENCY_PRIORITY = {"blocked": 3, "warn": 2, "normal": 1, "": 0}


def build_trace_batches(db: Session):
    """按 trace_code 聚合同组位标流转风险视图。

    - risk_level / consistency_state / latest_flow_note 取组内最近更新位标的值
    - 未闭环偏差包含 pending / processing / pending_confirm 状态
    - 流转说明优先 handover_note，回退 flow_digest
    """
    signs = db.query(GuideSign).filter(
        GuideSign.trace_code.isnot(None),
        GuideSign.trace_code != ""
    ).all()

    groups = {}
    for sign in signs:
        groups.setdefault(sign.trace_code, []).append(sign)

    def sort_key(s):
        return (s.updated_at or s.created_at, s.id)

    batches = []
    for trace_code, group in groups.items():
        latest = max(group, key=sort_key)
        sign_ids = [s.id for s in group]

        open_anomaly_count = db.query(Anomaly).filter(
            Anomaly.sign_id.in_(sign_ids),
            Anomaly.current_status.in_(OPEN_ANOMALY_STATUSES)
        ).count()

        latest_flow_note = (latest.handover_note or "").strip() or (latest.flow_digest or "").strip()

        batches.append(TraceBatchItem(
            trace_code=trace_code,
            risk_level=latest.risk_level or "none",
            consistency_state=latest.consistency_state or "normal",
            scene_scope=latest.scene_scope or "exclusive",
            total_count=len(group),
            issued_count=sum(1 for s in group if s.status == "issued"),
            pending_recycle_count=sum(1 for s in group if s.status == "pending_recycle"),
            pending_review_count=sum(1 for s in group if s.status == "pending_review"),
            open_anomaly_count=open_anomaly_count,
            latest_flow_note=latest_flow_note
        ))

    # 风险高、一致性冲突、未闭环偏差多的批次优先展示
    batches.sort(key=lambda b: (
        RISK_PRIORITY.get(b.risk_level, 0),
        CONSISTENCY_PRIORITY.get(b.consistency_state, 0),
        b.open_anomaly_count
    ), reverse=True)
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
    
    trace_batches = build_trace_batches(db)
    
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
