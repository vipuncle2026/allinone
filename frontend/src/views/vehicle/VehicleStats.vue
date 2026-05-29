<template>
  <div>
    <!-- 车辆选择 -->
    <div class="filter-bar">
      <a-select v-model:value="selectedVehicleId" placeholder="选择车辆" style="width: 200px" @change="onVehicleChange">
        <a-select-option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.name }} ({{ v.plate || v.brand }})</a-select-option>
      </a-select>
      <a-radio-group v-model:value="viewMode" button-style="solid" @change="loadData" style="margin-left: 12px">
        <a-radio-button value="year">按年</a-radio-button>
        <a-radio-button value="month">按月</a-radio-button>
      </a-radio-group>
    </div>

    <div v-if="!selectedVehicleId" style="text-align: center; padding: 60px; color: #999">
      请先选择一辆车
    </div>

    <template v-else>
      <!-- ═══════ 汇总统计卡片 ═══════ -->
      <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 20px">
        <!-- 卡片1：记录时段（通用） -->
        <div class="stat-card" style="background: linear-gradient(135deg, #0ea5e9, #38bdf8)">
          <div class="stat-label">记录时段</div>
          <div class="stat-val">{{ summaryRange }}</div>
          <div class="stat-unit">{{ viewMode === 'year' ? '年' : '个月' }}</div>
        </div>

        <!-- 燃油车卡片 -->
        <template v-if="!isElectric">
          <div class="stat-card" style="background: linear-gradient(135deg, #059669, #10b981)">
            <div class="stat-label">总加油量</div>
            <div class="stat-val">{{ summary.fuel_liters }}</div>
            <div class="stat-unit">升</div>
          </div>
          <div class="stat-card" style="background: linear-gradient(135deg, #0891b2, #22d3ee)">
            <div class="stat-label">平均油耗</div>
            <div class="stat-val">{{ summary.avg_consumption }}</div>
            <div class="stat-unit">L/100km</div>
          </div>
          <div class="stat-card" style="background: linear-gradient(135deg, #b45309, #d97706)">
            <div class="stat-label">总油费</div>
            <div class="stat-val">¥{{ summary.fuel_cost }}</div>
            <div class="stat-unit">元</div>
          </div>
        </template>

        <!-- 电动车卡片 -->
        <template v-else>
          <div class="stat-card" style="background: linear-gradient(135deg, #2563eb, #3b82f6)">
            <div class="stat-label">总充电量</div>
            <div class="stat-val">{{ summary.energy_kwh }}</div>
            <div class="stat-unit">kWh</div>
          </div>
          <div class="stat-card" style="background: linear-gradient(135deg, #0891b2, #22d3ee)">
            <div class="stat-label">平均电耗</div>
            <div class="stat-val">{{ summary.avg_elec_consumption }}</div>
            <div class="stat-unit">kWh/100km</div>
          </div>
          <div class="stat-card" style="background: linear-gradient(135deg, #7c3aed, #8b5cf6)">
            <div class="stat-label">总电费</div>
            <div class="stat-val">¥{{ summary.elec_cost }}</div>
            <div class="stat-unit">元</div>
          </div>
        </template>

        <!-- 通用卡片 -->
        <div class="stat-card" style="background: linear-gradient(135deg, #ef4444, #f87171)">
          <div class="stat-label">总费用</div>
          <div class="stat-val">¥{{ summary.expense }}</div>
          <div class="stat-unit">元（维护/保险等）</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #6b7280, #9ca3af)">
          <div class="stat-label">总支出</div>
          <div class="stat-val">¥{{ summary.spending }}</div>
          <div class="stat-unit">元（{{ isElectric ? '电费' : '油费' }}+费用）</div>
        </div>
      </div>

      <!-- ═══════ 图表区域 第一行 ═══════ -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px">
        <div class="chart-card">
          <div class="chart-title">{{ isElectric ? '📈 电费 & 费用趋势' : '📈 油费 & 费用趋势' }}</div>
          <div class="chart-wrapper"><canvas ref="spendingChartRef"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">{{ isElectric ? '⚡ 充电量 & 电耗趋势' : '⛽ 加油量 & 油耗趋势' }}</div>
          <div class="chart-wrapper"><canvas ref="fuelChartRef"></canvas></div>
        </div>
      </div>

      <!-- ═══════ 图表区域 第二行 ═══════ -->
      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px">
        <div class="chart-card">
          <div class="chart-title">💰 费用分类占比</div>
          <div class="chart-wrapper"><canvas ref="expenseTypeChartRef"></canvas></div>
        </div>
        <div class="chart-card">
          <div class="chart-title">{{ isElectric ? '⚡ 电价波动趋势' : '⛽ 油价波动趋势' }}</div>
          <div class="chart-wrapper"><canvas ref="priceChartRef"></canvas></div>
        </div>
      </div>

      <!-- ═══════ 数据明细表格 ═══════ -->
      <a-card size="small">
        <template #title>
          <span>{{ viewMode === 'year' ? '📊 年度统计明细' : '📊 月度统计明细' }}</span>
        </template>
        <a-table :data-source="currentData" :columns="isElectric ? evColumns : fuelColumns" :pagination="{ pageSize: 12, showSizeChanger: false, showTotal: total => `共 ${total} 条` }" row-key="period" size="small" bordered>
          <template #bodyCell="{ column, record }">
            <!-- 通用 -->
            <template v-if="column.key === 'total_fuel_cost' || column.key === 'total_elec_cost'">
              <span style="color: #f59e0b; font-weight: 600">¥{{ (column.key === 'total_fuel_cost' ? record.total_fuel_cost : record.total_fuel_cost).toLocaleString() }}</span>
            </template>
            <template v-if="column.key === 'total_expense'">
              <span style="color: #ef4444; font-weight: 600">¥{{ record.total_expense.toLocaleString() }}</span>
            </template>
            <template v-if="column.key === 'total_spending'">
              <span style="color: #e11d48; font-weight: 700">¥{{ record.total_spending.toLocaleString() }}</span>
            </template>
            <!-- 燃油车 -->
            <template v-if="column.key === 'avg_consumption'">
              <span :style="{ color: record.avg_consumption > 10 ? '#ef4444' : '#059669', fontWeight: 600 }">
                {{ record.avg_consumption ? record.avg_consumption : '-' }}
              </span>
            </template>
            <template v-if="column.key === 'price_range'">
              <span>{{ record.min_price && record.max_price ? '¥' + record.min_price + ' ~ ¥' + record.max_price : '-' }}</span>
            </template>
            <!-- 电动车 -->
            <template v-if="column.key === 'avg_elec_consumption'">
              <span :style="{ color: record.avg_elec_consumption > 18 ? '#ef4444' : '#059669', fontWeight: 600 }">
                {{ record.avg_elec_consumption ? record.avg_elec_consumption : '-' }}
              </span>
            </template>
            <template v-if="column.key === 'elec_price_range'">
              <span>{{ record.min_elec_price && record.max_elec_price ? '¥' + record.min_elec_price + ' ~ ¥' + record.max_elec_price : '-' }}</span>
            </template>
          </template>
        </a-table>
      </a-card>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { vehicleApi } from '@/api/index'

