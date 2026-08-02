from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    username: str
    full_name: str
    role: str = "operator"


class UserCreate(UserBase):
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


class PositionRecordBase(BaseModel):
    from_area: str
    to_area: str
    operator: str
    reason: str = ""


class PositionRecordResponse(PositionRecordBase):
    id: int
    sign_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class IssueRecordBase(BaseModel):
    issue_type: str
    session: Optional[str] = None
    operator: str
    receiver: Optional[str] = None
    remark: str = ""


class IssueRecordResponse(IssueRecordBase):
    id: int
    sign_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewRecordBase(BaseModel):
    reviewer: str
    conclusion: str
    reason: str = ""
    summary_meta: str = ""
    review_digest: str = ""


class ReviewRecordResponse(ReviewRecordBase):
    id: int
    sign_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GuideSignBase(BaseModel):
    sign_number: str
    batch_code: str = ""
    applicable_session: str
    current_area: str
    responsible_person: str
    status: str = "pending_production"
    remark: str = ""
    # 批次追踪与位标链路档案
    trace_code: Optional[str] = ""
    scene_scope: Optional[str] = "exclusive"
    risk_level: Optional[str] = "none"
    handover_note: Optional[str] = ""
    consistency_state: Optional[str] = "normal"
    summary_meta: Optional[str] = ""
    flow_digest: Optional[str] = ""


class GuideSignCreate(GuideSignBase):
    pass


class GuideSignUpdate(BaseModel):
    batch_code: Optional[str] = None
    applicable_session: Optional[str] = None
    current_area: Optional[str] = None
    responsible_person: Optional[str] = None
    remark: Optional[str] = None
    # 批次追踪与位标链路档案
    trace_code: Optional[str] = None
    scene_scope: Optional[str] = None
    risk_level: Optional[str] = None
    handover_note: Optional[str] = None
    consistency_state: Optional[str] = None
    summary_meta: Optional[str] = None
    flow_digest: Optional[str] = None


class GuideSignResponse(GuideSignBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    position_records: List[PositionRecordResponse] = []
    issue_records: List[IssueRecordResponse] = []
    review_records: List[ReviewRecordResponse] = []
    has_active_anomaly: bool = False
    active_anomaly_count: int = 0
    active_anomaly_types: List[str] = []

    class Config:
        from_attributes = True


class IssueSignRequest(BaseModel):
    receiver: str
    session: str
    operator: str
    remark: str = ""


class RecycleSignRequest(BaseModel):
    operator: str
    to_pending_review: bool = False
    remark: str = ""


class PositionAdjustRequest(BaseModel):
    to_area: str
    operator: str
    reason: str = ""


class ReviewRequest(BaseModel):
    reviewer: str
    conclusion: str
    reason: str = ""
    summary_meta: str = ""
    review_digest: str = ""


class SessionUsageItem(BaseModel):
    session: str
    count: int


class AreaConflictItem(BaseModel):
    area: str
    conflict_count: int


class PersonWorkloadItem(BaseModel):
    person: str
    count: int


class AnomalyFlowRecordBase(BaseModel):
    action: str
    operator: str
    remark: str = ""
    from_status: Optional[str] = None
    to_status: Optional[str] = None


class AnomalyFlowRecordResponse(AnomalyFlowRecordBase):
    id: int
    anomaly_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AnomalyBase(BaseModel):
    sign_id: int
    anomaly_type: str
    anomaly_level: str = "normal"
    session: Optional[str] = None
    reporter: str
    responsible_person: str
    description: str = ""
    # 批次追踪快照（登记时由后端从位标带出）
    trace_code: Optional[str] = ""
    scene_scope: Optional[str] = "exclusive"
    risk_level: Optional[str] = "none"
    handover_note: Optional[str] = ""


class AnomalyCreate(AnomalyBase):
    pass


class AnomalyUpdate(BaseModel):
    anomaly_type: Optional[str] = None
    anomaly_level: Optional[str] = None
    session: Optional[str] = None
    responsible_person: Optional[str] = None
    description: Optional[str] = None


class AnomalyProcessRequest(BaseModel):
    operator: str
    remark: str = ""
    action: str


class AnomalyResponse(AnomalyBase):
    id: int
    current_status: str
    final_result: str = ""
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    guide_sign: Optional[GuideSignResponse] = None
    flow_records: List[AnomalyFlowRecordResponse] = []

    class Config:
        from_attributes = True


class AnomalyStatsItem(BaseModel):
    status: str
    count: int


class AnomalyTypeStatsItem(BaseModel):
    anomaly_type: str
    count: int


class TraceBatchItem(BaseModel):
    trace_code: str
    risk_level: str = "none"
    consistency_state: str = "normal"
    scene_scope: str = "exclusive"
    total_count: int = 0
    issued_count: int = 0
    pending_recycle_count: int = 0
    pending_review_count: int = 0
    open_anomaly_count: int = 0
    latest_flow_note: str = ""


class OverviewStats(BaseModel):
    total_signs: int
    pending_production: int
    available: int
    issued: int
    pending_recycle: int
    pending_review: int
    restored: int
    deactivated: int
    session_usage: List[SessionUsageItem]
    area_conflicts: List[AreaConflictItem]
    person_workload: List[PersonWorkloadItem]
    pending_review_list: List[GuideSignResponse]
    total_anomalies: int
    pending_anomalies: int
    processing_anomalies: int
    pending_confirm_anomalies: int
    closed_anomalies: int
    recent_anomalies: List[AnomalyResponse]
    trace_batches: List[TraceBatchItem] = []
