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

    <el-drawer v-model="issueDrawerVisible" title="批量入场投放" size="520px" direction="rtl">
      <div class="drawer-body">
        <el-form :model="issueForm" :rules="issueRules" ref="issueFormRef" label-width="90px">
          <el-form-item label="选中数量">
            <el-tag type="success" size="large">{{ selectedSigns.length }} 张</el-tag>
            <el-tag v-if="hasYellowRisk" type="warning" size="large" effect="plain" class="risk-summary-tag">
              <el-icon style="vertical-align: -2px"><Warning /></el-icon>
              含 yellow 风险批次
            </el-tag>
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
          <el-form-item label="交接备注">
            <el-input
              v-model="issueForm.handover_note"
              type="textarea"
              :rows="2"
              placeholder="可选，将写入投放记录摘要并刷新 flow_digest"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="issueForm.remark" type="textarea" :rows="2" placeholder="可选" />
          </el-form-item>
        </el-form>

        <div class="trace-impact">
          <div class="trace-impact-title">
            <el-icon><Connection /></el-icon>
            本次投放影响的批次链路
            <span class="trace-impact-sub">（按 trace_code 聚合）</span>
          </div>

          <el-alert
            v-if="hasYellowRisk"
            type="warning"
            :closable="false"
            show-icon
            class="yellow-alert"
            title="检测到 risk_level=yellow"
            description="yellow 风险只做提醒不拦截流转，提交时将弹出确认提示，请在交接备注中说明处置情况。"
          />

          <div v-if="traceGroups.length === 0" class="no-trace-hint">
            选中位标未设置 trace_code，将仅更新单枚位标状态。
          </div>

          <div v-for="group in traceGroups" :key="group.key" class="trace-group">
            <div class="trace-group-header">
              <span class="trace-group-code" :title="group.trace_code">
                {{ group.trace_code || '未设置追踪码' }}
              </span>
              <el-tag
                :type="getRiskLevelType(group.risk_level)"
                size="small"
                effect="dark"
              >
                {{ getRiskLevelLabel(group.risk_level) }}
              </el-tag>
              <el-tag
                v-if="group.scene_scope === 'shared'"
                type="warning"
                size="small"
                effect="plain"
              >
                共享链路
              </el-tag>
              <el-tag
                :type="getConsistencyStateType(group.consistency_state)"
                size="small"
                effect="plain"
              >
                一致性·{{ getConsistencyStateLabel(group.consistency_state) }}
              </el-tag>
            </div>

            <div class="trace-group-meta">
              <span class="meta-item">
                <span class="meta-label">本组选中：</span>
                <b>{{ group.selectedCount }}</b> 枚
              </span>
              <span class="meta-item">
                <span class="meta-label">链路总位标：</span>
                <b>{{ group.linkedTotal ?? group.selectedCount }}</b> 枚
              </span>
              <span v-if="group.scene_scope === 'shared'" class="meta-item shared-hint">
                <el-icon><Share /></el-icon>
                同批次多人共用链路
              </span>
            </div>

            <div class="trace-group-note">
              <span class="note-label">交接备注：</span>
              <span class="note-text">{{ group.handover_note || '（同批次暂无交接备注，可在上方填写）' }}</span>
            </div>

            <div class="trace-group-signs">
              <el-tag
                v-for="sign in group.signs"
                :key="sign.id"
                size="small"
                :type="sign.has_active_anomaly ? 'danger' : 'info'"
                class="sign-tag"
              >
                {{ sign.sign_number }}
                <span v-if="sign.current_area" class="sign-area">·{{ sign.current_area }}</span>
              </el-tag>
            </div>
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
import { Search, Refresh, Promotion, Warning, CircleCheck, Connection, Share } from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getStatusLabel, getStatusType, getAnomalyTypeLabel,
  getRiskLevelLabel, getRiskLevelType,
  getSceneScopeLabel, getSceneScopeType,
  getConsistencyStateLabel, getConsistencyStateType
} from '@/utils/statusMap'

const RISK_RANK = { green: 0, yellow: 1, red: 2 }
const CONSISTENCY_RANK = { ok: 0, warn: 1, conflict: 2 }

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

const issueDrawerVisible = ref(false)
const issueFormRef = ref(null)
const issueForm = reactive({
  session: '',
  receiver: '',
  operator: '',
  handover_note: '',
  remark: ''
})
const issueRules = {
  session: [{ required: true, message: '请输入试听班次', trigger: 'blur' }],
  receiver: [{ required: true, message: '请输入接场人', trigger: 'blur' }],
  operator: [{ required: true, message: '请输入执行人', trigger: 'blur' }]
}

