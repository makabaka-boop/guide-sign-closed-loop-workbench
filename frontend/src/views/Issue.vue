<template>
  <div class="issue-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="选择状态" style="width: 140px">
            <el-option label="待投放" value="available" />
            <el-option label="复核后可投放" value="restored" />
            <el-option label="已投放" value="issued" />
          </el-select>
        </el-form-item>
        <el-form-item label="批次">
          <el-input v-model="filterForm.batch_code" placeholder="批次编号" clearable style="width: 140px" />
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
          <span>待入场定位位标</span>
          <el-tag type="success">待投放：{{ availableCount }} 张</el-tag>
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
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
      </el-table>
    </el-card>

    <el-drawer v-model="issueDrawerVisible" title="批量入场投放" size="480px" direction="rtl">
      <div v-if="traceGroups.length" class="trace-group-section">
        <div class="trace-group-title">批次链路影响范围（{{ traceGroups.length }} 组）</div>
        <div v-for="group in traceGroups" :key="group.trace_code || '__none__'" class="trace-group-card">
          <div class="trace-group-header">
            <span class="trace-group-code">{{ group.trace_code || '未关联批次链路' }}</span>
            <div class="trace-group-tags">
              <el-tag v-if="group.scene_scope" :type="getSceneScopeType(group.scene_scope)" size="small">
                {{ getSceneScopeLabel(group.scene_scope) }}
              </el-tag>
              <el-tag v-if="group.risk_level" :type="getRiskLevelType(group.risk_level)" size="small">
                {{ getRiskLevelLabel(group.risk_level) }}
              </el-tag>
            </div>
          </div>
          <div class="trace-group-scope">
            影响范围：{{ group.signs.length }} 枚位标（{{ group.signs.map(s => s.sign_number).join('、') }}）
          </div>
          <div class="trace-group-note" :title="group.handover_note">
            交接备注：{{ group.handover_note || '-' }}
          </div>
        </div>
        <el-alert
          v-if="hasYellowRisk"
          type="warning"
          show-icon
          :closable="false"
          class="yellow-risk-alert"
          title="本次投放包含黄色风险批次：仅提醒不拦截，确认后可继续提交"
        />
      </div>
      <el-form :model="issueForm" :rules="issueRules" ref="issueFormRef" label-width="90px">
        <el-form-item label="选中数量">
          <el-tag type="success" size="large">{{ selectedSigns.length }} 张</el-tag>
        </el-form-item>
        <el-form-item label="试听班次" prop="session">
          <el-input v-model="issueForm.session" placeholder="如：2024春季班试听" />
        </el-form-item>
        <el-form-item label="接场人" prop="receiver">
          <el-input v-model="issueForm.receiver" placeholder="请输入接场人" />
        </el-form-item>
        <el-form-item label="执行人" prop="operator">
          <el-input v-model="issueForm.operator" placeholder="请输入执行人" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="issueForm.remark" type="textarea" :rows="3" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="issueDrawerVisible = false">取消</el-button>
        <el-button type="primary" @click="handleBatchIssue" :loading="submitLoading">
          确认投放
        </el-button>
      </template>
    </el-drawer>

    <div class="issue-action-bar" v-if="selectedSigns.length > 0">
      <span>已选择 {{ selectedSigns.length }} 枚待投放导引位标</span>
      <el-button type="primary" size="large" @click="issueDrawerVisible = true">
        <el-icon><Promotion /></el-icon>批量投放
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Promotion, Warning, CircleCheck } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { getStatusLabel, getStatusType, getAnomalyTypeLabel, getRiskLevelLabel, getRiskLevelType, getSceneScopeLabel, getSceneScopeType } from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const signList = ref([])
const selectedSigns = ref([])

const filterForm = reactive({
  status: 'available',
  batch_code: '',
  keyword: ''
})

const availableCount = computed(() => {
  return signList.value.filter(s => s.status === 'available' || s.status === 'restored').length
})

// 按 trace_code 分组展示本次批量投放的批次链路影响范围
const traceGroups = computed(() => {
  const groups = {}
  selectedSigns.value.forEach(sign => {
    const key = sign.trace_code || ''
    if (!groups[key]) {
      groups[key] = { trace_code: key, signs: [], scene_scope: '', handover_note: '', risk_level: '' }
    }
    groups[key].signs.push(sign)
  })
  return Object.values(groups).map(group => ({
    ...group,
    scene_scope: group.signs.find(s => s.scene_scope)?.scene_scope || '',
    handover_note: group.signs.find(s => s.handover_note)?.handover_note || '',
    risk_level: group.signs.find(s => s.risk_level)?.risk_level || ''
  }))
})

const hasYellowRisk = computed(() => {
  return selectedSigns.value.some(s => s.risk_level === 'yellow')
})

const issueDrawerVisible = ref(false)
const issueFormRef = ref(null)
const issueForm = reactive({
  session: '',
  receiver: '',
  operator: '',
  remark: ''
})
const issueRules = {
  session: [{ required: true, message: '请输入试听班次', trigger: 'blur' }],
  receiver: [{ required: true, message: '请输入接场人', trigger: 'blur' }],
  operator: [{ required: true, message: '请输入执行人', trigger: 'blur' }]
}

function checkSelectable(row) {
  return (row.status === 'available' || row.status === 'restored') && !row.has_active_anomaly
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
  filterForm.status = 'available'
  filterForm.batch_code = ''
  filterForm.keyword = ''
  fetchList()
}

async function handleBatchIssue() {
  try {
    await issueFormRef.value.validate()
    if (selectedSigns.value.length === 0) {
      ElMessage.warning('请选择要投放的导引位标')
      return
    }

    // 黄色风险只提醒不拦截，确认后仍可继续提交
    if (hasYellowRisk.value) {
      const yellowCodes = traceGroups.value
        .filter(g => g.risk_level === 'yellow')
        .map(g => g.trace_code || '未关联批次链路')
      try {
        await ElMessageBox.confirm(
          `本次投放涉及黄色风险批次链路（${yellowCodes.join('、')}），黄色风险仅提醒不拦截。确认继续投放？`,
          '风险提醒',
          { confirmButtonText: '继续投放', cancelButtonText: '再核对一下', type: 'warning' }
        )
      } catch {
        return
      }
    }

    submitLoading.value = true
    let successCount = 0
    let failCount = 0
    
    for (const sign of selectedSigns.value) {
      try {
        await request.post(`/signs/${sign.id}/issue`, {
          receiver: issueForm.receiver,
          session: issueForm.session,
          operator: issueForm.operator,
          remark: issueForm.remark
        })
        successCount++
      } catch (e) {
        failCount++
      }
    }
    
    if (successCount > 0) {
      ElMessage.success(`成功投放 ${successCount} 枚导引位标${failCount > 0 ? `，失败 ${failCount} 枚` : ''}`)
    } else {
      ElMessage.error('投放失败')
    }
    
    issueDrawerVisible.value = false
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
.issue-page {
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

.trace-group-section {
  margin-bottom: 16px;
}

.trace-group-title {
  font-size: 13px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.trace-group-card {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fafafa;
}

.trace-group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.trace-group-code {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}

.trace-group-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.trace-group-scope {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
  word-break: break-all;
}

.trace-group-note {
  font-size: 12px;
  color: #909399;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.yellow-risk-alert {
  margin-top: 8px;
}

.issue-action-bar {
  position: fixed;
  bottom: 20px;
  right: 40px;
  background: white;
  padding: 12px 20px;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 16px;
  z-index: 100;
}

.issue-action-bar span {
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
