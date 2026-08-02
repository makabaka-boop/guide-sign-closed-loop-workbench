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

    <el-dialog v-model="reviewDialogVisible" title="防错复核 · 一次看完整链路" width="760px" top="6vh">
      <div v-loading="detailLoading">
        <el-descriptions :column="2" border size="small" v-if="currentSign">
          <el-descriptions-item label="位标编号">{{ currentSign.sign_number }}</el-descriptions-item>
          <el-descriptions-item label="批次编号">{{ currentSign.batch_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="批次追踪码">{{ currentSign.trace_code || '未关联' }}</el-descriptions-item>
          <el-descriptions-item label="使用场景">
            <el-tag :type="getSceneScopeType(currentSign.scene_scope)" size="small">{{ getSceneScopeLabel(currentSign.scene_scope) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag :type="getRiskLevelType(currentSign.risk_level)" size="small">{{ getRiskLevelLabel(currentSign.risk_level) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="一致性状态">
            <el-tag :type="getConsistencyStateType(currentSign.consistency_state)" size="small">{{ getConsistencyStateLabel(currentSign.consistency_state) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="当前座区">{{ currentSign.current_area }}</el-descriptions-item>
          <el-descriptions-item label="现场负责人">{{ currentSign.responsible_person }}</el-descriptions-item>
          <el-descriptions-item label="交接备注" :span="2">{{ currentSign.handover_note || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">同批次位标状态</el-divider>
        <div v-if="currentSign && !currentSign.trace_code" class="empty-hint">该位标未关联批次链路</div>
        <el-table v-else :data="batchSigns" size="small" max-height="180" empty-text="暂无同批次位标">
          <el-table-column prop="sign_number" label="位标编号" width="140">
            <template #default="{ row }">
              <span :class="{ 'self-row': row.id === currentSign?.id }">
                {{ row.sign_number }}{{ row.id === currentSign?.id ? '（本枚）' : '' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="current_area" label="目标座区" width="130" />
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="一致性" width="110">
            <template #default="{ row }">
              <el-tag :type="getConsistencyStateType(row.consistency_state)" size="small">{{ getConsistencyStateLabel(row.consistency_state) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="偏差" min-width="90">
            <template #default="{ row }">
              <span v-if="row.has_active_anomaly" class="anomaly-warning">{{ row.active_anomaly_count }} 项</span>
              <span v-else class="no-anomaly">正常</span>
            </template>
          </el-table-column>
        </el-table>

        <el-divider content-position="left">最近座区校准</el-divider>
        <div v-if="!latestPosition" class="empty-hint">暂无座区校准记录</div>
        <el-descriptions v-else :column="2" border size="small">
          <el-descriptions-item label="原座区">{{ latestPosition.from_area }}</el-descriptions-item>
          <el-descriptions-item label="新座区">{{ latestPosition.to_area }}</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ latestPosition.operator }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ formatDate(latestPosition.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="原因" :span="2">{{ latestPosition.reason || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-divider content-position="left">投放回收摘要</el-divider>
        <div v-if="currentSign && currentSign.flow_digest" class="flow-digest">
          <el-icon><Promotion /></el-icon>
          <span>{{ currentSign.flow_digest }}</span>
        </div>
        <div v-if="!(currentSign?.issue_records || []).length" class="empty-hint">暂无投放回收记录</div>
        <el-timeline v-else class="issue-timeline">
          <el-timeline-item
            v-for="rec in issueRecordsDesc"
            :key="rec.id"
            :type="rec.issue_type === 'issue' ? 'success' : 'info'"
            :timestamp="formatDate(rec.created_at)"
            size="normal"
          >
            <span class="issue-type">{{ rec.issue_type === 'issue' ? '投放' : '回收' }}</span>
            <span v-if="rec.session">· {{ rec.session }}</span>
            <span>· 执行人 {{ rec.operator }}</span>
            <span v-if="rec.receiver">· 接场人 {{ rec.receiver }}</span>
            <div v-if="rec.remark" class="issue-remark">{{ rec.remark }}</div>
          </el-timeline-item>
        </el-timeline>

        <el-divider content-position="left">关联偏差处理结果</el-divider>
        <div v-if="!relatedAnomalies.length" class="empty-hint">暂无关联偏差</div>
        <el-table v-else :data="relatedAnomalies" size="small" max-height="180">
          <el-table-column label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="getAnomalyTypeType(row.anomaly_type)" size="small">{{ getAnomalyTypeLabel(row.anomaly_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">{{ getAnomalyStatusLabel(row.current_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="处理结果" min-width="160">
            <template #default="{ row }">
              {{ row.current_status === 'closed' ? (row.final_result || '已闭环') : (row.description || '-') }}
            </template>
          </el-table-column>
        </el-table>

        <el-divider />

        <el-form :model="reviewForm" :rules="reviewRules" ref="reviewFormRef" label-width="90px">
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
            <el-input v-model="reviewForm.reason" type="textarea" :rows="2" placeholder="请输入判定依据" />
          </el-form-item>
          <el-form-item label="链路摘要" prop="summary_meta">
            <el-input
              v-model="reviewForm.summary_meta"
              type="textarea"
              :rows="3"
              placeholder="请汇总本次复核看到的完整链路结论（必填），将回写位标链路档案"
            />
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
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Warning, CircleCheck, Promotion } from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getStatusLabel, getStatusType, getAnomalyTypeLabel,
  getSceneScopeLabel, getSceneScopeType,
  getRiskLevelLabel, getRiskLevelType,
  getConsistencyStateLabel, getConsistencyStateType,
  getAnomalyTypeType, getAnomalyStatusLabel, getAnomalyStatusType
} from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const detailLoading = ref(false)
const reviewList = ref([])
const currentSign = ref(null)
const batchSigns = ref([])
const relatedAnomalies = ref([])
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
  summary_meta: [{ required: true, message: '请补全链路摘要后再提交', trigger: 'blur' }]
}

const latestPosition = computed(() => {
  const records = currentSign.value?.position_records || []
  if (!records.length) return null
  return [...records].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))[0]
})

const issueRecordsDesc = computed(() => {
  const records = currentSign.value?.issue_records || []
  return [...records].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit'
  })
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

async function openReviewDialog(row) {
  currentSign.value = { ...row }
  batchSigns.value = []
  relatedAnomalies.value = []
  reviewForm.reviewer = ''
  reviewForm.conclusion = 'restore'
  reviewForm.reason = ''
  reviewForm.summary_meta = ''
  reviewDialogVisible.value = true

  detailLoading.value = true
  try {
    // 位标完整详情（含座区校准、投放回收、复核记录、批次字段）
    const detail = await request.get(`/signs/${row.id}`)
    currentSign.value = detail

    // 同批次位标状态 + 关联偏差处理结果
    const tasks = []
    if (detail.trace_code) {
      tasks.push(
        request.get('/signs', { params: { trace_code: detail.trace_code, limit: 200 } })
          .then(list => { batchSigns.value = list || [] }),
        request.get('/anomalies', { params: { trace_code: detail.trace_code, limit: 200 } })
          .then(list => { relatedAnomalies.value = list || [] })
      )
    } else {
      tasks.push(
        request.get('/anomalies', { params: { keyword: detail.sign_number, limit: 200 } })
          .then(list => { relatedAnomalies.value = (list || []).filter(a => a.sign_id === detail.id) })
      )
    }
    await Promise.all(tasks)
  } catch (e) {
    console.error(e)
  } finally {
    detailLoading.value = false
  }
}

function buildReviewDigest() {
  // 拼接复核摘要，随复核记录留存，避免后端二次拼接
  const s = currentSign.value || {}
  const parts = []
  const conclusionLabel = { restore: '复核后可投放', reissue: '重新投放', deactivate: '隔离停用' }[reviewForm.conclusion] || reviewForm.conclusion
  parts.push(`判定：${conclusionLabel}`)
  if (s.trace_code) parts.push(`批次${s.trace_code}`)
  if (batchSigns.value.length) parts.push(`同批次${batchSigns.value.length}枚`)
  const openAnomaly = relatedAnomalies.value.filter(a => a.current_status !== 'closed').length
  parts.push(openAnomaly > 0 ? `关联未闭环偏差${openAnomaly}项` : '关联偏差已闭环')
  return parts.join(' | ')
}

async function handleReview() {
  try {
    await reviewFormRef.value.validate()
    if (!reviewForm.summary_meta || !reviewForm.summary_meta.trim()) {
      ElMessage.warning('请补全链路摘要后再提交')
      return
    }
    submitLoading.value = true
    await request.post(`/signs/${currentSign.value.id}/review`, {
      reviewer: reviewForm.reviewer,
      conclusion: reviewForm.conclusion,
      reason: reviewForm.reason,
      summary_meta: reviewForm.summary_meta,
      review_digest: buildReviewDigest()
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

.empty-hint {
  color: #909399;
  font-size: 13px;
  padding: 4px 0 8px;
}

.self-row {
  font-weight: 600;
  color: #409eff;
}

.flow-digest {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  padding: 8px 10px;
  background: #f0f9eb;
  border-radius: 4px;
  border-left: 3px solid #67c23a;
  margin-bottom: 8px;
}

.issue-timeline {
  padding: 4px 0 0 4px;
}

.issue-type {
  font-weight: 600;
  color: #303133;
}

.issue-remark {
  color: #909399;
  font-size: 12px;
  margin-top: 4px;
}

</style>