// 图表
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const vehicles = ref([])
const selectedVehicleId = ref(null)
const viewMode = ref('month')
const loading = ref(false)
const analysisData = ref({ yearly: [], monthly: [], expense_by_type: [], yearly_expense_by_type: [] })

const spendingChartRef = ref(null)
const fuelChartRef = ref(null)
const expenseTypeChartRef = ref(null)
const priceChartRef = ref(null)

let spendingChart = null
let fuelChart = null
let expenseTypeChart = null
let priceChart = null

// ── 是否电动车 ──
const isElectric = computed(() => {
  const v = vehicles.value.find(v => v.id === selectedVehicleId.value)
  if (!v) return false
  const ft = (v.fuel_type || '').trim()
  return ft === '电动' || ft === '纯电' || ft === '纯电动'
})

const currentData = computed(() => {
  return viewMode.value === 'year' ? analysisData.value.yearly : analysisData.value.monthly
})

// 图表专用：取最近12个月，避免图表 label 过多
const chartData = computed(() => {
  const data = currentData.value
  if (data.length <= 12) return data
  return data.slice(data.length - 12)
})

// ── 汇总统计 ──
const summary = computed(() => {
  const data = currentData.value
  if (!data.length) return { range: '-', fuel_liters: '0', fuel_cost: '0', expense: '0', spending: '0', energy_kwh: '0', elec_cost: '0', avg_consumption: '-', avg_elec_consumption: '-' }
  const fuel_liters = data.reduce((s, r) => s + (r.total_fuel_liters || 0), 0)
  const fuel_cost = data.reduce((s, r) => s + (r.total_fuel_cost || 0), 0)
  const expense = data.reduce((s, r) => s + (r.total_expense || 0), 0)
  const spending = data.reduce((s, r) => s + (r.total_spending || 0), 0)
  const energy_kwh = data.reduce((s, r) => s + (r.total_energy_kwh || 0), 0)
  // 加权平均油耗：按各期加油量加权
  const fuelItems = data.filter(r => r.avg_consumption && r.total_fuel_liters > 0)
  const avg_consumption = fuelItems.length
    ? fuelItems.reduce((s, r) => s + r.avg_consumption * r.total_fuel_liters, 0) / fuelItems.reduce((s, r) => s + r.total_fuel_liters, 0)
    : null
  // 加权平均电耗：按各期充电量加权
  const elecItems = data.filter(r => r.avg_elec_consumption && r.total_energy_kwh > 0)
  const avg_elec_consumption = elecItems.length
    ? elecItems.reduce((s, r) => s + r.avg_elec_consumption * r.total_energy_kwh, 0) / elecItems.reduce((s, r) => s + r.total_energy_kwh, 0)
    : null
  return {
    fuel_liters: fuel_liters.toFixed(1),
    fuel_cost: fuel_cost.toLocaleString(undefined, { maximumFractionDigits: 0 }),
    expense: expense.toLocaleString(undefined, { maximumFractionDigits: 0 }),
    spending: spending.toLocaleString(undefined, { maximumFractionDigits: 0 }),
    energy_kwh: energy_kwh.toFixed(1),
    elec_cost: fuel_cost.toLocaleString(undefined, { maximumFractionDigits: 0 }),
    avg_consumption: avg_consumption ? avg_consumption.toFixed(1) : '-',
    avg_elec_consumption: avg_elec_consumption ? avg_elec_consumption.toFixed(1) : '-',
  }
})

