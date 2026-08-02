<template>
  <div class="anomaly-page">
    <el-card class="filter-card">
      <el-form :inline="true" :model="filterForm" @submit.prevent>
        <el-form-item label="状态">
          <el-select v-model="filterForm.current_status" placeholder="全部状态" clearable style="width: 130px">
            <el-option v-for="item in anomalyStatusOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="偏差类型">
          <el-select v-model="filterForm.anomaly_type" placeholder="全部类型" clearable style="width: 130px">
            <el-option v-for="item in anomalyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="影响等级">
          <el-select v-model="filterForm.anomaly_level" placeholder="全部等级" clearable style="width: 110px">
            <el-option v-for="item in anomalyLevelOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="班次">
          <el-input v-model="filterForm.session" placeholder="班次名称" clearable style="width: 140px" />
        </el-form-item>
        <el-form-item label="追踪码">
          <el-input v-model="filterForm.trace_code" placeholder="trace_code" clearable style="width: 150px" />
        </el-form-item>
        <el-form-item label="现场负责人">
          <el-input v-model="filterForm.responsible_person" placeholder="现场负责人" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="filterForm.keyword" placeholder="编号/描述" clearable style="width: 140px" />
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
          <span>现场偏差闭环台账</span>
          <div class="header-tags">
            <el-tooltip content="返回现场闭环总览" placement="top">
              <el-tag type="info" size="small" style="margin-right: 8px">
                闭环项：{{ globalStats.total || 0 }}
              </el-tag>
            </el-tooltip>
            <el-tooltip content="返回现场闭环总览" placement="top">
              <el-tag type="danger" size="small" style="margin-right: 8px">
                待核查：{{ globalStats.pending || 0 }}
              </el-tag>
            </el-tooltip>
            <el-tooltip content="返回现场闭环总览" placement="top">
              <el-tag type="warning" size="small" style="margin-right: 8px">
                核查中：{{ globalStats.processing || 0 }}
              </el-tag>
            </el-tooltip>
            <el-tooltip content="返回现场闭环总览" placement="top">
              <el-tag type="primary" size="small" style="margin-right: 8px">
                待复核：{{ globalStats.pending_confirm || 0 }}
              </el-tag>
            </el-tooltip>
            <el-tooltip content="返回现场闭环总览" placement="top">
              <el-tag type="success" size="small" style="margin-right: 8px">
                已核销：{{ globalStats.closed || 0 }}
              </el-tag>
            </el-tooltip>
            <el-button type="primary" size="small" @click="openRegisterDialog">
              <el-icon><Plus /></el-icon>登记现场偏差
            </el-button>
          </div>
        </div>
      </template>
      <el-table :data="anomalyList" v-loading="loading" stripe>
        <el-table-column prop="id" label="偏差编号" width="90" />
        <el-table-column label="位标信息" width="180">
          <template #default="{ row }">
            <div class="sign-info">
              <div class="sign-number">{{ row.guide_sign?.sign_number || '-' }}</div>
              <div class="sign-session">{{ row.guide_sign?.applicable_session || '-' }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="批次追踪" width="200">
          <template #default="{ row }">
            <div class="trace-cell">
              <div class="trace-code-line">
                <el-icon><Connection /></el-icon>
                <span class="trace-code-text">{{ row.trace_code || row.guide_sign?.trace_code || '-' }}</span>
              </div>
              <div class="trace-tags">
                <el-tag
                  v-if="(row.scene_scope || row.guide_sign?.scene_scope) === 'shared'"
                  type="warning"
                  size="small"
                  effect="plain"
                >共享链路</el-tag>
                <el-tag
                  :type="getRiskLevelType(row.risk_level || row.guide_sign?.risk_level)"
                  size="small"
                  effect="plain"
                >
                  {{ getRiskLevelLabel(row.risk_level || row.guide_sign?.risk_level) }}
                </el-tag>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="偏差类型" width="100">
          <template #default="{ row }">
            <el-tag :type="getAnomalyTypeType(row.anomaly_type)" size="small">
              {{ getAnomalyTypeLabel(row.anomaly_type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="等级" width="80">
          <template #default="{ row }">
            <el-tag :type="getAnomalyLevelType(row.anomaly_level)" size="small">
              {{ getAnomalyLevelLabel(row.anomaly_level) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="session" label="班次" width="140" show-overflow-tooltip />
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">
              {{ getAnomalyStatusLabel(row.current_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="reporter" label="登记人" width="90" />
        <el-table-column prop="responsible_person" label="现场负责人" width="90" />
        <el-table-column prop="description" label="偏差描述" min-width="150" show-overflow-tooltip />
        <el-table-column prop="created_at" label="登记时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
            <el-button link type="primary" size="small" @click="openProcessDialog(row)">
              {{ row.current_status === 'closed' ? '重新纳入' : '核查' }}
            </el-button>
            <el-button
              link
              type="warning"
              size="small"
              :disabled="!(row.trace_code || row.guide_sign?.trace_code)"
              @click="openSameTraceDrawer(row)"
            >
              同批次
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="registerDialogVisible" title="登记现场偏差" width="560px">
      <el-form :model="registerForm" :rules="registerRules" ref="registerFormRef" label-width="100px">
        <el-form-item label="导引位标" prop="sign_id">
          <el-select
            v-model="registerForm.sign_id"
            filterable
            placeholder="请选择导引位标"
            style="width: 100%"
            @change="handleRegisterSignChange"
          >
            <el-option
              v-for="sign in availableSigns"
              :key="sign.id"
              :label="sign.sign_number + ' - ' + sign.applicable_session"
              :value="sign.id"
            />
          </el-select>
        </el-form-item>

        <div v-if="selectedRegisterSign" class="trace-context">
          <div class="trace-context-title">
            <el-icon><Connection /></el-icon>
            位标批次链路档案（自动带出）
          </div>
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="追踪码">
              {{ selectedRegisterSign.trace_code || '-' }}
            </el-descriptions-item>
            <el-descriptions-item label="链路范围">
              <el-tag
                v-if="selectedRegisterSign.scene_scope === 'shared'"
                type="warning"
                size="small"
              >同批次共用链路</el-tag>
              <el-tag v-else type="info" size="small">本批次专用</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="风险等级">
              <el-tag
                :type="getRiskLevelType(selectedRegisterSign.risk_level)"
                size="small"
                effect="dark"
              >
                {{ getRiskLevelLabel(selectedRegisterSign.risk_level) }}
              </el-tag>
              <span
                v-if="selectedRegisterSign.risk_level === 'yellow'"
                class="hint-text"
              >（yellow 仅提醒不拦截）</span>
            </el-descriptions-item>
            <el-descriptions-item label="一致性">
              <el-tag
                :type="getConsistencyStateType(selectedRegisterSign.consistency_state)"
                size="small"
              >
                {{ getConsistencyStateLabel(selectedRegisterSign.consistency_state) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="交接备注" :span="2">
              {{ selectedRegisterSign.handover_note || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <el-form-item label="偏差类型" prop="anomaly_type">
          <el-select v-model="registerForm.anomaly_type" placeholder="请选择偏差类型" style="width: 100%">
            <el-option v-for="item in anomalyTypeOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="影响等级" prop="anomaly_level">
          <el-select v-model="registerForm.anomaly_level" placeholder="请选择影响等级" style="width: 100%">
            <el-option v-for="item in anomalyLevelOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="班次">
          <el-input v-model="registerForm.session" placeholder="试听班次（可选）" />
        </el-form-item>
        <el-form-item label="登记人" prop="reporter">
          <el-input v-model="registerForm.reporter" placeholder="请输入登记人姓名" />
        </el-form-item>
        <el-form-item label="现场负责人" prop="responsible_person">
          <el-input v-model="registerForm.responsible_person" placeholder="请输入现场负责人姓名" />
        </el-form-item>
        <el-form-item label="偏差描述" prop="description">
          <el-input v-model="registerForm.description" type="textarea" :rows="3" placeholder="请描述偏差情况" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="registerDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleRegister" :loading="submitLoading">确认登记</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="processDialogVisible" title="偏差闭环核查" width="500px">
      <div class="process-info" v-if="currentAnomaly">
        <el-descriptions :column="2" size="small" border>
          <el-descriptions-item label="偏差编号">{{ currentAnomaly.id }}</el-descriptions-item>
          <el-descriptions-item label="当前状态">
            <el-tag :type="getAnomalyStatusType(currentAnomaly.current_status)" size="small">
              {{ getAnomalyStatusLabel(currentAnomaly.current_status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="导引位标">{{ currentAnomaly.guide_sign?.sign_number }}</el-descriptions-item>
          <el-descriptions-item label="偏差类型">{{ getAnomalyTypeLabel(currentAnomaly.anomaly_type) }}</el-descriptions-item>
          <el-descriptions-item label="现场负责人" :span="2">{{ currentAnomaly.responsible_person }}</el-descriptions-item>
        </el-descriptions>
        <el-alert
          v-if="recommendSubmitConfirm"
          type="warning"
          :closable="false"
          show-icon
          class="recommend-alert"
          title="同批次共享链路 + yellow 风险"
          description="该位标属于同批次共用链路且风险等级为 yellow，建议先提交复核确认，由复核人员统一确认后再核销闭环。"
        />
      </div>
      <el-form :model="processForm" :rules="processRules" ref="processFormRef" label-width="90px" style="margin-top: 20px">
        <el-form-item label="核查动作" prop="action">
          <el-select v-model="processForm.action" placeholder="请选择核查动作" style="width: 100%">
            <el-option v-for="action in availableActions" :key="action.value" :label="action.label" :value="action.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="执行人" prop="operator">
          <el-input v-model="processForm.operator" placeholder="请输入执行人姓名" />
        </el-form-item>
        <el-form-item label="核查说明" prop="remark">
          <el-input v-model="processForm.remark" type="textarea" :rows="4" placeholder="请输入现场核查说明或复核备注" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="processDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleProcess" :loading="submitLoading">确认提交</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="detailDrawerVisible" title="偏差详情" size="600px" direction="rtl">
      <div v-loading="detailLoading" class="detail-content">
        <div v-if="currentAnomaly">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="偏差编号">{{ currentAnomaly.id }}</el-descriptions-item>
            <el-descriptions-item label="当前状态">
              <el-tag :type="getAnomalyStatusType(currentAnomaly.current_status)">
                {{ getAnomalyStatusLabel(currentAnomaly.current_status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="偏差类型">{{ getAnomalyTypeLabel(currentAnomaly.anomaly_type) }}</el-descriptions-item>
            <el-descriptions-item label="影响等级">
              <el-tag :type="getAnomalyLevelType(currentAnomaly.anomaly_level)" size="small">
                {{ getAnomalyLevelLabel(currentAnomaly.anomaly_level) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="班次">{{ currentAnomaly.session || '-' }}</el-descriptions-item>
            <el-descriptions-item label="登记人">{{ currentAnomaly.reporter }}</el-descriptions-item>
            <el-descriptions-item label="现场负责人">{{ currentAnomaly.responsible_person }}</el-descriptions-item>
            <el-descriptions-item label="登记时间">{{ formatDate(currentAnomaly.created_at) }}</el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">偏差描述</el-divider>
          <p class="description-text">{{ currentAnomaly.description || '暂无描述' }}</p>

          <el-divider content-position="left" v-if="currentAnomaly.current_status === 'closed'">最终结果</el-divider>
          <p class="final-result" v-if="currentAnomaly.current_status === 'closed'">
            {{ currentAnomaly.final_result || '无' }}
          </p>

          <el-divider content-position="left">关联导引位标</el-divider>
          <el-descriptions :column="2" size="small" border v-if="currentAnomaly.guide_sign">
            <el-descriptions-item label="编号">{{ currentAnomaly.guide_sign.sign_number }}</el-descriptions-item>
            <el-descriptions-item label="批次">{{ currentAnomaly.guide_sign.batch_code || '-' }}</el-descriptions-item>
            <el-descriptions-item label="试听班次">{{ currentAnomaly.guide_sign.applicable_session }}</el-descriptions-item>
            <el-descriptions-item label="当前状态">
              <el-tag :type="getStatusType(currentAnomaly.guide_sign.status)" size="small">
                {{ getStatusLabel(currentAnomaly.guide_sign.status) }}
              </el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="目标座区" :span="2">{{ currentAnomaly.guide_sign.current_area }}</el-descriptions-item>
          </el-descriptions>

          <el-divider content-position="left">历史防错轨迹</el-divider>
          <div class="timeline">
            <el-timeline>
              <el-timeline-item
                v-for="(flow, index) in flowRecords"
                :key="flow.id"
                :timestamp="formatDate(flow.created_at)"
                :type="getTimelineType(flow.action)"
                size="large"
              >
                <div class="flow-item">
                  <div class="flow-header">
                    <span class="flow-action">{{ getAnomalyActionLabel(flow.action) }}</span>
                    <span class="flow-operator">执行人：{{ flow.operator }}</span>
                  </div>
                  <div class="flow-status" v-if="flow.from_status || flow.to_status">
                    <span v-if="flow.from_status" :class="['status-tag', 'from']">
                      {{ getAnomalyStatusLabel(flow.from_status) }}
                    </span>
                    <el-icon class="arrow-icon"><ArrowRight /></el-icon>
                    <span v-if="flow.to_status" :class="['status-tag', 'to', flow.to_status]">
                      {{ getAnomalyStatusLabel(flow.to_status) }}
                    </span>
                  </div>
                  <div class="flow-remark" v-if="flow.remark">{{ flow.remark }}</div>
                </div>
              </el-timeline-item>
            </el-timeline>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button @click="detailDrawerVisible = false">关闭</el-button>
        <el-button type="primary" @click="handleDetailProcess" v-if="currentAnomaly">
          {{ currentAnomaly.current_status === 'closed' ? '重新纳入核查' : '偏差核查' }}
        </el-button>
      </template>
    </el-drawer>

    <el-drawer v-model="sameTraceDrawerVisible" title="同批次偏差追查" size="620px" direction="rtl">
      <div v-loading="sameTraceLoading" class="same-trace-body">
        <div v-if="sameTraceCode" class="same-trace-summary">
          <el-descriptions :column="2" size="small" border>
            <el-descriptions-item label="追踪码" :span="2">
              <b>{{ sameTraceCode }}</b>
            </el-descriptions-item>
            <el-descriptions-item label="偏差总数">{{ sameTraceList.length }}</el-descriptions-item>
            <el-descriptions-item label="未闭环数">{{ sameTraceActiveCount }}</el-descriptions-item>
            <el-descriptions-item label="风险等级" :span="2">
              <el-tag :type="getRiskLevelType(sameTraceRiskLevel)" effect="dark" size="small">
                {{ getRiskLevelLabel(sameTraceRiskLevel) }}
              </el-tag>
              <el-tag
                v-if="sameTraceSceneScope === 'shared'"
                type="warning"
                size="small"
                effect="plain"
                style="margin-left: 6px"
              >同批次共用链路</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="交接备注" :span="2">
              {{ sameTraceHandoverNote || '-' }}
            </el-descriptions-item>
          </el-descriptions>
        </div>

        <el-table :data="sameTraceList" size="small" stripe style="margin-top: 12px">
          <el-table-column prop="id" label="编号" width="70" />
          <el-table-column label="位标" width="120">
            <template #default="{ row }">
              {{ row.guide_sign?.sign_number || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="类型" width="90">
            <template #default="{ row }">
              <el-tag :type="getAnomalyTypeType(row.anomaly_type)" size="small">
                {{ getAnomalyTypeLabel(row.anomaly_type) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">
                {{ getAnomalyStatusLabel(row.current_status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="responsible_person" label="负责人" width="90" />
          <el-table-column prop="description" label="描述" min-width="140" show-overflow-tooltip />
          <el-table-column label="操作" width="80" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="viewDetail(row)">详情</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <template #footer>
        <el-button @click="sameTraceDrawerVisible = false">关闭</el-button>
      </template>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Refresh, Plus, ArrowRight, Connection } from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getStatusLabel, getStatusType,
  getAnomalyStatusLabel, getAnomalyStatusType,
  getAnomalyTypeLabel, getAnomalyTypeType,
  getAnomalyLevelLabel, getAnomalyLevelType,
  getAnomalyActionLabel,
  getRiskLevelLabel, getRiskLevelType,
  getConsistencyStateLabel, getConsistencyStateType,
  ANOMALY_STATUS_MAP, ANOMALY_TYPE_MAP, ANOMALY_LEVEL_MAP
} from '@/utils/statusMap'

const RISK_RANK = { green: 0, yellow: 1, red: 2 }

const route = useRoute()

const loading = ref(false)
const submitLoading = ref(false)
const detailLoading = ref(false)
const anomalyList = ref([])
const availableSigns = ref([])
const flowRecords = ref([])
const globalStats = ref({})

const filterForm = reactive({
  current_status: '',
  anomaly_type: '',
  anomaly_level: '',
  session: '',
  trace_code: '',
  responsible_person: '',
  keyword: ''
})

const pendingAnomalyId = ref(null)

async function fetchGlobalStats() {
  try {
    globalStats.value = await request.get('/anomalies/stats/summary')
  } catch (e) {
    console.error(e)
  }
}

function initFilterFromQuery() {
  const query = route.query
  if (query.current_status) {
    filterForm.current_status = query.current_status
  }
  if (query.anomaly_type) {
    filterForm.anomaly_type = query.anomaly_type
  }
  if (query.anomaly_id) {
    pendingAnomalyId.value = parseInt(query.anomaly_id)
  }
}

async function openAnomalyById(id) {
  try {
    const [anomaly, flows] = await Promise.all([
      request.get(`/anomalies/${id}`),
      request.get(`/anomalies/${id}/flows`)
    ])
    currentAnomaly.value = anomaly
    flowRecords.value = flows
    detailDrawerVisible.value = true
  } catch (e) {
    ElMessage.error('偏差记录不存在')
  }
}

const anomalyStatusOptions = computed(() => {
  return Object.entries(ANOMALY_STATUS_MAP).map(([value, { label }]) => ({ value, label }))
})

const anomalyTypeOptions = computed(() => {
  return Object.entries(ANOMALY_TYPE_MAP).map(([value, { label }]) => ({ value, label }))
})

const anomalyLevelOptions = computed(() => {
  return Object.entries(ANOMALY_LEVEL_MAP).map(([value, { label }]) => ({ value, label }))
})

const pendingCount = computed(() => {
  return anomalyList.value.filter(a => a.current_status === 'pending').length
})

const processingCount = computed(() => {
  return anomalyList.value.filter(a => a.current_status === 'processing').length
})

const registerDialogVisible = ref(false)
const registerFormRef = ref(null)
const registerForm = reactive({
  sign_id: null,
  anomaly_type: '',
  anomaly_level: 'normal',
  session: '',
  reporter: '',
  responsible_person: '',
  description: ''
})
const registerRules = {
  sign_id: [{ required: true, message: '请选择导引位标', trigger: 'change' }],
  anomaly_type: [{ required: true, message: '请选择偏差类型', trigger: 'change' }],
  anomaly_level: [{ required: true, message: '请选择影响等级', trigger: 'change' }],
  reporter: [{ required: true, message: '请输入登记人', trigger: 'blur' }],
  responsible_person: [{ required: true, message: '请输入现场负责人', trigger: 'blur' }]
}

const selectedRegisterSign = computed(() => {
  if (!registerForm.sign_id) return null
  return availableSigns.value.find((s) => s.id === registerForm.sign_id) || null
})

function handleRegisterSignChange(signId) {
  const sign = availableSigns.value.find((s) => s.id === signId)
  if (!sign) return
  if (!registerForm.session && sign.applicable_session) {
    registerForm.session = sign.applicable_session
  }
  if (!registerForm.responsible_person && sign.responsible_person) {
    registerForm.responsible_person = sign.responsible_person
  }
}

const processDialogVisible = ref(false)
const processFormRef = ref(null)
const currentAnomaly = ref(null)
const processForm = reactive({
  action: '',
  operator: '',
  remark: ''
})
const processRules = {
  action: [{ required: true, message: '请选择核查动作', trigger: 'change' }],
  operator: [{ required: true, message: '请输入执行人', trigger: 'blur' }]
}

const detailDrawerVisible = ref(false)

const availableActions = computed(() => {
  if (!currentAnomaly.value) return []
  const status = currentAnomaly.value.current_status
  const actions = []

  if (status === 'pending') {
    actions.push({ value: 'start_process', label: '开始现场核查' })
  }
  if (status === 'processing') {
    actions.push({ value: 'submit_confirm', label: '提交复核确认' })
    actions.push({ value: 'add_remark', label: '补充核查说明' })
  }
  if (status === 'pending_confirm') {
    actions.push({ value: 'confirm_close', label: '核销闭环' })
    actions.push({ value: 'reject', label: '退回复查' })
    actions.push({ value: 'start_process', label: '继续现场核查' })
  }
  if (status === 'closed') {
    actions.push({ value: 'reopen', label: '重新纳入核查' })
  }

  return actions
})

const recommendSubmitConfirm = computed(() => {
  if (!currentAnomaly.value) return false
  const sign = currentAnomaly.value.guide_sign || {}
  const sceneScope = currentAnomaly.value.scene_scope || sign.scene_scope
  const riskLevel = currentAnomaly.value.risk_level || sign.risk_level
  const status = currentAnomaly.value.current_status
  return sceneScope === 'shared' && riskLevel === 'yellow' && status === 'processing'
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

function getTimelineType(action) {
  const typeMap = {
    register: 'primary',
    start_process: 'warning',
    submit_confirm: 'warning',
    confirm_close: 'success',
    reject: 'danger',
    reopen: 'warning',
    add_remark: 'info'
  }
  return typeMap[action] || 'primary'
}

async function fetchList() {
  loading.value = true
  try {
    const params = {}
    Object.keys(filterForm).forEach(key => {
      if (filterForm[key]) params[key] = filterForm[key]
    })
    anomalyList.value = await request.get('/anomalies', { params })
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function resetFilter() {
  filterForm.current_status = ''
  filterForm.anomaly_type = ''
  filterForm.anomaly_level = ''
  filterForm.session = ''
  filterForm.trace_code = ''
  filterForm.responsible_person = ''
  filterForm.keyword = ''
  fetchList()
}

async function fetchAvailableSigns() {
  try {
    availableSigns.value = await request.get('/signs', { params: { limit: 200 } })
  } catch (e) {
    console.error(e)
  }
}

function openRegisterDialog() {
  registerForm.sign_id = null
  registerForm.anomaly_type = ''
  registerForm.anomaly_level = 'normal'
  registerForm.session = ''
  registerForm.reporter = ''
  registerForm.responsible_person = ''
  registerForm.description = ''
  fetchAvailableSigns()
  registerDialogVisible.value = true
}

async function handleRegister() {
  try {
    await registerFormRef.value.validate()
    submitLoading.value = true
    
    const data = { ...registerForm }
    if (!data.session) delete data.session
    
    await request.post('/anomalies', data)
    ElMessage.success('偏差登记成功')
    registerDialogVisible.value = false
    Promise.all([fetchList(), fetchGlobalStats()])
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

function openProcessDialog(row) {
  currentAnomaly.value = row
  const sign = row.guide_sign || {}
  const sceneScope = row.scene_scope || sign.scene_scope
  const riskLevel = row.risk_level || sign.risk_level
  const isSharedYellow =
    sceneScope === 'shared' && riskLevel === 'yellow' && row.current_status === 'processing'
  processForm.action = isSharedYellow ? 'submit_confirm' : ''
  processForm.operator = ''
  processForm.remark = ''
  if (isSharedYellow) {
    processForm.remark = '同批次共享链路 + yellow 风险，按建议先提交复核确认。'
  }
  processDialogVisible.value = true
}

async function handleProcess() {
  try {
    await processFormRef.value.validate()
    submitLoading.value = true
    
    await request.post(`/anomalies/${currentAnomaly.value.id}/process`, {
      action: processForm.action,
      operator: processForm.operator,
      remark: processForm.remark
    })
    
    ElMessage.success('操作成功')
    processDialogVisible.value = false
    Promise.all([fetchList(), fetchGlobalStats()])
    if (detailDrawerVisible.value) {
      fetchDetail(currentAnomaly.value.id)
    }
  } catch (e) {
    if (e?.message) ElMessage.error(e.message)
  } finally {
    submitLoading.value = false
  }
}

async function viewDetail(row) {
  currentAnomaly.value = row
  detailDrawerVisible.value = true
  fetchDetail(row.id)
}

async function fetchDetail(id) {
  detailLoading.value = true
  try {
    const [anomaly, flows] = await Promise.all([
      request.get(`/anomalies/${id}`),
      request.get(`/anomalies/${id}/flows`)
    ])
    currentAnomaly.value = anomaly
    flowRecords.value = flows
  } catch (e) {
    console.error(e)
  } finally {
    detailLoading.value = false
  }
}

function handleDetailProcess() {
  detailDrawerVisible.value = false
  openProcessDialog(currentAnomaly.value)
}

const sameTraceDrawerVisible = ref(false)
const sameTraceLoading = ref(false)
const sameTraceCode = ref('')
const sameTraceList = ref([])

const sameTraceActiveCount = computed(() => {
  return sameTraceList.value.filter(
    (item) => item.current_status !== 'closed'
  ).length
})

const sameTraceRiskLevel = computed(() => {
  let best = 'green'
  let bestRank = RISK_RANK[best]
  sameTraceList.value.forEach((item) => {
    const level = item.risk_level || item.guide_sign?.risk_level || 'green'
    const rank = RISK_RANK[level] ?? 0
    if (rank > bestRank) {
      bestRank = rank
      best = level
    }
  })
  return best
})

const sameTraceSceneScope = computed(() => {
  return sameTraceList.value.some(
    (item) =>
      (item.scene_scope || item.guide_sign?.scene_scope) === 'shared'
  )
    ? 'shared'
    : 'private'
})

const sameTraceHandoverNote = computed(() => {
  for (const item of sameTraceList.value) {
    const note = item.handover_note || item.guide_sign?.handover_note
    if (note && note.trim()) return note
  }
  return ''
})

async function openSameTraceDrawer(row) {
  const code = (row.trace_code || row.guide_sign?.trace_code || '').trim()
  if (!code) {
    ElMessage.warning('该偏差没有 trace_code，无法追查同批次')
    return
  }
  sameTraceCode.value = code
  sameTraceList.value = []
  sameTraceDrawerVisible.value = true
  sameTraceLoading.value = true
  try {
    sameTraceList.value = await request.get('/anomalies', {
      params: { trace_code: code, limit: 200 }
    })
  } catch (e) {
    console.error(e)
  } finally {
    sameTraceLoading.value = false
  }
}

async function initPage() {
  initFilterFromQuery()
  await Promise.all([fetchList(), fetchGlobalStats()])
  if (pendingAnomalyId.value) {
    await openAnomalyById(pendingAnomalyId.value)
  }
}

onMounted(() => {
  initPage()
})
</script>

<style scoped>
.anomaly-page {
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

.sign-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.sign-number {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.sign-session {
  color: #909399;
  font-size: 12px;
}

.process-info {
  margin-bottom: 10px;
}

.detail-content {
  padding: 10px 0;
}

.description-text {
  color: #606266;
  line-height: 1.6;
  margin: 0;
  padding: 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.final-result {
  color: #67c23a;
  line-height: 1.6;
  margin: 0;
  padding: 10px;
  background: #f0f9eb;
  border-radius: 4px;
  border-left: 3px solid #67c23a;
}

.timeline {
  padding: 10px 0;
}

.flow-item {
  padding-bottom: 10px;
}

.flow-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.flow-action {
  font-weight: 600;
  color: #303133;
  font-size: 14px;
}

.flow-operator {
  color: #909399;
  font-size: 12px;
}

.flow-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 6px;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.status-tag.from {
  background: #f4f4f5;
  color: #909399;
}

.status-tag.to {
  font-weight: 500;
}

.status-tag.to.pending {
  background: #fef0f0;
  color: #f56c6c;
}

.status-tag.to.processing {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-tag.to.pending_confirm {
  background: #fdf6ec;
  color: #e6a23c;
}

.status-tag.to.closed {
  background: #f0f9eb;
  color: #67c23a;
}

.arrow-icon {
  color: #c0c4cc;
  font-size: 12px;
}

.flow-remark {
  color: #606266;
  font-size: 13px;
  line-height: 1.5;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.trace-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.trace-code-line {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #303133;
  font-weight: 500;
}

.trace-code-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 150px;
}

.trace-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.trace-context {
  background: #f7f8fa;
  border: 1px solid #ebeef5;
  border-radius: 6px;
  padding: 10px 12px;
  margin-bottom: 14px;
}

.trace-context-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 13px;
  color: #303133;
  margin-bottom: 8px;
}

.hint-text {
  margin-left: 6px;
  font-size: 12px;
  color: #909399;
  font-weight: normal;
}

.recommend-alert {
  margin-top: 12px;
}

.same-trace-body {
  padding: 4px 0;
}

.same-trace-summary {
  background: #f7f8fa;
  padding: 10px;
  border-radius: 6px;
}
</style>
