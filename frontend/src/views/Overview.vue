<template>
  <div class="overview-page">
    <el-row :gutter="16" class="stats-row">
      <el-col :span="3">
        <div class="stat-card total">
          <div class="stat-icon">
            <el-icon :size="28"><Tickets /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">位标在控总量</div>
            <div class="stat-value">{{ stats.total_signs || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card pending">
          <div class="stat-icon">
            <el-icon :size="28"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待印制校样</div>
            <div class="stat-value">{{ stats.pending_production || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card available">
          <div class="stat-icon">
            <el-icon :size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待投放</div>
            <div class="stat-value">{{ stats.available || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card issued">
          <div class="stat-icon">
            <el-icon :size="28"><Promotion /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">已投放</div>
            <div class="stat-value">{{ stats.issued || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card recycle">
          <div class="stat-icon">
            <el-icon :size="28"><Refresh /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待回收核验</div>
            <div class="stat-value">{{ stats.pending_recycle || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card review">
          <div class="stat-icon">
            <el-icon :size="28"><DocumentChecked /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待防错复核</div>
            <div class="stat-value">{{ stats.pending_review || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card restored">
          <div class="stat-icon">
            <el-icon :size="28"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">复核后可投放</div>
            <div class="stat-value">{{ stats.restored || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="3">
        <div class="stat-card anomaly" @click="goToAnomaly" style="cursor: pointer">
          <div class="stat-icon">
            <el-icon :size="28"><Warning /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">偏差线索</div>
            <div class="stat-value">{{ stats.total_anomalies || 0 }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="stats-row anomaly-stats">
      <el-col :span="6">
        <div class="stat-card anomaly-pending" @click="goToAnomaly('pending')" style="cursor: pointer">
          <div class="stat-icon">
            <el-icon :size="24"><Clock /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待现场核查</div>
            <div class="stat-value">{{ stats.pending_anomalies || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card anomaly-processing" @click="goToAnomaly('processing')" style="cursor: pointer">
          <div class="stat-icon">
            <el-icon :size="24"><Loading /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">核查中</div>
            <div class="stat-value">{{ stats.processing_anomalies || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card anomaly-confirm" @click="goToAnomaly('pending_confirm')" style="cursor: pointer">
          <div class="stat-icon">
            <el-icon :size="24"><QuestionFilled /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">待复核确认</div>
            <div class="stat-value">{{ stats.pending_confirm_anomalies || 0 }}</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card anomaly-closed" @click="goToAnomaly('closed')" style="cursor: pointer">
          <div class="stat-icon">
            <el-icon :size="24"><CircleCheck /></el-icon>
          </div>
          <div class="stat-info">
            <div class="stat-label">已核销闭环</div>
            <div class="stat-value">{{ stats.closed_anomalies || 0 }}</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="charts-row">
      <el-col :span="24">
        <el-card class="chart-card trace-batch-card">
          <template #header>
            <div class="card-title">
              <span>批次追踪概览</span>
              <el-tag type="warning" size="small">{{ (stats.trace_batches || []).length }} 组批次链路</el-tag>
            </div>
          </template>

          <div v-if="(stats.trace_batches || []).length" class="trace-batch-cards">
            <div
              v-for="batch in stats.trace_batches"
              :key="batch.trace_code"
              class="trace-batch-item"
              :class="{ 'is-risky': batch.risk_level === 'yellow' || batch.risk_level === 'red' || batch.consistency_state === 'warn' }"
              @click="goToSignsByTrace(batch.trace_code)"
            >
              <div class="trace-batch-head">
                <span class="trace-code">{{ batch.trace_code }}</span>
                <div class="trace-tags">
                  <el-tag :type="getSceneScopeType(batch.scene_scope)" size="small">{{ getSceneScopeLabel(batch.scene_scope) }}</el-tag>
                  <el-tag :type="getRiskLevelType(batch.risk_level)" size="small">{{ getRiskLevelLabel(batch.risk_level) }}</el-tag>
                  <el-tag :type="getConsistencyStateType(batch.consistency_state)" size="small">{{ getConsistencyStateLabel(batch.consistency_state) }}</el-tag>
                </div>
              </div>
              <div class="trace-batch-metrics">
                <div class="metric"><span class="metric-label">同组位标</span><span class="metric-value">{{ batch.total_count }}</span></div>
                <div class="metric"><span class="metric-label">已投放</span><span class="metric-value">{{ batch.issued_count }}</span></div>
                <div class="metric"><span class="metric-label">待回收</span><span class="metric-value">{{ batch.pending_recycle_count }}</span></div>
                <div class="metric"><span class="metric-label">待复核</span><span class="metric-value">{{ batch.pending_review_count }}</span></div>
                <div class="metric"><span class="metric-label">未闭环偏差</span><span class="metric-value" :class="{ 'is-alert': batch.open_anomaly_count > 0 }">{{ batch.open_anomaly_count }}</span></div>
              </div>
              <div class="trace-batch-note">
                <el-icon><ChatLineSquare /></el-icon>
                <span>{{ batch.latest_flow_note || '暂无流转说明' }}</span>
              </div>
            </div>
          </div>
          <el-empty v-else description="暂无批次追踪链路" :image-size="80" />

          <el-table
            v-if="(stats.trace_batches || []).length"
            :data="stats.trace_batches"
            size="small"
            v-loading="loading"
            class="trace-batch-table"
          >
            <el-table-column prop="trace_code" label="追踪码" width="140" />
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
                <el-tag :type="getConsistencyStateType(row.consistency_state)" size="small">{{ getConsistencyStateLabel(row.consistency_state) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="total_count" label="同组位标" width="90" />
            <el-table-column prop="issued_count" label="已投放" width="80" />
            <el-table-column prop="pending_recycle_count" label="待回收" width="80" />
            <el-table-column prop="pending_review_count" label="待复核" width="80" />
            <el-table-column prop="open_anomaly_count" label="未闭环偏差" width="100">
              <template #default="{ row }">
                <span :class="{ 'is-alert': row.open_anomaly_count > 0 }">{{ row.open_anomaly_count }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="latest_flow_note" label="最近一次流转说明" min-width="180" show-overflow-tooltip />
            <el-table-column label="操作" width="110" fixed="right">
              <template #default="{ row }">
                <el-button link type="primary" size="small" @click="goToSignsByTrace(row.trace_code)">查看位标</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="charts-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>试听班次覆盖量</span>
            </div>
          </template>
          <div ref="sessionChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>座区变更热区</span>
            </div>
          </template>
          <div ref="areaChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="charts-row">
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>现场角色闭环量</span>
            </div>
          </template>
          <div ref="personChartRef" class="chart-container"></div>
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>待复核位标</span>
              <el-tag type="danger" size="small">{{ (stats.pending_review_list || []).length }} 项</el-tag>
            </div>
          </template>
          <div class="pending-review-list">
            <el-table :data="stats.pending_review_list || []" size="small" v-loading="loading">
              <el-table-column prop="sign_number" label="位标编号" width="120" />
              <el-table-column prop="applicable_session" label="试听班次" width="140" />
              <el-table-column prop="current_area" label="目标座区" width="140" />
              <el-table-column prop="responsible_person" label="现场负责人" width="100" />
              <el-table-column label="操作" width="80">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="goToReview">去复核</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="charts-row">
      <el-col :span="24">
        <el-card class="chart-card">
          <template #header>
            <div class="card-title">
              <span>近期现场偏差闭环</span>
              <el-button link type="primary" size="small" @click="goToAnomaly">查看闭环台账</el-button>
            </div>
          </template>
          <div class="anomaly-list">
            <el-table :data="stats.recent_anomalies || []" size="small" v-loading="loading">
              <el-table-column prop="id" label="偏差编号" width="90" />
              <el-table-column label="导引位标" width="140">
                <template #default="{ row }">
                  {{ row.guide_sign?.sign_number || '-' }}
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
              <el-table-column label="状态" width="90">
                <template #default="{ row }">
                  <el-tag :type="getAnomalyStatusType(row.current_status)" size="small">
                    {{ getAnomalyStatusLabel(row.current_status) }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="responsible_person" label="现场负责人" width="100" />
              <el-table-column prop="description" label="偏差描述" min-width="150" show-overflow-tooltip />
              <el-table-column prop="created_at" label="登记时间" width="160">
                <template #default="{ row }">
                  {{ formatDate(row.created_at) }}
                </template>
              </el-table-column>
              <el-table-column label="操作" width="100" fixed="right">
                <template #default="{ row }">
                  <el-button link type="primary" size="small" @click="goToAnomalyDetail(row)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { 
  Tickets, Clock, CircleCheck, Promotion, Refresh, Warning, Close,
  Loading, QuestionFilled, DocumentChecked, ChatLineSquare
} from '@element-plus/icons-vue'
import request from '@/utils/request'
import {
  getAnomalyStatusLabel, getAnomalyStatusType,
  getAnomalyTypeLabel, getAnomalyTypeType,
  getAnomalyLevelLabel, getAnomalyLevelType,
  getSceneScopeLabel, getSceneScopeType,
  getRiskLevelLabel, getRiskLevelType,
  getConsistencyStateLabel, getConsistencyStateType
} from '@/utils/statusMap'

const router = useRouter()
const loading = ref(false)
const stats = ref({})

const sessionChartRef = ref(null)
const areaChartRef = ref(null)
const personChartRef = ref(null)

let sessionChart = null
let areaChart = null
let personChart = null

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

async function fetchData() {
  loading.value = true
  try {
    stats.value = await request.get('/stats/overview')
    await nextTick()
    renderCharts()
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function renderCharts() {
  renderSessionChart()
  renderAreaChart()
  renderPersonChart()
}

function renderSessionChart() {
  if (!sessionChartRef.value) return
  
  if (sessionChart) {
    sessionChart.dispose()
  }
  
  sessionChart = echarts.init(sessionChartRef.value)
  
  const data = stats.value.session_usage || []
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(d => d.session),
      axisLabel: {
        rotate: 30,
        interval: 0
      }
    },
    yAxis: {
      type: 'value',
      minInterval: 1
    },
    series: [{
      name: '使用量',
      type: 'bar',
      data: data.map(d => d.count),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#667eea' },
          { offset: 1, color: '#764ba2' }
        ]),
        borderRadius: [4, 4, 0, 0]
      },
      barWidth: '50%'
    }]
  }
  
  sessionChart.setOption(option)
}

function renderAreaChart() {
  if (!areaChartRef.value) return
  
  if (areaChart) {
    areaChart.dispose()
  }
  
  areaChart = echarts.init(areaChartRef.value)
  
  const data = stats.value.area_conflicts || []
  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      minInterval: 1
    },
    yAxis: {
      type: 'category',
      data: data.map(d => d.area).reverse()
    },
    series: [{
      name: '调整次数',
      type: 'bar',
      data: data.map(d => d.conflict_count).reverse(),
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
          { offset: 0, color: '#f093fb' },
          { offset: 1, color: '#f5576c' }
        ]),
        borderRadius: [0, 4, 4, 0]
      },
      barWidth: '60%'
    }]
  }
  
  areaChart.setOption(option)
}

function renderPersonChart() {
  if (!personChartRef.value) return
  
  if (personChart) {
    personChart.dispose()
  }
  
  personChart = echarts.init(personChartRef.value)
  
  const data = stats.value.person_workload || []
  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      right: '5%',
      top: 'center'
    },
    series: [{
      name: '处理量',
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['35%', '50%'],
      avoidLabelOverlap: false,
      itemStyle: {
        borderRadius: 6,
        borderColor: '#fff',
        borderWidth: 2
      },
      label: {
        show: false,
        position: 'center'
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 18,
          fontWeight: 'bold'
        }
      },
      labelLine: {
        show: false
      },
      data: data.map((d, i) => ({
        value: d.count,
        name: d.person,
        itemStyle: {
          color: [
            '#667eea', '#f093fb', '#4facfe',
            '#43e97b', '#fa709a', '#fee140'
          ][i % 6]
        }
      }))
    }]
  }
  
  personChart.setOption(option)
}

function goToReview() {
  router.push('/review')
}

function goToAnomaly(status) {
  if (status) {
    router.push({ path: '/anomaly', query: { current_status: status } })
  } else {
    router.push('/anomaly')
  }
}

function goToAnomalyDetail(row) {
  router.push({ path: '/anomaly', query: { anomaly_id: row.id } })
}

function goToSignsByTrace(traceCode) {
  router.push({ path: '/signs', query: { trace_code: traceCode } })
}

function handleResize() {
  sessionChart?.resize()
  areaChart?.resize()
  personChart?.resize()
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  sessionChart?.dispose()
  areaChart?.dispose()
  personChart?.dispose()
  window.removeEventListener('resize', handleResize)
})
</script>

<style scoped>
.overview-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.stats-row {
  margin-bottom: 0;
}

.stat-card {
  background: white;
  border-radius: 8px;
  padding: 16px;
  display: flex;
  align-items: center;
  gap: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
}

.stat-card.total .stat-icon {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.stat-card.pending .stat-icon {
  background: linear-gradient(135deg, #f6d365, #fda085);
}

.stat-card.available .stat-icon {
  background: linear-gradient(135deg, #43e97b, #38f9d7);
}

.stat-card.issued .stat-icon {
  background: linear-gradient(135deg, #fa709a, #fee140);
}

.stat-card.recycle .stat-icon {
  background: linear-gradient(135deg, #30cfd0, #330867);
}

.stat-card.review .stat-icon {
  background: linear-gradient(135deg, #ff0844, #ffb199);
}

.stat-card.restored .stat-icon {
  background: linear-gradient(135deg, #a8edea, #fed6e3);
  color: #67c23a;
}

.stat-card.deactivated .stat-icon {
  background: linear-gradient(135deg, #bdc3c7, #2c3e50);
}

.stat-card.anomaly .stat-icon {
  background: linear-gradient(135deg, #ff6b6b, #ee5a52);
}

.anomaly-stats .stat-icon {
  width: 44px;
  height: 44px;
}

.anomaly-stats .stat-value {
  font-size: 20px;
}

.stat-card.anomaly-pending .stat-icon {
  background: linear-gradient(135deg, #ff9a56, #ff6b35);
}

.stat-card.anomaly-processing .stat-icon {
  background: linear-gradient(135deg, #4facfe, #00f2fe);
}

.stat-card.anomaly-confirm .stat-icon {
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.stat-card.anomaly-closed .stat-icon {
  background: linear-gradient(135deg, #43e97b, #38f9d7);
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-label {
  color: #909399;
  font-size: 13px;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
}

.charts-row {
  margin-bottom: 0;
}

.chart-card {
  height: 100%;
}

.card-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}

.chart-container {
  width: 100%;
  height: 300px;
}

.pending-review-list {
  max-height: 300px;
  overflow-y: auto;
}

.anomaly-list {
  max-height: 300px;
  overflow-y: auto;
}

.trace-batch-cards {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.trace-batch-item {
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 14px;
  cursor: pointer;
  transition: box-shadow 0.2s, border-color 0.2s;
  background: #fff;
}

.trace-batch-item:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.trace-batch-item.is-risky {
  border-color: #e6a23c;
  background: #fdf6ec;
}

.trace-batch-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  gap: 8px;
  flex-wrap: wrap;
}

.trace-code {
  font-weight: 600;
  font-size: 15px;
  color: #303133;
}

.trace-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.trace-batch-metrics {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-bottom: 12px;
}

.trace-batch-metrics .metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: 1;
}

.metric-label {
  font-size: 12px;
  color: #909399;
}

.metric-value {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
}

.metric-value.is-alert,
.is-alert {
  color: #f56c6c;
}

.trace-batch-note {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #606266;
  border-top: 1px dashed #ebeef5;
  padding-top: 10px;
}

.trace-batch-note span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-batch-table {
  margin-top: 8px;
}

</style>