const summaryRange = computed(() => {
  const data = currentData.value
  if (!data.length) return '-'
  return `${data.length}`
})

// ── 燃油车表格列 ──
const fuelColumns = [
  { title: '年份/月份', key: 'period', dataIndex: 'period', width: 100, align: 'center' },
  { title: '加油次数', key: 'fuel_count', dataIndex: 'fuel_count', width: 90, align: 'center' },
  { title: '加油量(L)', key: 'total_fuel_liters', dataIndex: 'total_fuel_liters', width: 100, align: 'center' },
  { title: '总油费', key: 'total_fuel_cost', dataIndex: 'total_fuel_cost', width: 110, align: 'center' },
  { title: '平均油耗', key: 'avg_consumption', dataIndex: 'avg_consumption', width: 100, align: 'center' },
  { title: '油价范围', key: 'price_range', width: 150, align: 'center' },
  { title: '费用笔数', key: 'expense_count', dataIndex: 'expense_count', width: 90, align: 'center' },
  { title: '费用总额', key: 'total_expense', dataIndex: 'total_expense', width: 110, align: 'center' },
  { title: '总支出', key: 'total_spending', dataIndex: 'total_spending', width: 120, align: 'center' },
]

// ── 电动车表格列 ──
const evColumns = [
  { title: '年份/月份', key: 'period', dataIndex: 'period', width: 100, align: 'center' },
  { title: '充电次数', key: 'fuel_count', dataIndex: 'fuel_count', width: 90, align: 'center' },
  { title: '充电量(kWh)', key: 'total_energy_kwh', dataIndex: 'total_energy_kwh', width: 110, align: 'center' },
  { title: '总电费', key: 'total_elec_cost', dataIndex: 'total_fuel_cost', width: 110, align: 'center' },
  { title: '平均电耗', key: 'avg_elec_consumption', dataIndex: 'avg_elec_consumption', width: 100, align: 'center' },
  { title: '电价范围', key: 'elec_price_range', width: 150, align: 'center' },
  { title: '费用笔数', key: 'expense_count', dataIndex: 'expense_count', width: 90, align: 'center' },
  { title: '费用总额', key: 'total_expense', dataIndex: 'total_expense', width: 110, align: 'center' },
  { title: '总支出', key: 'total_spending', dataIndex: 'total_spending', width: 120, align: 'center' },
]

onMounted(async () => {
  try {
    const { data } = await vehicleApi.list()
    vehicles.value = data
    if (data.length > 0) {
      selectedVehicleId.value = data[0].id
      loadData()
    }
  } catch (e) { message.error('加载车辆列表失败') }
})

function onVehicleChange() {
  loadData()
}

async function loadData() {
  if (!selectedVehicleId.value) return
  loading.value = true
  try {
    const { data } = await vehicleApi.getAnalysis(selectedVehicleId.value)
    analysisData.value = data
    await nextTick()
    renderCharts()
  } catch (e) {
    message.error('加载统计数据失败')
  } finally {
    loading.value = false
  }
}

