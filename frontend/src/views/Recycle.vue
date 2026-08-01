<template>
  <div class="recycle-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" style="width: 140px">
            <el-option label="已投放" value="issued" />
            <el-option label="待回收核验" value="pending_recycle" />
          </el-select>
        </el-form-item>
        <el-form-item label="班次">
          <el-input v-model="filterForm.applicable_session" placeholder="班次" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="编号/座区" clearable style="width: 160px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="fetchList">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="resetFilter">
            <el-icon><Refresh /></el-icon>重置
          </el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>散场归位核验队列</span>
          <el-tag type="warning">待回收核验：{{ pendingRecycleCount }} 张</el-tag>
        </div>
      </template>
      <el-table :data="signList" v-loading="loading" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="55" :selectable="checkSelectable" />
        <el-table-column prop="sign_number" label="位标编号" width="140">
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
            <el-tag :type="getStatusType(row.status)">{{ getStatusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="偏差提示" width="160">
          <template #default="{ row }">
            <span v-if="row.has_active_anomaly" class="anomaly-warning">
              <el-icon color="#f56c6c"><Warning /></el-icon>
              {{ row.active_anomaly_count }} 项待处置
            </span>
            <span v-else class="no-anomaly">
              <el-icon color="#67c23a"><CircleCheck /></el-icon>
              正常
            </span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button link type="primary" @click="markPendingRecycle(row)" v-if="row.status === 'issued'">
              标记待回收核验
            </el-button>
            <el-button link type="success" @click="openRecycleDialog(row)" v-if="row.status === 'pending_recycle'">
              回收
            </el-button>
            <el-button link type="warning" @click="openRecycleDialog(row)" v-if="row.status === 'issued'">
              直接回收
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="recycleDialogVisible" title="回收节点登记" width="450px">
      <el-form :model="recycleForm" :rules="recycleRules" ref="recycleFormRef" label-width="100px">
        <el-form-item label="位标编号">
          <el-input :value="currentSign?.sign_number" disabled />
        </el-form-item>
        <el-form-item label="当前状态">
          <el-tag :type="getStatusType(currentSign?.status)">{{ getStatusLabel(currentSign?.status) }}</el-tag>
        </el-form-item>
        <el-form-item label="执行人" prop="operator">
          <el-input v-model="recycleForm.operator" placeholder="请输入执行人" />
        </el-form-item>
        <el-form-item label="回收后状态">
          <el-radio-group v-model="recycleForm.to_pending_review">
            <el-radio :value="false">直接归位（待投放）</el-radio>
            <el-radio :value="true">转入待防错复核</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="recycleForm.remark" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recycleDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRecycle" :loading="submitLoading">确认回收</el-button>
      </template>
    </el-dialog>

    <div class="recycle-action-bar" v-if="selectedSigns.length > 0">
      <span>已选择 {{ selectedSigns.length }} 枚导引位标</span>
      <el-button type="success" @click="batchRecycle(false)">
        <el-icon><Refresh /></el-icon>批量回收
      </el-button>
      <el-button type="warning" @click="batchRecycle(true)">
        <el-icon><Warning /></el-icon>批量转待防错复核
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Warning, CircleCheck } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { getStatusLabel, getStatusType, getAnomalyTypeLabel } from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const signList = ref([])
const selectedSigns = ref([])
const currentSign = ref(null)

const filterForm = reactive({
  status: 'issued',
  applicable_session: '',
  keyword: ''
})

const pendingRecycleCount = computed(() => {
  return signList.value.filter(s => s.status === 'issued' || s.status === 'pending_recycle').length
})

const recycleDialogVisible = ref(false)
const recycleFormRef = ref(null)
const recycleForm = reactive({
  operator: '',
  to_pending_review: false,
  remark: ''
})
const recycleRules = {
  operator: [{ required: true, message: '请输入执行人', trigger: 'blur' }]
}

function checkSelectable(row) {
  return row.status === 'issued' || row.status === 'pending_recycle'
}

function handleSelectionChange(selection) {
  selectedSigns.value = selection.filter(s => checkSelectable(s))
}

async function fetchList() {
  loading.value = true
  try {
    const params = {}
    Object.keys(filterForm).forEach(key => {
      if (filterForm[key]) params[key] = filterForm[key]
    })
    signList.value = await request.get('/signs', { params })
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filterForm.status = 'issued'
  filterForm.applicable_session = ''
  filterForm.keyword = ''
  fetchList()
}

async function markPendingRecycle(row) {
  try {
    await request.post(`/signs/${row.id}/pending-recycle`)
    ElMessage.success('已标记为待回收核验')
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  }
}

function openRecycleDialog(row) {
  currentSign.value = { ...row }
  recycleDialogVisible.value = true
  recycleForm.operator = ''
  recycleForm.to_pending_review = false
  recycleForm.remark = ''
}

async function handleRecycle() {
  try {
    await recycleFormRef.value.validate()
    submitLoading.value = true
    await request.post(`/signs/${currentSign.value.id}/recycle`, recycleForm)
    ElMessage.success('回收成功')
    recycleDialogVisible.value = false
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

async function batchRecycle(toReview) {
  try {
    await ElMessageBox.confirm(
      `确定要批量${toReview ? '转入待防错复核' : '回收'} ${selectedSigns.value.length} 枚导引位标吗？`,
      '提示',
      { type: 'warning' }
    )
    
    const operator = '批量操作'
    let successCount = 0
    let failCount = 0
    
    for (const sign of selectedSigns.value) {
      try {
        await request.post(`/signs/${sign.id}/recycle`, {
          operator,
          to_pending_review: toReview,
          remark: '批量操作'
        })
        successCount++
      } catch (e) {
        failCount++
      }
    }
    
    if (successCount > 0) {
      ElMessage.success(`成功${toReview ? '转入待防错复核' : '回收'} ${successCount} 枚${failCount > 0 ? `，失败 ${failCount} 枚` : ''}`)
    }
    fetchList()
  } catch (e) {
    if (e !== 'cancel') {
      console.error(e)
    }
  }
}

onMounted(() => {
  fetchList()
})
</script>

<style scoped>
.recycle-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 80px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.recycle-action-bar {
  position: fixed;
  bottom: 20px;
  right: 40px;
  background: white;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 100;
}

.recycle-action-bar span {
  color: #606266;
  font-size: 14px;
}

.sign-number-with-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.anomaly-tag {
  margin-left: 4px;
}

.anomaly-warning {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #f56c6c;
  font-size: 13px;
  font-weight: 500;
}

.no-anomaly {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: #67c23a;
  font-size: 13px;
}
</style>
