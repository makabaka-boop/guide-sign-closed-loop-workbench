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

    <el-dialog v-model="reviewDialogVisible" title="防错复核登记" width="760px">
      <div v-loading="detailLoading" class="review-dialog-body" v-if="currentSign">
        <el-divider content-position="left">位标基础信息</el-divider>
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="位标编号">{{ currentSign.sign_number }}</el-descriptions-item>
          <el-descriptions-item label="批次编号">{{ currentSign.batch_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="试听班次">{{ currentSign.applicable_session }}</el-descriptions-item>
          <el-descriptions-item label="当前座区">{{ currentSign.current_area }}</el-descriptions-item>
          <el-descriptions-item label="现场负责人">{{ currentSign.responsible_person }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="getStatusType(currentSign.status)" size="small">{{ getStatusLabel(currentSign.status) }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="追踪码">{{ currentSign.trace_code || '-' }}</el-descriptions-item>
          <el-descriptions-item label="场景范围">
            <el-tag v-if="currentSign.scene_scope" :type="getSceneScopeType(currentSign.scene_scope)" size="small">{{ getSceneScopeLabel(currentSign.scene_scope) }}</el-tag>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="风险等级">
            <el-tag v-if="currentSign.risk_level" :type="getRiskLevelType(currentSign.risk_level)" size="small">{{ getRiskLevelLabel(currentSign.risk_level) }}</el-tag>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="链路一致性">
            <el-tag v-if="currentSign.consistency_state" :type="getConsistencyStateType(currentSign.consistency_state)" size="small">{{ getConsistencyStateLabel(currentSign.consistency_state) }}</el-tag>
            <span v-else>-</span>
          </el-descriptions-item>
          <el-descriptions-item label="交接说明" :span="2">{{ currentSign.handover_note || '-' }}</el-descriptions-item>
          <el-descriptions-item label="汇总元信息" :span="2">{{ currentSign.summary_meta || '-' }}</el-descriptions-item>
          <el-descriptions-item label="链路摘要" :span="2">{{ currentSign.flow_digest || '-' }}</el-descriptions-item>
        </el-descriptions>

        <template v-if="currentSign.trace_code">
          <el-divider content-position="left">同批次位标状态（{{ batchSigns.length }} 枚）</el-divider>
          <el-table :data="batchSigns" size="small" max-height="180">
            <el-table-column label="位标编号" width="140">
              <template #default="{ row }">
                <span :class="{ 'current-sign-mark': row.id === currentSign.id }">
                  {{ row.sign_number }}{{ row.id === currentSign.id ? '（本位标）' : '' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="current_area" label="目标座区" width="140" />
            <el-table-column prop="responsible_person" label="现场负责人" width="110" />
            <el-table-column label="一致性" width="110">
              <template #default="{ row }">
                <el-tag v-if="row.consistency_state" :type="getConsistencyStateType(row.consistency_state)" size="small">{{ getConsistencyStateLabel(row.consistency_state) }}</el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </template>

        <el-divider content-position="left">最近座区校准</el-divider>
        <el-descriptions v-if="latestPosition" :column="2" border size="small">
          <el-descriptions-item label="原座区">{{ latestPosition.from_area }}</el-descriptions-item>
          <el-descriptions-item label="新座区">{{ latestPosition.to_area }}</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ latestPosition.operator }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ formatDate(latestPosition.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="原因" :span="2">{{ latestPosition.reason || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-else class="empty-tip">暂无座区校准记录</div>

        <el-divider content-position="left">投放回收摘要</el-divider>
        <el-descriptions v-if="latestIssue" :column="2" border size="small">
          <el-descriptions-item label="类型">
            <el-tag :type="latestIssue.issue_type === 'issue' ? 'success' : 'info'" size="small">
              {{ latestIssue.issue_type === 'issue' ? '投放' : '回收' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="班次">{{ latestIssue.session || '-' }}</el-descriptions-item>
          <el-descriptions-item label="执行人">{{ latestIssue.operator }}</el-descriptions-item>
          <el-descriptions-item label="接场人">{{ latestIssue.receiver || '-' }}</el-descriptions-item>
          <el-descriptions-item label="摘要" :span="2">{{ latestIssue.remark || '-' }}</el-descriptions-item>
        </el-descriptions>
        <div v-else class="empty-tip">暂无投放回收记录</div>

        <el-divider content-position="left">关联偏差处理结果（{{ batchAnomalies.length }} 条）</el-divider>
        <el-table v-if="batchAnomalies.length" :data="batchAnomalies" size="small" max-height="180">
          <el-table-column prop="id" label="偏差编号" width="90" />
          <el-table-column label="类型" width="110">
            <template #default="{ row }">
              <el-tag :type="getAnomalyTypeType(row.anomaly_type)" size="small">{{ getAnomalyTypeLabel(row.anomaly_type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">{{ getAnomalyStatusLabel(row.current_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="final_result" label="处理结果" min-width="160" show-overflow-tooltip>
            <template #default="{ row }">{{ row.final_result || '-' }}</template>
          </el-table-column>
        </el-table>
        <div v-else class="empty-tip">同批次无关联偏差记录</div>

        <el-divider content-position="left">复核登记</el-divider>
        <el-form :model="reviewForm" :rules="reviewRules" ref="reviewFormRef" label-width="110px">
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
          <el-form-item label="汇总元信息" prop="summary_meta">
            <el-input v-model="reviewForm.summary_meta" placeholder="批次汇总元信息（必填，可基于链路信息补全）" />
          </el-form-item>
          <el-form-item label="复核摘要" prop="review_digest">
            <el-input v-model="reviewForm.review_digest" placeholder="复核结论摘要，将回写位标链路摘要（可选）" />
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
import { Refresh, Warning, CircleCheck } from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getStatusLabel, getStatusType, getAnomalyTypeLabel, getAnomalyTypeType,
  getAnomalyStatusLabel, getAnomalyStatusType,
  getRiskLevelLabel, getRiskLevelType,
  getSceneScopeLabel, getSceneScopeType,
  getConsistencyStateLabel, getConsistencyStateType
} from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const detailLoading = ref(false)
const reviewList = ref([])
const currentSign = ref(null)
const batchSigns = ref([])
const batchAnomalies = ref([])
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
  summary_meta: '',
  review_digest: ''
})
const reviewRules = {
  reviewer: [{ required: true, message: '请输入复核员', trigger: 'blur' }],
  conclusion: [{ required: true, message: '请选择复核判定', trigger: 'change' }],
  reason: [{ required: true, message: '请输入判定依据', trigger: 'blur' }],
  summary_meta: [{ required: true, message: '请补全汇总元信息后再提交', trigger: 'blur' }]
}

const latestPosition = computed(() => {
  const records = currentSign.value?.position_records || []
  return records.length ? records[records.length - 1] : null
})

const latestIssue = computed(() => {
  const records = currentSign.value?.issue_records || []
  return records.length ? records[records.length - 1] : null
})

function formatDate(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
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
  batchAnomalies.value = []
  reviewForm.reviewer = ''
  reviewForm.conclusion = 'restore'
  reviewForm.reason = ''
  reviewForm.summary_meta = row.summary_meta || ''
  reviewForm.review_digest = ''
  reviewDialogVisible.value = true

  detailLoading.value = true
  try {
    const detail = await request.get(`/signs/${row.id}`)
    currentSign.value = detail
    if (detail.trace_code) {
      const [signs, anomalies] = await Promise.all([
        request.get('/signs', { params: { trace_code: detail.trace_code, limit: 200 } }),
        request.get('/anomalies', { params: { trace_code: detail.trace_code, limit: 200 } })
      ])
      batchSigns.value = signs
      batchAnomalies.value = anomalies
    }
  } catch (e) {
    console.error(e)
  } finally {
    detailLoading.value = false
  }
}

async function handleReview() {
  try {
    await reviewFormRef.value.validate()
    if (!reviewForm.summary_meta.trim()) {
      ElMessage.warning('请补全汇总元信息（summary_meta）后再提交')
      return
    }
    submitLoading.value = true
    await request.post(`/signs/${currentSign.value.id}/review`, reviewForm)
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

.review-dialog-body :deep(.el-divider__text) {
  font-weight: 600;
  color: #303133;
}

.empty-tip {
  color: #909399;
  font-size: 13px;
  padding: 8px 0;
}

.current-sign-mark {
  font-weight: 600;
  color: #409eff;
}
</style>
