<template>
  <div class="review-page">
    <el-card class="stats-card">
      <el-row :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">待防错复核</div>
            <div class="stat-value danger">{{ stats.pending_review || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">已复核后可投放</div>
            <div class="stat-value success">{{ stats.restored || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">已隔离停用</div>
            <div class="stat-value info">{{ stats.deactivated || 0 }}</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-label">流程总量</div>
            <div class="stat-value">{{ stats.total_signs || 0 }}</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>防错复核队列</span>
          <el-button type="primary" @click="fetchList">
            <el-icon><Refresh /></el-icon>刷新
          </el-button>
        </div>
      </template>
      <el-table :data="reviewList" v-loading="loading" stripe>
        <el-table-column label="位标编号" width="180">
          <template #default="{ row }">
            <div class="sign-number-with-tag">
              <span>{{ row.sign_number }}</span>
              <el-tooltip v-if="row.has_active_anomaly" :content="'存在未闭合偏差：' + (row.active_anomaly_types || []).map(t => getAnomalyTypeLabel(t)).join('、')" placement="top">
                <el-tag type="danger" size="small" effect="dark" round class="anomaly-tag">偏差</el-tag>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="batch_code" label="批次编号" width="120" />
        <el-table-column prop="applicable_session" label="试听班次" width="140" />
        <el-table-column prop="current_area" label="目标座区" width="140" />
        <el-table-column prop="responsible_person" label="现场负责人" width="120" />
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag type="danger">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="偏差提示" width="160">
          <template #default="{ row }">
            <span v-if="row.has_active_anomaly" class="anomaly-warning">
              <el-icon><Warning /></el-icon>
              {{ (row.active_anomaly_types || []).length }}项未闭环
            </span>
            <span v-else class="no-anomaly">
              <el-icon><CircleCheck /></el-icon>
              正常
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openReviewDialog(row)">复核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="reviewDialogVisible" title="防错复核登记" width="900px" top="5vh">
      <div v-loading="detailLoading" class="review-dialog-body">
        <el-tabs v-model="activeTab" v-if="currentSign">
          <el-tab-pane label="基础信息" name="basic">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="位标编号">{{ currentSign.sign_number }}</el-descriptions-item>
              <el-descriptions-item label="批次编号">{{ currentSign.batch_code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="追踪码 trace_code">{{ currentSign.trace_code || '-' }}</el-descriptions-item>
              <el-descriptions-item label="试听班次">{{ currentSign.applicable_session }}</el-descriptions-item>
              <el-descriptions-item label="当前座区">{{ currentSign.current_area }}</el-descriptions-item>
              <el-descriptions-item label="现场负责人">{{ currentSign.responsible_person }}</el-descriptions-item>
              <el-descriptions-item label="链路范围">
                <el-tag :type="getSceneScopeType(currentSign.scene_scope)" size="small">
                  {{ getSceneScopeLabel(currentSign.scene_scope) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="风险等级">
                <el-tag :type="getRiskLevelType(currentSign.risk_level)" size="small" effect="dark">
                  {{ getRiskLevelLabel(currentSign.risk_level) }}
                </el-tag>
                <el-tag
                  :type="getConsistencyStateType(currentSign.consistency_state)"
                  size="small"
                  style="margin-left: 6px"
                >
                  一致性·{{ getConsistencyStateLabel(currentSign.consistency_state) }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="交接备注" :span="2">
                {{ currentSign.handover_note || '-' }}
              </el-descriptions-item>
              <el-descriptions-item label="原备注" :span="2">
                {{ currentSign.remark || '-' }}
              </el-descriptions-item>
            </el-descriptions>
          </el-tab-pane>

          <el-tab-pane :label="`同批次位标 (${tracePeers.length})`" name="peers">
            <el-table :data="tracePeers" size="small" stripe max-height="320">
              <el-table-column prop="sign_number" label="位标编号" width="140" />
              <el-table-column prop="current_area" label="目标座区" width="140" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" size="small">
                    {{ getStatusLabel(row.status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="responsible_person" label="负责人" width="110" />
              <el-table-column label="偏差" width="80" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.has_active_anomaly" type="danger" size="small">
                    {{ row.active_anomaly_count || 0 }}
                  </el-tag>
                  <span v-else class="muted">0</span>
                </template>
              </el-table-column>
              <el-table-column prop="applicable_session" label="班次" min-width="120" />
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="座区校准 / 投放回收" name="flow">
            <div class="flow-section">
              <div class="section-title">最近座区校准</div>
              <el-table :data="(currentSign.position_records || []).slice(0, 5)" size="small" border>
                <el-table-column prop="from_area" label="原座区" width="140" />
                <el-table-column prop="to_area" label="新座区" width="140" />
                <el-table-column prop="operator" label="执行人" width="110" />
                <el-table-column prop="reason" label="原因" min-width="140" show-overflow-tooltip />
                <el-table-column label="时间" width="160">
                  <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                </el-table-column>
              </el-table>
              <div v-if="!(currentSign.position_records || []).length" class="empty-hint">暂无座区校准记录</div>
            </div>
            <div class="flow-section">
              <div class="section-title">投放回收摘要</div>
              <el-table :data="(currentSign.issue_records || []).slice(0, 6)" size="small" border>
                <el-table-column label="类型" width="80">
                  <template #default="{ row }">
                    <el-tag :type="row.issue_type === 'issue' ? 'success' : 'info'" size="small">
                      {{ row.issue_type === 'issue' ? '投放' : '回收' }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="session" label="班次" width="140" />
                <el-table-column prop="operator" label="执行人" width="110" />
                <el-table-column prop="receiver" label="接场人" width="110" />
                <el-table-column prop="remark" label="摘要/备注" min-width="160" show-overflow-tooltip />
                <el-table-column label="时间" width="160">
                  <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
                </el-table-column>
              </el-table>
              <div v-if="!(currentSign.issue_records || []).length" class="empty-hint">暂无投放回收记录</div>
            </div>
          </el-tab-pane>

          <el-tab-pane :label="`关联偏差 (${relatedAnomalies.length})`" name="anomalies">
            <el-table :data="relatedAnomalies" size="small" stripe max-height="320">
              <el-table-column prop="id" label="编号" width="70" />
              <el-table-column label="类型" width="100">
                <template #default="{ row }">
                  <el-tag :type="getAnomalyTypeType(row.anomaly_type)" size="small">
                    {{ getAnomalyTypeLabel(row.anomaly_type) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">
                    {{ getAnomalyStatusLabel(row.current_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="responsible_person" label="负责人" width="100" />
              <el-table-column prop="description" label="描述" min-width="160" show-overflow-tooltip />
              <el-table-column prop="final_result" label="处理结果" min-width="160" show-overflow-tooltip />
              <el-table-column label="登记时间" width="160">
                <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
              </el-table-column>
            </el-table>
          </el-tab-pane>

          <el-tab-pane label="链路摘要 summary_meta" name="summary">
            <el-alert
              type="info"
              :closable="false"
              show-icon
              title="summary_meta 是本次复核的链路汇总结论"
              description="请在综合以上各 Tab 信息后，在下方文本框中填写本次复核的链路总结（将写入复核记录与位标 summary_meta，并刷新 flow_digest）。"
              style="margin-bottom: 12px"
            />
            <el-input
              v-model="reviewForm.summary_meta"
              type="textarea"
              :rows="6"
              placeholder="请填写本次复核链路汇总，例如：同批次 X 个位标，已闭环偏差 Y 项，座区校准 N 次，结论为...（提交时不能为空）"
            />
            <div class="existing-summary" v-if="currentSign.summary_meta">
              <div class="section-title">位标历史 summary_meta</div>
              <pre class="digest-block">{{ formatDigest(currentSign.summary_meta) }}</pre>
            </div>
            <div class="existing-summary" v-if="currentSign.flow_digest">
              <div class="section-title">当前 flow_digest（提交后会自动刷新）</div>
              <pre class="digest-block">{{ formatDigest(currentSign.flow_digest) }}</pre>
            </div>
          </el-tab-pane>
        </el-tabs>

        <el-divider content-position="left">复核判定</el-divider>
        <el-form :model="reviewForm" :rules="reviewRules" ref="reviewFormRef" label-width="100px">
          <el-form-item label="复核员" prop="reviewer">
            <el-input v-model="reviewForm.reviewer" placeholder="请输入复核员姓名" />
          </el-form-item>
          <el-form-item label="复核判定" prop="conclusion">
            <el-radio-group v-model="reviewForm.conclusion">
              <el-radio value="restore">复核后可投放</el-radio>
              <el-radio value="reissue">重新投放</el-radio>
              <el-radio value="deactivate">隔离停用</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="判定依据" prop="reason">
            <el-input v-model="reviewForm.reason" type="textarea" :rows="3" placeholder="请输入判定依据" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="reviewDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleReview" :loading="submitLoading">确认判定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Warning, CircleCheck } from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getStatusLabel, getStatusType,
  getAnomalyTypeLabel, getAnomalyTypeType,
  getAnomalyStatusLabel, getAnomalyStatusType,
  getSceneScopeLabel, getSceneScopeType,
  getRiskLevelLabel, getRiskLevelType,
  getConsistencyStateLabel, getConsistencyStateType
} from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const detailLoading = ref(false)
const reviewList = ref([])
const currentSign = ref(null)
const tracePeers = ref([])
const relatedAnomalies = ref([])
const activeTab = ref('basic')
const stats = reactive({
  total_signs: 0,
  pending_review: 0,
  restored: 0,
  deactivated: 0
})

const reviewDialogVisible = ref(false)
const reviewFormRef = ref(null)
const reviewForm = reactive({
  reviewer: '',
  conclusion: 'restore',
  reason: '',
  summary_meta: ''
})
const reviewRules = {
  reviewer: [{ required: true, message: '请输入复核员', trigger: 'blur' }],
  conclusion: [{ required: true, message: '请选择复核判定', trigger: 'change' }],
  reason: [{ required: true, message: '请输入判定依据', trigger: 'blur' }],
  summary_meta: [{ required: true, message: '请填写链路汇总 summary_meta 后再提交', trigger: 'blur' }]
}

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
}

function formatDigest(value) {
  if (!value) return '-'
  const trimmed = String(value).trim()
  if (!trimmed) return '-'
  try {
    return JSON.stringify(JSON.parse(trimmed), null, 2)
  } catch (e) {
    return trimmed
  }
}

function buildReviewDigest(sign, peers, anomalies) {
  const positionRecords = [...(sign.position_records || [])].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  )
  const issueRecords = [...(sign.issue_records || [])].sort(
    (a, b) => new Date(b.created_at) - new Date(a.created_at)
  )
  const lastPosition = positionRecords[0]
  const lastIssue = issueRecords.find((r) => r.issue_type === 'issue')
  const lastRecycle = issueRecords.find((r) => r.issue_type === 'recycle')
  const activeAnomalies = (anomalies || []).filter((a) => a.current_status !== 'closed')
  const closedAnomalies = (anomalies || []).filter((a) => a.current_status === 'closed')

  return JSON.stringify({
    sign_id: sign.id,
    sign_number: sign.sign_number,
    trace_code: sign.trace_code || '',
    scene_scope: sign.scene_scope,
    risk_level: sign.risk_level,
    consistency_state_before: sign.consistency_state,
    peer_count: (peers || []).length,
    peer_status_breakdown: (peers || []).reduce((acc, peer) => {
      acc[peer.status] = (acc[peer.status] || 0) + 1
      return acc
    }, {}),
    last_position: lastPosition ? {
      from_area: lastPosition.from_area,
      to_area: lastPosition.to_area,
      operator: lastPosition.operator,
      reason: lastPosition.reason,
      at: lastPosition.created_at
    } : null,
    last_issue: lastIssue ? {
      session: lastIssue.session,
      operator: lastIssue.operator,
      receiver: lastIssue.receiver,
      remark: lastIssue.remark,
      at: lastIssue.created_at
    } : null,
    last_recycle: lastRecycle ? {
      operator: lastRecycle.operator,
      remark: lastRecycle.remark,
      at: lastRecycle.created_at
    } : null,
    anomaly_total: (anomalies || []).length,
    anomaly_active: activeAnomalies.length,
    anomaly_closed: closedAnomalies.length,
    reviewer: reviewForm.reviewer,
    conclusion: reviewForm.conclusion,
    reason: reviewForm.reason,
    submitted_at: new Date().toISOString()
  }, null, 2)
}

async function fetchList() {
  loading.value = true
  try {
    const data = await request.get('/stats/overview')
    reviewList.value = data.pending_review_list || []
    stats.total_signs = data.total_signs
    stats.pending_review = data.pending_review
    stats.restored = data.restored
    stats.deactivated = data.deactivated
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function loadReviewContext(signId) {
  detailLoading.value = true
  tracePeers.value = []
  relatedAnomalies.value = []
  try {
    const detail = await request.get(`/signs/${signId}`)
    currentSign.value = detail

    const traceCode = (detail.trace_code || '').trim()
    if (traceCode) {
      const allSigns = await request.get('/signs', {
        params: { trace_code: traceCode, limit: 200 }
      })
      tracePeers.value = allSigns
    } else {
      tracePeers.value = [detail]
    }

    if (traceCode) {
      relatedAnomalies.value = await request.get('/anomalies', {
        params: { trace_code: traceCode, limit: 200 }
      })
    }
  } catch (e) {
    console.error(e)
    ElMessage.error('加载复核上下文失败')
  } finally {
    detailLoading.value = false
  }
}

function openReviewDialog(row) {
  currentSign.value = { ...row }
  tracePeers.value = []
  relatedAnomalies.value = []
  reviewDialogVisible.value = true
  activeTab.value = 'basic'
  reviewForm.reviewer = ''
  reviewForm.conclusion = 'restore'
  reviewForm.reason = ''
  reviewForm.summary_meta = row.summary_meta || ''
  loadReviewContext(row.id)
}

async function handleReview() {
  try {
    await reviewFormRef.value.validate()
    if (!reviewForm.summary_meta || !reviewForm.summary_meta.trim()) {
      ElMessage.warning('请先在"链路摘要 summary_meta"页签中补全链路汇总')
      activeTab.value = 'summary'
      return
    }
    submitLoading.value = true
    const reviewDigest = buildReviewDigest(
      currentSign.value,
      tracePeers.value,
      relatedAnomalies.value
    )
    await request.post(`/signs/${currentSign.value.id}/review`, {
      reviewer: reviewForm.reviewer,
      conclusion: reviewForm.conclusion,
      reason: reviewForm.reason,
      summary_meta: reviewForm.summary_meta.trim(),
      review_digest: reviewDigest
    })
    ElMessage.success('防错复核完成')
    reviewDialogVisible.value = false
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.review-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-card .stat-item {
  background: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  text-align: center;
}

.stat-label {
  color: #909399;
  font-size: 14px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
}

.stat-value.success {
  color: #67c23a;
}

.stat-value.danger {
  color: #f56c6c;
}

.stat-value.info {
  color: #909399;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.sign-number-with-tag { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.anomaly-tag { margin-left: 4px; }
.anomaly-warning { display: inline-flex; align-items: center; gap: 4px; color: #f56c6c; font-size: 13px; font-weight: 500; }
.no-anomaly { display: inline-flex; align-items: center; gap: 4px; color: #67c23a; font-size: 13px; }

.review-dialog-body {
  min-height: 300px;
}

.flow-section {
  margin-bottom: 16px;
}

.section-title {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
  margin-bottom: 8px;
  padding-left: 8px;
  border-left: 3px solid #667eea;
}

.empty-hint {
  color: #909399;
  font-size: 12px;
  padding: 12px;
  text-align: center;
  background: #f7f8fa;
  border-radius: 4px;
}

.existing-summary {
  margin-top: 14px;
}

.digest-block {
  margin: 6px 0 0;
  padding: 10px 12px;
  background: #f7f8fa;
  border-radius: 4px;
  font-family: Menlo, Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 220px;
  overflow: auto;
}

.muted {
  color: #c0c4cc;
}
</style>