function maxByRank(values, rankMap, fallback) {
  let best = fallback
  let bestRank = -1
  values.forEach((value) => {
    if (!value) return
    const rank = rankMap[value] ?? -1
    if (rank > bestRank) {
      bestRank = rank
      best = value
    }
  })
  return best
}

const traceGroups = computed(() => {
  const map = new Map()
  selectedSigns.value.forEach((sign) => {
    const key = sign.trace_code ? sign.trace_code.trim() : ''
    if (!map.has(key)) {
      map.set(key, {
        key: key || '__no_trace__',
        trace_code: key,
        signs: [],
        handover_notes: []
      })
    }
    const group = map.get(key)
    group.signs.push(sign)
    if (sign.handover_note && sign.handover_note.trim()) {
      group.handover_notes.push(sign.handover_note.trim())
    }
  })

  const result = []
  map.forEach((group) => {
    const risk_level = maxByRank(
      group.signs.map((s) => s.risk_level),
      RISK_RANK,
      'green'
    )
    const consistency_state = maxByRank(
      group.signs.map((s) => s.consistency_state),
      CONSISTENCY_RANK,
      'ok'
    )
    const scene_scope = group.signs.some((s) => (s.scene_scope || 'private') === 'shared')
      ? 'shared'
      : 'private'

    const uniqueNotes = Array.from(new Set(group.handover_notes))
    result.push({
      key: group.key,
      trace_code: group.trace_code,
      signs: group.signs,
      selectedCount: group.signs.length,
      linkedTotal: group.trace_code ? group.signs.length : group.signs.length,
      risk_level,
      consistency_state,
      scene_scope,
      handover_note: uniqueNotes.join('；')
    })
  })

  result.sort((a, b) => {
    const riskDiff = (RISK_RANK[b.risk_level] || 0) - (RISK_RANK[a.risk_level] || 0)
    if (riskDiff !== 0) return riskDiff
    return b.selectedCount - a.selectedCount
  })

  return result
})

const hasYellowRisk = computed(() => {
  return traceGroups.value.some(
    (group) => group.risk_level === 'yellow' && group.trace_code
  )
})

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

    if (hasYellowRisk.value) {
      try {
        await ElMessageBox.confirm(
          '本次选中的位标中包含 risk_level=yellow 的批次。yellow 仅做提醒不拦截流转，但请确认已核对共享链路与交接备注，是否继续投放？',
          '检测到 yellow 风险提醒',
          {
            confirmButtonText: '继续投放',
            cancelButtonText: '再检查一下',
            type: 'warning'
          }
        )
      } catch (e) {
        return
      }
    }

    submitLoading.value = true
    let successCount = 0
    let failCount = 0
    const updatedSigns = []

    for (const sign of selectedSigns.value) {
      try {
        const updated = await request.post(`/signs/${sign.id}/issue`, {
          receiver: issueForm.receiver,
          session: issueForm.session,
          operator: issueForm.operator,
          remark: issueForm.remark,
          handover_note: issueForm.handover_note
        })
        if (updated && updated.flow_digest) {
          updatedSigns.push(updated)
        }
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
    issueForm.session = ''
    issueForm.receiver = ''
    issueForm.operator = ''
    issueForm.handover_note = ''
    issueForm.remark = ''
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

.drawer-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-summary-tag {
  margin-left: 8px;
}

.trace-impact {
  margin-top: 8px;
  padding: 14px;
  background: #f7f8fa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

.trace-impact-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 10px;
}

.trace-impact-sub {
  color: #909399;
  font-size: 12px;
  font-weight: normal;
}

.yellow-alert {
  margin-bottom: 12px;
}

.no-trace-hint {
  color: #909399;
  font-size: 13px;
  padding: 12px 0;
  text-align: center;
}

.trace-group {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 10px;
}

.trace-group:last-child {
  margin-bottom: 0;
}

.trace-group-header {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.trace-group-code {
  font-weight: 600;
  color: #303133;
  font-size: 13px;
  margin-right: auto;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-group-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  font-size: 12px;
  color: #606266;
  margin-bottom: 6px;
}

.meta-item b {
  color: #303133;
  font-weight: 600;
}

.meta-item.shared-hint {
  color: #e6a23c;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.trace-group-note {
  font-size: 12px;
  color: #606266;
  margin-bottom: 8px;
  line-height: 1.5;
}

.note-label {
  color: #909399;
}

.note-text {
  word-break: break-all;
}

.trace-group-signs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.sign-tag {
  font-weight: 500;
}

.sign-area {
  opacity: 0.75;
  margin-left: 2px;
}
</style>