function destroyCharts() {
  if (spendingChart) { spendingChart.destroy(); spendingChart = null }
  if (fuelChart) { fuelChart.destroy(); fuelChart = null }
  if (expenseTypeChart) { expenseTypeChart.destroy(); expenseTypeChart = null }
  if (priceChart) { priceChart.destroy(); priceChart = null }
}

function renderCharts() {
  destroyCharts()
  const data = chartData.value
  if (!data.length) return

  const labels = data.map(r => r.period)
  const ev = isElectric.value

  // ── 1. 费用趋势（柱状图）──
  spendingChart = new Chart(spendingChartRef.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: ev ? '电费' : '油费',
          data: data.map(r => r.total_fuel_cost || 0),
          backgroundColor: ev ? 'rgba(139, 92, 246, 0.7)' : 'rgba(245, 158, 11, 0.7)',
          borderColor: ev ? '#8b5cf6' : '#f59e0b',
          borderWidth: 1,
        },
        {
          label: '费用',
          data: data.map(r => r.total_expense || 0),
          backgroundColor: 'rgba(239, 68, 68, 0.7)',
          borderColor: '#ef4444',
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { display: false } },
        y: { beginAtZero: true, ticks: { callback: v => '¥' + v.toLocaleString() } },
      },
    },
  })

  // ── 2. 加油量/充电量 & 油耗/电耗趋势 ──
  fuelChart = new Chart(fuelChartRef.value, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: ev ? '充电量(kWh)' : '加油量(L)',
          data: data.map(r => ev ? (r.total_energy_kwh || 0) : (r.total_fuel_liters || 0)),
          backgroundColor: ev ? 'rgba(37, 99, 235, 0.7)' : 'rgba(5, 150, 105, 0.7)',
          borderColor: ev ? '#2563eb' : '#059669',
          borderWidth: 1,
          yAxisID: 'y',
        },
        {
          label: ev ? '平均电耗' : '平均油耗',
          data: data.map(r => ev ? r.avg_elec_consumption : r.avg_consumption),
          type: 'line',
          borderColor: ev ? '#f59e0b' : '#8b5cf6',
          backgroundColor: ev ? 'rgba(245, 158, 11, 0.1)' : 'rgba(139, 92, 246, 0.1)',
          tension: 0.3,
          yAxisID: 'y1',
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { display: false } },
        y: {
          beginAtZero: true, position: 'left',
          title: { display: true, text: ev ? '充电量(kWh)' : '加油量(L)' },
        },
        y1: {
          beginAtZero: true, position: 'right',
          title: { display: true, text: ev ? '电耗(kWh/100km)' : '油耗(L/100km)' },
          grid: { drawOnChartArea: false },
        },
      },
    },
  })

  // ── 3. 费用分类饼图（通用，不变）──
  const expByType = analysisData.value.expense_by_type || []
  if (expByType.length > 0) {
    const colors = ['#0ea5e9', '#059669', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16']
    expenseTypeChart = new Chart(expenseTypeChartRef.value, {
      type: 'doughnut',
      data: {
        labels: expByType.map(r => r.type),
        datasets: [{
          data: expByType.map(r => r.total),
          backgroundColor: expByType.map((_, i) => colors[i % colors.length]),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right' },
          tooltip: { callbacks: { label: ctx => `${ctx.label}: ¥${ctx.parsed.toLocaleString()}` } },
        },
      },
    })
  }

  // ── 4. 价格波动趋势 ──
  priceChart = new Chart(priceChartRef.value, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: ev ? '最低电价' : '最低油价',
          data: data.map(r => ev ? r.min_elec_price : r.min_price),
          borderColor: '#059669',
          backgroundColor: 'rgba(5, 150, 105, 0.1)',
          tension: 0.3,
          fill: false,
        },
        {
          label: ev ? '最高电价' : '最高油价',
          data: data.map(r => ev ? r.max_elec_price : r.max_price),
          borderColor: '#ef4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          tension: 0.3,
          fill: false,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: {
        x: { grid: { display: false } },
        y: { ticks: { callback: v => '¥' + (v != null ? v.toFixed(2) : '-') } },
      },
    },
  })
}
</script>

<style scoped>
.filter-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 20px; flex-wrap: wrap; }
.stat-card { border-radius: 12px; padding: 16px; color: #fff; }
.stat-label { font-size: 12px; opacity: .85; margin-bottom: 6px; }
.stat-val { font-size: 24px; font-weight: 800; }
.stat-unit { font-size: 11px; opacity: .7; margin-top: 4px; }
.chart-card { background: #fff; border-radius: 12px; padding: 16px; box-shadow: 0 1px 4px rgba(0,0,0,.06); }
.chart-title { font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #333; }
.chart-wrapper { position: relative; height: 260px; }
</style>
