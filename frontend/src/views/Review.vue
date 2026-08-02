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

    <el-dialog v-model="reviewDialogVisible" title="防错复核 - 全链路核查" width="860px" top="5vh">
      <div v-loading="contextLoading" class="review-dialog-body">
        <div v-if="reviewContext">
          <el-descriptions :column="3" border size="small" title="位标基础信息">
            <el-descriptions-item label="位标编号">{{ reviewContext.sign.sign_number }}</el-descriptions-item>
            <el-descriptions-item label="批次编号">{{ reviewContext.sign.batch_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="追踪码">{{ reviewContext.sign.trace_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="试听班次">{{ reviewContext.sign.applicable_session }}</el-descriptions-item>
            <el-descriptions-item label="当前座区">{{ reviewContext.sign.current_area }}</el-descriptions-item>
            <el-descriptions-item label="现场负责人">{{ reviewContext.sign.responsible_person }}</el-descriptions-item>
            <el-descriptions-item label="链路范围">
              <el-tag :type="getTraceScopeType(reviewContext.sign.scene_scope)" size="small">{{ getTraceScopeLabel(reviewContext.sign.scene_scope) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag :type="getRiskLevelType(reviewContext.sign.risk_level)" size="small" effect="plain">{{ getRiskLevelLabel(reviewContext.sign.risk_level) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="一致性">
              <el-tag :type="getConsistencyStateType(reviewContext.sign.consistency_state)" size="small">{{ getConsistencyStateLabel(reviewContext.sign.consistency_state) }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="交接备注" :span="3" v-if="reviewContext.sign.handover_note">
              {{ reviewContext.sign.handover_note }}
            </el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">同批次位标状态</el-divider>
          <div v-if="reviewContext.same_batch_signs.length > 0">
            <el-table :data="reviewContext.same_batch_signs" size="small" border>
              <el-table-column prop="sign_number" label="位标编号" width="140" />
              <el-table-column label="状态" width="110">
                <template #default="{ row }">
                  <el-tag :type="getStatusType(row.status)" size="small">{{ getStatusLabel(row.status) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="current_area" label="座区" width="120" />
              <el-table-column label="风险" width="90">
                <template #default="{ row }">
                  <el-tag :type="getRiskLevelType(row.risk_level)" size="small" effect="plain">{{ getRiskLevelLabel(row.risk_level) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="一致性" width="90">
                <template #default="{ row }">
                  <el-tag :type="getConsistencyStateType(row.consistency_state)" size="small">{{ getConsistencyStateLabel(row.consistency_state) }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="未闭环偏差" width="100">
                <template #default="{ row }">
                  <span v-if="row.has_active_anomaly" class="text-danger fw-600">有</span>
                  <span v-else class="text-muted">无</span>
                </template>
              </el-table-column>
            </el-table>
          </div>
          <el-empty v-else description="该位标无同批次其他位标" :image-size="40" />

          <el-divider content-position="left">最近座区校准</el-divider>
          <div v-if="reviewContext.latest_position">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="原座区">{{ reviewContext.latest_position.from_area }}</el-descriptions-item>
              <el-descriptions-item label="新座区">{{ reviewContext.latest_position.to_area }}</el-descriptions-item>
              <el-descriptions-item label="执行人">{{ reviewContext.latest_position.operator }}</el-descriptions-item>
              <el-descriptions-item label="校准时间">{{ formatDate(reviewContext.latest_position.created_at) }}</el-descriptions-item>
              <el-descriptions-item label="校准原因" :span="2">{{ reviewContext.latest_position.reason || '-' }}</el-descriptions-item>
            </el-descriptions>
          </div>
          <el-empty v-else description="暂无座区校准记录" :image-size="40" />

          <el-divider content-position="left">投放回收摘要</el-divider>
          <el-table v-if="reviewContext.issue_records.length > 0" :data="reviewContext.issue_records" size="small" border max-height="180">
            <el-table-column label="类型" width="80">
              <template #default="{ row }">
                <el-tag :type="row.issue_type === 'issue' ? 'success' : 'info'" size="small">
                  {{ row.issue_type === 'issue' ? '投放' : '回收' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="session" label="班次" width="120" />
            <el-table-column prop="operator" label="执行人" width="90" />
            <el-table-column prop="receiver" label="接场人" width="90" />
            <el-table-column prop="remark" label="备注" min-width="120" show-overflow-tooltip />
            <el-table-column label="时间" width="150">
              <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
            </el-table-column>
          </el-table>
          <el-empty v-else description="暂无投放回收记录" :image-size="40" />

          <el-divider content-position="left">关联偏差处理结果</el-divider>
          <el-table v-if="reviewContext.related_anomalies.length > 0" :data="reviewContext.related_anomalies" size="small" border max-height="180">
            <el-table-column label="类型" width="90">
              <template #default="{ row }">
                <el-tag :type="getAnomalyTypeType(row.anomaly_type)" size="small">{{ getAnomalyTypeLabel(row.anomaly_type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="等级" width="70">
              <template #default="{ row }">
                <el-tag :type="getAnomalyLevelType(row.anomaly_level)" size="small">{{ getAnomalyLevelLabel(row.anomaly_level) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">
                <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">{{ getAnomalyStatusLabel(row.current_status) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="description" label="描述" min-width="120" show-overflow-tooltip />
            <el-table-column prop="final_result" label="处理结果" min-width="120" show-overflow-tooltip />
          </el-table>
          <el-empty v-else description="无关联偏差" :image-size="40" />

          <el-divider content-position="left">复核摘要归档</el-divider>
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
            <el-form-item label="链路摘要" prop="summary_meta">
              <el-input
                v-model="reviewForm.summary_meta"
                type="textarea"
                :rows="3"
                placeholder="请填写批次链路核查摘要（必填，将归档至位标 summary_meta）"
              />
            </el-form-item>
            <el-form-item label="复核要点" prop="review_digest">
              <el-input
                v-model="reviewForm.review_digest"
                type="textarea"
                :rows="2"
                placeholder="简要复核结论（可选，将写入 flow_digest）"
              />
            </el-form-item>
            <el-form-item label="判定依据" prop="reason">
              <el-input v-model="reviewForm.reason" type="textarea" :rows="2" placeholder="请输入判定依据" />
            </el-form-item>
          </el-form>
        </div>
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
  getStatusLabel, getAnomalyTypeLabel,
  getAnomalyStatusLabel, getAnomalyStatusType,
  getAnomalyTypeType, getAnomalyLevelLabel, getAnomalyLevelType,
  getRiskLevelLabel, getRiskLevelType,
  getTraceScopeLabel, getTraceScopeType,
  getConsistencyStateLabel, getConsistencyStateType
} from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const contextLoading = ref(false)
const reviewList = ref([])
const currentSign = ref(null)
const reviewContext = ref(null)
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
  summary_meta: [{ required: true, message: '请填写链路核查摘要', trigger: 'blur' }],
  reason: [{ required: true, message: '请输入判定依据', trigger: 'blur' }]
}

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
  reviewDialogVisible.value = true
  reviewContext.value = null
  reviewForm.reviewer = ''
  reviewForm.conclusion = 'restore'
  reviewForm.reason = ''
  reviewForm.summary_meta = row.summary_meta || ''
  reviewForm.review_digest = ''
  contextLoading.value = true
  try {
    reviewContext.value = await request.get(`/signs/${row.id}/review-context`)
  } catch (e) {
    console.error(e)
    ElMessage.error('加载复核上下文失败')
  } finally {
    contextLoading.value = false
  }
}

async function handleReview() {
  try {
    await reviewFormRef.value.validate()
    if (!reviewForm.summary_meta.trim()) {
      ElMessage.warning('请补全链路核查摘要（summary_meta）后再提交')
      return
    }
    submitLoading.value = true
    await request.post(`/signs/${currentSign.value.id}/review`, {
      reviewer: reviewForm.reviewer,
      conclusion: reviewForm.conclusion,
      reason: reviewForm.reason,
      summary_meta: reviewForm.summary_meta,
      review_digest: reviewForm.review_digest
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
  max-height: 70vh;
  overflow-y: auto;
  padding-right: 8px;
}

.text-danger {
  color: #f56c6c;
}

.fw-600 {
  font-weight: 600;
}

.text-muted {
  color: #c0c4cc;
}
</style>
