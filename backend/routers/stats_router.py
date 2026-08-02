from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from collections import defaultdict
from datetime import datetime

from database import get_db
from models import GuideSign, PositionRecord, IssueRecord, User, Anomaly
from auth import get_current_user
from schemas import (
    OverviewStats, SessionUsageItem, AreaConflictItem,
    PersonWorkloadItem, TraceBatchItem
)

router = APIRouter(prefix="/api/stats", tags=["现场闭环总览"])

RISK_RANK = {"green": 0, "yellow": 1, "red": 2}
CONSISTENCY_RANK = {"ok": 0, "warn": 1, "conflict": 2}
ACTIVE_ANOMALY_STATUSES = ("pending", "processing", "pending_confirm")


def _max_by_rank(values, rank_map, default):
    best = default
    best_rank = -1
    for value in values:
        if not value:
            continue
        rank = rank_map.get(value, -1)
        if rank > best_rank:
            best_rank = rank
            best = value
    return best


def _build_trace_batches(db: Session) -> List[TraceBatchItem]:
    signs = db.query(GuideSign).filter(
        GuideSign.trace_code.isnot(None),
        GuideSign.trace_code != ""
    ).all()

    if not signs:
        return []

    groups = defaultdict(list)
    for sign in signs:
        groups[sign.trace_code].append(sign)

    sign_ids = [sign.id for sign in signs]

    active_anomaly_counts = dict(
        db.query(Anomaly.sign_id, func.count(Anomaly.id))
        .filter(
            Anomaly.sign_id.in_(sign_ids),
            Anomaly.current_status.in_(ACTIVE_ANOMALY_STATUSES)
        )
        .group_by(Anomaly.sign_id)
        .all()
    )

    latest_issue = (
        db.query(IssueRecord.sign_id, IssueRecord.remark, IssueRecord.created_at)
        .filter(IssueRecord.sign_id.in_(sign_ids))
        .order_by(IssueRecord.created_at.desc())
        .all()
    )
    latest_position = (
        db.query(PositionRecord.sign_id, PositionRecord.reason, PositionRecord.created_at)
        .filter(PositionRecord.sign_id.in_(sign_ids))
        .order_by(PositionRecord.created_at.desc())
        .all()
    )

    flow_lookup = {}
    for sign_id, remark, created_at in latest_issue + latest_position:
        if sign_id in flow_lookup:
            if created_at and flow_lookup[sign_id][1] and created_at <= flow_lookup[sign_id][1]:
                continue
        text_value = (remark or "").strip()
        if text_value:
            flow_lookup[sign_id] = (text_value, created_at)

    trace_batches = []
    for trace_code, group_signs in groups.items():
        issued_count = sum(1 for s in group_signs if s.status == "issued")
        pending_recycle_count = sum(1 for s in group_signs if s.status == "pending_recycle")
        pending_review_count = sum(1 for s in group_signs if s.status == "pending_review")
        active_anomaly_count = sum(active_anomaly_counts.get(s.id, 0) for s in group_signs)

        risk_level = _max_by_rank(
            [s.risk_level for s in group_signs], RISK_RANK, "green"
        )
        consistency_state = _max_by_rank(
            [s.consistency_state for s in group_signs], CONSISTENCY_RANK, "ok"
        )
        scene_scope = "shared" if any(
            (s.scene_scope or "private") == "shared" for s in group_signs
        ) else "private"

        latest_note = ""
        latest_at = None
        candidate_signs = sorted(
            group_signs,
            key=lambda s: s.updated_at or s.created_at or datetime.min,
            reverse=True
        )
        for sign in candidate_signs:
            handover = (sign.handover_note or "").strip()
            if handover:
                latest_note = handover
                latest_at = sign.updated_at or sign.created_at
                break
            if sign.id in flow_lookup:
                latest_note, latest_at = flow_lookup[sign.id]
                break

        trace_batches.append(TraceBatchItem(
            trace_code=trace_code,
            risk_level=risk_level or "green",
            consistency_state=consistency_state or "ok",
            scene_scope=scene_scope,
            total_count=len(group_signs),
            issued_count=issued_count,
            pending_recycle_count=pending_recycle_count,
            pending_review_count=pending_review_count,
            active_anomaly_count=active_anomaly_count,
            latest_flow_note=latest_note,
            latest_flow_at=latest_at
        ))

    trace_batches.sort(key=lambda b: (
        RISK_RANK.get(b.risk_level, 0),
        b.active_anomaly_count,
        b.pending_recycle_count,
        b.pending_review_count
    ), reverse=True)

    return trace_batches


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
        trace_batches=trace_batches,
        pending_review_list=pending_review_list,
        total_anomalies=total_anomalies,
        pending_anomalies=pending_anomalies,
        processing_anomalies=processing_anomalies,
        pending_confirm_anomalies=pending_confirm_anomalies,
        closed_anomalies=closed_anomalies,
        recent_anomalies=recent_anomalies
    )
