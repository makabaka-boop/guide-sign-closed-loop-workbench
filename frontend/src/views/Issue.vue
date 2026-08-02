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

      <el-alert
        v-if="hasYellowRisk"
        title="本次投放存在黄色风险位标：可继续提交，但请确认交接链路后再投放"
        type="warning"
        :closable="false"
        show-icon
        class="risk-alert"
      />

      <div class="trace-review">
        <div class="trace-review-title">同批次链路核对</div>
        <div v-for="group in traceGroups" :key="group.trace_code" class="trace-group">
          <div class="trace-group-head">
            <span class="trace-group-code">
              <el-icon><Connection /></el-icon>
              {{ group.is_untraced ? '未关联批次链路' : group.trace_code }}
            </span>
            <div class="trace-group-tags">
              <el-tag v-if="group.shared" type="warning" size="small">批次共用链路</el-tag>
              <el-tag :type="getRiskLevelType(group.risk_level)" size="small">{{ getRiskLevelLabel(group.risk_level) }}</el-tag>
              <el-tag type="info" size="small">影响 {{ group.signs.length }} 枚</el-tag>
            </div>
          </div>
          <div class="trace-group-signs">
            <el-tag
              v-for="s in group.signs"
              :key="s.id"
              size="small"
              :type="s.risk_level === 'yellow' ? 'warning' : 'info'"
              effect="plain"
              class="trace-sign-tag"
            >
              {{ s.sign_number }}
            </el-tag>
          </div>
          <div v-if="group.handover_note" class="trace-group-note">
            <el-icon><ChatLineSquare /></el-icon>
            <span>{{ group.handover_note }}</span>
          </div>
        </div>
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
import { Search, Refresh, Promotion, Warning, CircleCheck, Connection, ChatLineSquare } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { getStatusLabel, getStatusType, getAnomalyTypeLabel, getRiskLevelLabel, getRiskLevelType } from '@/utils/statusMap'

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

// 按 trace_code 分组展示本次投放影响范围、共享链路标识、交接备注和风险等级
const traceGroups = computed(() => {
  const map = new Map()
  for (const sign of selectedSigns.value) {
    const key = sign.trace_code || '__untraced__'
    if (!map.has(key)) {
      map.set(key, {
        trace_code: key,
        is_untraced: !sign.trace_code,
        signs: [],
        shared: false,
        risk_level: 'none',
        handover_note: ''
      })
    }
    const group = map.get(key)
    group.signs.push(sign)
    if (sign.scene_scope === 'shared') group.shared = true
    // 组内风险取最高：red > yellow > none
    if (sign.risk_level === 'red') {
      group.risk_level = 'red'
    } else if (sign.risk_level === 'yellow' && group.risk_level !== 'red') {
      group.risk_level = 'yellow'
    }
    // 交接备注取组内首个非空值
    if (!group.handover_note && sign.handover_note) group.handover_note = sign.handover_note
  }
  return Array.from(map.values())
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

    // risk_level=yellow 只提醒不拦截：弹出确认后仍可提交
    if (hasYellowRisk.value) {
      try {
        await ElMessageBox.confirm(
          '本次投放包含黄色风险位标，请确认交接链路无误后继续投放。',
          '黄色风险提醒',
          { confirmButtonText: '仍然投放', cancelButtonText: '再核对一下', type: 'warning' }
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

.risk-alert {
  margin-bottom: 16px;
}

.trace-review {
  margin-top: 8px;
}

.trace-review-title {
  font-weight: 600;
  font-size: 14px;
  color: #303133;
  margin-bottom: 12px;
}

.trace-group {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 10px;
  background: #fafafa;
}

.trace-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.trace-group-code {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-weight: 600;
  color: #303133;
  font-size: 13px;
}

.trace-group-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.trace-group-signs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.trace-sign-tag {
  margin: 0;
}

.trace-group-note {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: 12px;
  color: #606266;
  border-top: 1px dashed #dcdfe6;
  padding-top: 8px;
}

</style>
