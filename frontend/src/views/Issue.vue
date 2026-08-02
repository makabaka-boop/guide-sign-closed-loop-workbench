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
        <el-table-column prop="trace_code" label="追踪码" width="130" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.trace_code">{{ row.trace_code }}</span>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="applicable_session" label="试听班次" width="140" />
        <el-table-column prop="current_area" label="目标座区" width="140" />
        <el-table-column prop="responsible_person" label="现场负责人" width="120" />
        <el-table-column label="链路范围" width="110">
          <template #default="{ row }">
            <el-tag :type="getTraceScopeType(row.scene_scope)" size="small">{{ getTraceScopeLabel(row.scene_scope) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="100">
          <template #default="{ row }">
            <el-tag :type="getRiskLevelType(row.risk_level)" size="small" effect="plain">{{ getRiskLevelLabel(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
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

    <el-drawer v-model="issueDrawerVisible" title="批量入场投放" size="520px" direction="rtl">
      <div class="drawer-content">
        <div class="drawer-summary">
          <el-tag type="success" size="large">本次选中 {{ selectedSigns.length }} 张</el-tag>
          <el-tag v-if="hasYellowRisk" type="warning" size="large">
            <el-icon><WarningFilled /></el-icon> 含黄色预警批次
          </el-tag>
        </div>

        <el-divider content-position="left">链路影响范围</el-divider>

        <div class="trace-groups">
          <div
            v-for="group in traceGroups"
            :key="group.key"
            class="trace-group"
            :class="{
              'trace-risk-yellow': group.maxRisk === 'yellow',
              'trace-risk-red': group.maxRisk === 'red',
              'trace-shared': group.hasShared
            }"
          >
            <div class="trace-group-header">
              <div class="trace-group-title">
                <el-icon v-if="group.key !== '__untracked__'" class="trace-icon"><Connection /></el-icon>
                <span class="trace-code">{{ group.key === '__untracked__' ? '未绑定追踪码' : group.key }}</span>
                <el-tag v-if="group.hasShared" type="warning" size="small" effect="plain">同批次共用链路</el-tag>
              </div>
              <div class="trace-group-tags">
                <el-tag :type="getRiskLevelType(group.maxRisk)" size="small" effect="dark">{{ getRiskLevelLabel(group.maxRisk) }}</el-tag>
              </div>
            </div>
            <div class="trace-group-meta">
              <span class="meta-item">
                <span class="meta-label">本次投放</span>
                <span class="meta-value">{{ group.signs.length }} 张</span>
              </span>
              <span class="meta-item" v-if="group.key !== '__untracked__'">
                <span class="meta-label">链路在册</span>
                <span class="meta-value">{{ group.totalInTrace }} 张</span>
              </span>
              <span class="meta-item">
                <span class="meta-label">涉及座区</span>
                <span class="meta-value">{{ group.areas.join('、') || '-' }}</span>
              </span>
            </div>
            <div class="trace-group-note" v-if="group.handoverNote">
              <el-icon><InfoFilled /></el-icon>
              <span>交接备注：{{ group.handoverNote }}</span>
            </div>
            <div class="trace-group-signs">
              <el-tag
                v-for="sign in group.signs"
                :key="sign.id"
                size="small"
                class="sign-tag"
              >
                {{ sign.sign_number }}（{{ sign.current_area }}）
              </el-tag>
            </div>
          </div>
        </div>

        <el-divider content-position="left">投放信息</el-divider>

        <el-form :model="issueForm" :rules="issueRules" ref="issueFormRef" label-width="90px">
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
      </div>
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
import { Search, Refresh, Promotion, Warning, CircleCheck, WarningFilled, Connection, InfoFilled } from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getStatusLabel, getStatusType, getAnomalyTypeLabel,
  getRiskLevelLabel, getRiskLevelType,
  getTraceScopeLabel, getTraceScopeType
} from '@/utils/statusMap'

const RISK_RANK = { normal: 0, yellow: 1, red: 2 }

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

const traceGroups = computed(() => {
  const groups = {}
  for (const sign of selectedSigns.value) {
    const key = sign.trace_code || '__untracked__'
    if (!groups[key]) {
      groups[key] = []
    }
    groups[key].push(sign)
  }

  return Object.entries(groups).map(([key, signs]) => {
    const maxRisk = signs.reduce((max, s) => {
      return RISK_RANK[s.risk_level] > RISK_RANK[max] ? (s.risk_level || 'normal') : max
    }, 'normal')
    const hasShared = signs.some(s => s.scene_scope === 'shared')
    const handoverNote = signs.map(s => s.handover_note).find(n => n) || ''
    const areas = [...new Set(signs.map(s => s.current_area).filter(Boolean))]
    const totalInTrace = key !== '__untracked__'
      ? signList.value.filter(s => s.trace_code === key).length
      : signs.length

    return { key, signs, maxRisk, hasShared, handoverNote, areas, totalInTrace }
  }).sort((a, b) => RISK_RANK[b.maxRisk] - RISK_RANK[a.maxRisk])
})

const hasYellowRisk = computed(() => {
  return traceGroups.value.some(g => g.maxRisk === 'yellow')
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

    const yellowGroups = traceGroups.value.filter(g => g.maxRisk === 'yellow')
    if (yellowGroups.length > 0) {
      const yellowCodes = yellowGroups.map(g => g.key === '__untracked__' ? '未绑定追踪码' : g.key).join('、')
      try {
        await ElMessageBox.confirm(
          `以下批次存在黄色预警：${yellowCodes}。黄色预警仅提醒不拦截，请确认现场链路完整后继续投放。`,
          '黄色预警确认',
          {
            confirmButtonText: '确认继续投放',
            cancelButtonText: '取消',
            type: 'warning',
            confirmButtonClass: 'el-button--warning'
          }
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

.drawer-content {
  padding: 0 4px;
}

.drawer-summary {
  display: flex;
  gap: 8px;
  align-items: center;
}

.trace-groups {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trace-group {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px;
  background: #fff;
}

.trace-group.trace-risk-yellow {
  border-left: 4px solid #e6a23c;
  background: #fdf6ec;
}

.trace-group.trace-risk-red {
  border-left: 4px solid #f56c6c;
  background: #fef0f0;
}

.trace-group.trace-shared {
  border-style: dashed;
}

.trace-group-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.trace-group-title {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.trace-icon {
  color: #409eff;
}

.trace-code {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}

.trace-group-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.meta-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
}

.meta-label {
  color: #909399;
}

.meta-value {
  color: #303133;
  font-weight: 500;
}

.trace-group-note {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  font-size: 12px;
  color: #e6a23c;
  background: #faecd8;
  padding: 6px 8px;
  border-radius: 4px;
  margin-bottom: 8px;
  word-break: break-all;
}

.trace-group-signs {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sign-tag {
  max-width: 100%;
}

.text-muted {
  color: #c0c4cc;
}
</style>
