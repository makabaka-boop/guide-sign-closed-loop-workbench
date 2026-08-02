export const STATUS_MAP = {
  pending_production: { label: '待印制校样', type: 'info' },
  available: { label: '待投放', type: 'success' },
  issued: { label: '已投放', type: 'warning' },
  pending_recycle: { label: '待回收核验', type: 'warning' },
  pending_review: { label: '待防错复核', type: 'danger' },
  restored: { label: '复核后可投放', type: 'success' },
  deactivated: { label: '隔离停用', type: 'info' }
}

export const ANOMALY_STATUS_MAP = {
  pending: { label: '待现场核查', type: 'danger' },
  processing: { label: '核查中', type: 'warning' },
  pending_confirm: { label: '待复核确认', type: 'warning' },
  closed: { label: '已核销闭环', type: 'success' }
}

export const ANOMALY_TYPE_MAP = {
  lost: { label: '离场缺失', type: 'danger' },
  damaged: { label: '版面破损', type: 'warning' },
  wrong_issue: { label: '座区错配', type: 'warning' },
  overdue: { label: '散场超时未回收', type: 'warning' },
  other: { label: '其他', type: 'info' }
}

export const ANOMALY_LEVEL_MAP = {
  low: { label: '低', type: 'info' },
  normal: { label: '一般', type: 'warning' },
  high: { label: '高', type: 'danger' },
  critical: { label: '严重', type: 'danger' }
}

export const ANOMALY_ACTION_MAP = {
  register: '偏差登记',
  start_process: '开始现场核查',
  submit_confirm: '提交复核确认',
  confirm_close: '核销闭环',
  reject: '退回复查',
  reopen: '重新纳入核查',
  add_remark: '补充核查说明'
}

export const SCENE_SCOPE_MAP = {
  private: { label: '本批次专用', type: 'info' },
  shared: { label: '同批次共用链路', type: 'warning' }
}

export const RISK_LEVEL_MAP = {
  green: { label: '正常', type: 'success' },
  yellow: { label: '提醒', type: 'warning' },
  red: { label: '拦截', type: 'danger' }
}

export const CONSISTENCY_STATE_MAP = {
  ok: { label: '一致', type: 'success' },
  warn: { label: '冲突可继续', type: 'warning' },
  conflict: { label: '冲突阻断', type: 'danger' }
}

export function getStatusLabel(status) {
  return STATUS_MAP[status]?.label || status
}

export function getStatusType(status) {
  return STATUS_MAP[status]?.type || 'info'
}

export function getAnomalyStatusLabel(status) {
  return ANOMALY_STATUS_MAP[status]?.label || status
}

export function getAnomalyStatusType(status) {
  return ANOMALY_STATUS_MAP[status]?.type || 'info'
}

export function getAnomalyTypeLabel(type) {
  return ANOMALY_TYPE_MAP[type]?.label || type
}

export function getAnomalyTypeType(type) {
  return ANOMALY_TYPE_MAP[type]?.type || 'info'
}

export function getAnomalyLevelLabel(level) {
  return ANOMALY_LEVEL_MAP[level]?.label || level
}

export function getAnomalyLevelType(level) {
  return ANOMALY_LEVEL_MAP[level]?.type || 'info'
}

export function getAnomalyActionLabel(action) {
  return ANOMALY_ACTION_MAP[action] || action
}

export function getSceneScopeLabel(scope) {
  return SCENE_SCOPE_MAP[scope]?.label || scope || '-'
}

export function getSceneScopeType(scope) {
  return SCENE_SCOPE_MAP[scope]?.type || 'info'
}

export function getRiskLevelLabel(level) {
  return RISK_LEVEL_MAP[level]?.label || level || '-'
}

export function getRiskLevelType(level) {
  return RISK_LEVEL_MAP[level]?.type || 'info'
}

export function getConsistencyStateLabel(state) {
  return CONSISTENCY_STATE_MAP[state]?.label || state || '-'
}

export function getConsistencyStateType(state) {
  return CONSISTENCY_STATE_MAP[state]?.type || 'info'
}
