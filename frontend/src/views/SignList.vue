<template>
  <div class="sign-list">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable style="width: 140px">
            <el-option v-for="(item, key) in STATUS_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="批次">
          <el-input v-model="filterForm.batch_code" placeholder="批次编号" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="追踪码">
          <el-input v-model="filterForm.trace_code" placeholder="批次追踪码" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="使用场景">
          <el-select v-model="filterForm.scene_scope" placeholder="全部场景" clearable style="width: 140px">
            <el-option v-for="(item, key) in SCENE_SCOPE_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="filterForm.risk_level" placeholder="全部风险" clearable style="width: 140px">
            <el-option v-for="(item, key) in RISK_LEVEL_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="一致性">
          <el-select v-model="filterForm.consistency_state" placeholder="全部一致性" clearable style="width: 140px">
            <el-option v-for="(item, key) in CONSISTENCY_STATE_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="试听班次">
          <el-input v-model="filterForm.applicable_session" placeholder="班次" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="现场负责人">
          <el-input v-model="filterForm.responsible_person" placeholder="现场负责人" clearable style="width: 140px" />
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

    <el-card class="table-card">
      <template #header>
        <div class="card-header">
          <span>位标准入核验清单</span>
          <el-button type="primary" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>新增导引位标
          </el-button>
        </div>
      </template>
      <el-table :data="signList" v-loading="loading" stripe style="width: 100%">
        <el-table-column label="位标编号" width="140">
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
        <el-table-column prop="trace_code" label="追踪码" width="120">
          <template #default="{ row }">
            <span>{{ row.trace_code || '-' }}</span>
          </template>
        </el-table-column>
        <el-table-column label="使用场景" width="120">
          <template #default="{ row }">
            <el-tag :type="getSceneScopeType(row.scene_scope)" size="small">{{ getSceneScopeLabel(row.scene_scope) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险等级" width="110">
          <template #default="{ row }">
            <el-tag :type="getRiskLevelType(row.risk_level)" size="small">{{ getRiskLevelLabel(row.risk_level) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="一致性" width="120">
          <template #default="{ row }">
            <el-tooltip
              v-if="row.consistency_state === 'warn'"
              content="存在批次链路冲突，允许继续流转但请核对交接说明"
              placement="top"
            >
              <el-tag :type="getConsistencyStateType(row.consistency_state)" size="small">
                {{ getConsistencyStateLabel(row.consistency_state) }}
              </el-tag>
            </el-tooltip>
            <el-tag v-else :type="getConsistencyStateType(row.consistency_state)" size="small">
              {{ getConsistencyStateLabel(row.consistency_state) }}
            </el-tag>
          </template>
        </el-table-column>
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
              <el-icon><Warning /></el-icon>
              {{ (row.active_anomaly_types || []).length }}项待处置
            </span>
            <span v-else class="no-anomaly">
              <el-icon><CircleCheck /></el-icon>
              正常
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="remark" label="备注" min-width="150" show-overflow-tooltip />
        <el-table-column label="操作" width="360" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="openDetailDialog(row)">详情</el-button>
            <el-button link type="primary" @click="openAdjustDialog(row)" :disabled="['deactivated'].includes(row.status)">
              座区校准
            </el-button>
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button
              v-if="row.status === 'pending_production'"
              link
              type="success"
              @click="handleMarkAvailable(row)"
            >
              校验通过
            </el-button>
            <el-popconfirm title="确定删除此导引位标？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="createDialogVisible" title="新增导引位标" width="500px">
      <el-form :model="createForm" :rules="createRules" ref="createFormRef" label-width="100px">
        <el-form-item label="位标编号" prop="sign_number">
          <el-input v-model="createForm.sign_number" placeholder="请输入编号" />
        </el-form-item>
        <el-form-item label="批次编号" prop="batch_code">
          <el-input v-model="createForm.batch_code" placeholder="请输入批次编号" />
        </el-form-item>
        <el-form-item label="批次追踪码" prop="trace_code">
          <el-input v-model="createForm.trace_code" placeholder="同批次共用链路可填写相同追踪码" />
        </el-form-item>
        <el-form-item label="使用场景" prop="scene_scope">
          <el-select v-model="createForm.scene_scope" style="width: 100%">
            <el-option v-for="(item, key) in SCENE_SCOPE_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级" prop="risk_level">
          <el-select v-model="createForm.risk_level" style="width: 100%">
            <el-option v-for="(item, key) in RISK_LEVEL_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="交接说明" prop="handover_note">
          <el-input v-model="createForm.handover_note" type="textarea" :rows="2" placeholder="批次交接备注，可选" />
        </el-form-item>
        <el-form-item label="试听班次" prop="applicable_session">
          <el-input v-model="createForm.applicable_session" placeholder="如：2024春季班" />
        </el-form-item>
        <el-form-item label="目标座区" prop="current_area">
          <el-input v-model="createForm.current_area" placeholder="如：A区第1排" />
        </el-form-item>
        <el-form-item label="现场负责人" prop="responsible_person">
          <el-input v-model="createForm.responsible_person" placeholder="请输入现场负责人" />
        </el-form-item>
        <el-form-item label="初始状态" prop="status">
          <el-select v-model="createForm.status" style="width: 100%">
            <el-option label="待印制校样" value="pending_production" />
            <el-option label="待投放" value="available" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注" prop="remark">
          <el-input v-model="createForm.remark" type="textarea" :rows="2" placeholder="可选" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleCreate" :loading="submitLoading">确定</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" title="导引防错详情" width="700px">
      <el-descriptions :column="2" border v-if="currentSign">
        <el-descriptions-item label="位标编号">{{ currentSign.sign_number }}</el-descriptions-item>
        <el-descriptions-item label="批次编号">{{ currentSign.batch_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="批次追踪码">{{ currentSign.trace_code || '-' }}</el-descriptions-item>
        <el-descriptions-item label="使用场景">
          <el-tag :type="getSceneScopeType(currentSign.scene_scope)" size="small">{{ getSceneScopeLabel(currentSign.scene_scope) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="风险等级">
          <el-tag :type="getRiskLevelType(currentSign.risk_level)" size="small">{{ getRiskLevelLabel(currentSign.risk_level) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="一致性状态">
          <el-tag :type="getConsistencyStateType(currentSign.consistency_state)" size="small">{{ getConsistencyStateLabel(currentSign.consistency_state) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="试听班次">{{ currentSign.applicable_session }}</el-descriptions-item>
        <el-descriptions-item label="当前座区">{{ currentSign.current_area }}</el-descriptions-item>
        <el-descriptions-item label="现场负责人">{{ currentSign.responsible_person }}</el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentSign.status)">{{ getStatusLabel(currentSign.status) }}</el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="交接说明" :span="2">{{ currentSign.handover_note || '-' }}</el-descriptions-item>
        <el-descriptions-item label="链路摘要" :span="2">{{ currentSign.summary_meta || '-' }}</el-descriptions-item>
        <el-descriptions-item label="流转摘要" :span="2">{{ currentSign.flow_digest || '-' }}</el-descriptions-item>
        <el-descriptions-item label="备注" :span="2">{{ currentSign.remark || '-' }}</el-descriptions-item>
      </el-descriptions>

      <el-alert
        v-if="currentSign && currentSign.consistency_state === 'warn'"
        title="该位标存在批次链路冲突：允许继续流转，但请核对交接说明后再操作"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      />
      <el-alert
        v-else-if="currentSign && currentSign.risk_level === 'yellow'"
        title="黄色风险提醒：仅提示不拦截，请留意批次链路状态"
        type="warning"
        :closable="false"
        show-icon
        style="margin-top: 12px"
      />

      <el-tabs v-model="activeTab" class="detail-tabs" v-if="currentSign">
        <el-tab-pane label="座区校准轨迹" name="position">
          <el-table :data="currentSign.position_records || []" size="small">
            <el-table-column prop="from_area" label="原座区" width="180" />
            <el-table-column prop="to_area" label="新座区" width="180" />
            <el-table-column prop="operator" label="执行人" width="120" />
            <el-table-column prop="reason" label="原因" />
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="投放回收轨迹" name="issue">
          <el-table :data="currentSign.issue_records || []" size="small">
            <el-table-column label="类型" width="100">
              <template #default="{ row }">
                <el-tag :type="row.issue_type === 'issue' ? 'success' : 'info'">
                  {{ row.issue_type === 'issue' ? '投放' : '回收' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="session" label="班次" width="140" />
            <el-table-column prop="operator" label="执行人" width="120" />
            <el-table-column prop="receiver" label="接场人" width="120" />
            <el-table-column prop="remark" label="备注" />
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="防错复核记录" name="review">
          <el-table :data="currentSign.review_records || []" size="small">
            <el-table-column label="结论" width="120">
              <template #default="{ row }">
                <el-tag :type="row.conclusion === 'deactivate' ? 'danger' : 'success'">
                  {{ { restore: '复核后可投放', deactivate: '隔离停用', reissue: '重新投放' }[row.conclusion] || row.conclusion }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="reviewer" label="复核员" width="120" />
            <el-table-column prop="reason" label="原因" />
            <el-table-column prop="created_at" label="时间" width="180" />
          </el-table>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="adjustDialogVisible" title="座区校准" width="450px">
      <el-form :model="adjustForm" :rules="adjustRules" ref="adjustFormRef" label-width="100px">
        <el-form-item label="当前座区">
          <el-input :value="currentSign?.current_area" disabled />
        </el-form-item>
        <el-form-item label="调整到" prop="to_area">
          <el-input v-model="adjustForm.to_area" placeholder="请输入新座区" />
        </el-form-item>
        <el-form-item label="执行人" prop="operator">
          <el-input v-model="adjustForm.operator" placeholder="请输入执行人" />
        </el-form-item>
        <el-form-item label="校准原因" prop="reason">
          <el-input v-model="adjustForm.reason" type="textarea" :rows="2" placeholder="请输入原因" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="adjustDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleAdjust" :loading="submitLoading">确认调整</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="editDialogVisible" title="编辑导引位标" width="500px">
      <el-form :model="editForm" :rules="editRules" ref="editFormRef" label-width="100px">
        <el-form-item label="位标编号">
          <el-input v-model="editForm.sign_number" disabled />
        </el-form-item>
        <el-form-item label="批次编号">
          <el-input v-model="editForm.batch_code" />
        </el-form-item>
        <el-form-item label="批次追踪码">
          <el-input v-model="editForm.trace_code" placeholder="同批次共用链路可填写相同追踪码" />
        </el-form-item>
        <el-form-item label="使用场景">
          <el-select v-model="editForm.scene_scope" style="width: 100%">
            <el-option v-for="(item, key) in SCENE_SCOPE_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="editForm.risk_level" style="width: 100%">
            <el-option v-for="(item, key) in RISK_LEVEL_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="一致性状态">
          <el-select v-model="editForm.consistency_state" style="width: 100%">
            <el-option v-for="(item, key) in CONSISTENCY_STATE_MAP" :key="key" :label="item.label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item label="交接说明">
          <el-input v-model="editForm.handover_note" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="试听班次" prop="applicable_session">
          <el-input v-model="editForm.applicable_session" />
        </el-form-item>
        <el-form-item label="目标座区" prop="current_area">
          <el-input v-model="editForm.current_area" />
        </el-form-item>
        <el-form-item label="现场负责人" prop="responsible_person">
          <el-input v-model="editForm.responsible_person" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="editForm.remark" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleEdit" :loading="submitLoading">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Search, Refresh, Plus, Warning, CircleCheck } from '@element-plus/icons-vue'
import request from '@/utils/request'
import { STATUS_MAP, getStatusLabel, getStatusType, getAnomalyTypeLabel,
  SCENE_SCOPE_MAP, RISK_LEVEL_MAP, CONSISTENCY_STATE_MAP,
  getSceneScopeLabel, getSceneScopeType,
  getRiskLevelLabel, getRiskLevelType,
  getConsistencyStateLabel, getConsistencyStateType } from '@/utils/statusMap'

const loading = ref(false)
const submitLoading = ref(false)
const signList = ref([])
const currentSign = ref(null)
const route = useRoute()

const filterForm = reactive({
  status: '',
  batch_code: '',
  trace_code: '',
  scene_scope: '',
  risk_level: '',
  consistency_state: '',
  applicable_session: '',
  responsible_person: '',
  keyword: ''
})

const createDialogVisible = ref(false)
const createFormRef = ref(null)
const createForm = reactive({
  sign_number: '',
  batch_code: '',
  trace_code: '',
  scene_scope: 'exclusive',
  risk_level: 'none',
  handover_note: '',
  applicable_session: '',
  current_area: '',
  responsible_person: '',
  status: 'pending_production',
  remark: ''
})
const createRules = {
  sign_number: [{ required: true, message: '请输入位标编号', trigger: 'blur' }],
  applicable_session: [{ required: true, message: '请输入试听班次', trigger: 'blur' }],
  current_area: [{ required: true, message: '请输入目标座区', trigger: 'blur' }],
  responsible_person: [{ required: true, message: '请输入现场负责人', trigger: 'blur' }]
}

const detailDialogVisible = ref(false)
const activeTab = ref('position')

const adjustDialogVisible = ref(false)
const adjustFormRef = ref(null)
const adjustForm = reactive({
  to_area: '',
  operator: '',
  reason: ''
})
const adjustRules = {
  to_area: [{ required: true, message: '请输入新座区', trigger: 'blur' }],
  operator: [{ required: true, message: '请输入执行人', trigger: 'blur' }]
}

const editDialogVisible = ref(false)
const editFormRef = ref(null)
const editForm = reactive({
  id: null,
  sign_number: '',
  batch_code: '',
  trace_code: '',
  scene_scope: 'exclusive',
  risk_level: 'none',
  consistency_state: 'normal',
  handover_note: '',
  applicable_session: '',
  current_area: '',
  responsible_person: '',
  remark: ''
})
const editRules = {
  applicable_session: [{ required: true, message: '请输入试听班次', trigger: 'blur' }],
  current_area: [{ required: true, message: '请输入目标座区', trigger: 'blur' }],
  responsible_person: [{ required: true, message: '请输入现场负责人', trigger: 'blur' }]
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
  filterForm.status = ''
  filterForm.batch_code = ''
  filterForm.trace_code = ''
  filterForm.scene_scope = ''
  filterForm.risk_level = ''
  filterForm.consistency_state = ''
  filterForm.applicable_session = ''
  filterForm.responsible_person = ''
  filterForm.keyword = ''
  fetchList()
}

function openCreateDialog() {
  createDialogVisible.value = true
  Object.assign(createForm, {
    sign_number: '',
    batch_code: '',
    trace_code: '',
    scene_scope: 'exclusive',
    risk_level: 'none',
    handover_note: '',
    applicable_session: '',
    current_area: '',
    responsible_person: '',
    status: 'pending_production',
    remark: ''
  })
}

async function handleCreate() {
  try {
    await createFormRef.value.validate()
    submitLoading.value = true
    await request.post('/signs', createForm)
    ElMessage.success('创建成功')
    createDialogVisible.value = false
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

async function openDetailDialog(row) {
  currentSign.value = await request.get(`/signs/${row.id}`)
  detailDialogVisible.value = true
}

function openAdjustDialog(row) {
  currentSign.value = { ...row }
  adjustDialogVisible.value = true
  adjustForm.to_area = ''
  adjustForm.operator = ''
  adjustForm.reason = ''
}

async function handleAdjust() {
  try {
    await adjustFormRef.value.validate()
    submitLoading.value = true
    await request.post(`/signs/${currentSign.value.id}/adjust-position`, adjustForm)
    ElMessage.success('座区校准成功')
    adjustDialogVisible.value = false
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

function openEditDialog(row) {
  editForm.id = row.id
  editForm.sign_number = row.sign_number
  editForm.batch_code = row.batch_code
  editForm.trace_code = row.trace_code || ''
  editForm.scene_scope = row.scene_scope || 'exclusive'
  editForm.risk_level = row.risk_level || 'none'
  editForm.consistency_state = row.consistency_state || 'normal'
  editForm.handover_note = row.handover_note || ''
  editForm.applicable_session = row.applicable_session
  editForm.current_area = row.current_area
  editForm.responsible_person = row.responsible_person
  editForm.remark = row.remark
  editDialogVisible.value = true
}

async function handleEdit() {
  try {
    await editFormRef.value.validate()
    submitLoading.value = true
    await request.put(`/signs/${editForm.id}`, {
      batch_code: editForm.batch_code,
      trace_code: editForm.trace_code,
      scene_scope: editForm.scene_scope,
      risk_level: editForm.risk_level,
      consistency_state: editForm.consistency_state,
      handover_note: editForm.handover_note,
      applicable_session: editForm.applicable_session,
      current_area: editForm.current_area,
      responsible_person: editForm.responsible_person,
      remark: editForm.remark
    })
    ElMessage.success('保存成功')
    editDialogVisible.value = false
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

async function handleDelete(row) {
  try {
    await request.delete(`/signs/${row.id}`)
    ElMessage.success('删除成功')
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  }
}

async function handleMarkAvailable(row) {
  try {
    await request.post(`/signs/${row.id}/status/available`)
    ElMessage.success('已标记为待投放')
    fetchList()
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  }
}

onMounted(() => {
  // 支持从批次追踪概览等页面跳转时携带筛选条件
  const query = route.query || {}
  Object.keys(filterForm).forEach(key => {
    if (query[key] !== undefined && query[key] !== null) {
      filterForm[key] = String(query[key])
    }
  })
  fetchList()
})
</script>

<style scoped>
.sign-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}

.detail-tabs {
  margin-top: 20px;
}

.sign-number-with-tag { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
.anomaly-tag { margin-left: 4px; }
.anomaly-warning { display: inline-flex; align-items: center; gap: 4px; color: #f56c6c; font-size: 13px; font-weight: 500; }
.no-anomaly { display: inline-flex; align-items: center; gap: 4px; color: #67c23a; font-size: 13px; }
</style>
