<template>
  <div class="health-stats">
    <!-- 筛选栏 -->
    <div class="filter-bar">
      <a-select
        v-model:value="filters.member_id"
        style="width: 180px"
        @change="onFilterChange"
        :options="memberOptions"
        placeholder="全部成员"
      />
      <a-select
        v-model:value="filters.year"
        style="width: 140px"
        @change="onFilterChange"
        :options="yearOptions"
        placeholder="全部年份"
      />
      <a-button @click="reloadAll" :loading="loading">刷新</a-button>
      <div class="filter-summary">
        <span v-if="agg">统计范围：{{ filters.member_id ? memberName(filters.member_id) : '全部成员' }} · {{ filters.year ? filters.year + ' 年' : '全部年份' }}</span>
      </div>
    </div>

    <a-spin :spinning="loading">
      <!-- KPI -->
      <div class="kpi-grid" v-if="agg">
        <div class="kpi" v-for="k in kpis" :key="k.label">
          <div class="kpi-icon" :style="{ background: k.bg, color: k.color }">{{ k.icon }}</div>
          <div class="kpi-body">
            <div class="kpi-val" :style="{ color: k.color }">{{ k.value }}<span class="kpi-unit">{{ k.unit }}</span></div>
            <div class="kpi-label">{{ k.label }}</div>
            <div class="kpi-sub">{{ k.sub }}</div>
          </div>
        </div>
      </div>

      <!-- 图表区 -->
      <a-row :gutter="16" style="margin-top: 16px" v-if="agg">
        <a-col :xs="24" :lg="14">
          <a-card :bordered="false" size="small" title="按年趋势（花费 / 就诊）">
            <div class="chart-box"><canvas ref="yearChartRef"></canvas></div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="10">
          <a-card :bordered="false" size="small" title="花费构成">
            <div class="chart-box"><canvas ref="catChartRef"></canvas></div>
            <div class="legend-extra" v-if="agg.expense_by_ref?.length">
              <span v-for="r in agg.expense_by_ref" :key="r.ref_type" class="legend-item">
                {{ r.ref_type }} <b>¥{{ fmt(r.amount) }}</b>
              </span>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <a-row :gutter="16" style="margin-top: 16px" v-if="agg">
        <a-col :xs="24" :lg="14">
          <a-card :bordered="false" size="small" :title="`${agg.trend_year} 年月度花费与就诊次数`">
            <div class="chart-box"><canvas ref="monthChartRef"></canvas></div>
          </a-card>
        </a-col>
        <a-col :xs="24" :lg="10">
          <a-card :bordered="false" size="small" title="就诊医院 Top">
            <template v-if="agg.hospitals?.length">
              <div v-for="h in agg.hospitals" :key="h.hospital" class="rank-row">
                <span class="rank-name">{{ h.hospital }}</span>
                <span class="rank-bar"><i :style="{ width: barWidth(h.count) }"></i></span>
                <span class="rank-val">{{ h.count }} 次</span>
              </div>
            </template>
            <a-empty v-else description="暂无就诊记录" :image-style="{ height: '60px' }" />
          </a-card>
        </a-col>
      </a-row>

      <!-- 按年 -->
      <a-card :bordered="false" size="small" title="按年统计" style="margin-top: 16px" v-if="agg">
        <a-table
          :data-source="agg.by_year"
          :columns="yearColumns"
          row-key="year"
          size="small"
          :pagination="false"
          :row-class-name="() => 'clickable-row'"
          :custom-row="(record) => ({ onClick: () => onYearRowClick(record) })"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'year'">
              <b>{{ record.year }}</b>
              <a-tag v-if="filters.year === record.year" color="blue" style="margin-left:6px">当前</a-tag>
            </template>
            <template v-else-if="column.key === 'cost'">¥{{ fmt(record.expense_total) }}</template>
            <template v-else-if="column.key === 'checkup_cost'">¥{{ fmt(record.checkup_cost) }}</template>
          </template>
        </a-table>
      </a-card>

      <!-- 按人 -->
      <a-card :bordered="false" size="small" title="按人统计" style="margin-top: 16px" v-if="agg">
        <a-table
          :data-source="agg.by_member"
          :columns="memberColumns"
          row-key="member_id"
          size="small"
          :pagination="false"
          :row-class-name="() => 'clickable-row'"
          :custom-row="(record) => ({ onClick: () => onMemberRowClick(record) })"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'name'">
              <b>{{ record.name }}</b>
              <span class="rel">{{ record.relationship }}</span>
              <a-tag v-if="filters.member_id === record.member_id" color="blue" style="margin-left:6px">当前</a-tag>
            </template>
            <template v-else-if="column.key === 'cost'">¥{{ fmt(record.expense_total) }}</template>
            <template v-else-if="column.key === 'checkup_cost'">¥{{ fmt(record.checkup_cost) }}</template>
            <template v-else-if="column.key === 'disease'">
              <span v-if="record.disease_active" class="danger">{{ record.disease_active }}</span>
              <span v-else>0</span>
              <span class="muted"> / {{ record.disease_new }} 新增</span>
            </template>
          </template>
        </a-table>
      </a-card>

      <!-- 疾病排行 -->
      <a-card :bordered="false" size="small" title="疾病排行（按就诊次数）" style="margin-top: 16px" v-if="agg">
        <a-table
          :data-source="agg.diseases"
          :columns="diseaseColumns"
          row-key="disease_id"
          size="small"
          :pagination="{ pageSize: 10, hideOnSinglePage: true }"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="statusColor(record.status)" :bordered="false">{{ record.status || '-' }}</a-tag>
            </template>
            <template v-else-if="column.key === 'expense'">¥{{ fmt(record.expense) }}</template>
          </template>
          <template #emptyText><a-empty description="当前筛选条件下暂无疾病记录" /></template>
        </a-table>
      </a-card>

      <!-- 成员健康卡片 -->
      <div class="section-title" style="margin-top: 22px">成员概览</div>
      <div class="overview-grid" v-if="overview.length">
        <div
          v-for="m in overview" :key="m.id"
          class="ov-card" :class="{ active: selectedMember === m.id }"
          @click="selectMember(m.id)"
        >
          <div class="ov-head">
            <div class="ov-avatar">
              <img v-if="m.photo_path" :src="'/' + m.photo_path" />
              <span v-else>{{ m.name?.slice(0, 1) }}</span>
            </div>
            <div>
              <div class="ov-name">{{ m.name }}<span class="ov-rel">{{ m.relationship }}</span></div>
              <div class="ov-age">{{ m.gender || '' }}<span v-if="m.birthday"> · {{ ageOf(m.birthday) }} 岁</span></div>
            </div>
          </div>
          <div class="ov-metrics">
            <div class="ov-m"><span class="ov-mn">{{ m.active_disease_count }}</span><span class="ov-ml">活动疾病</span></div>
            <div class="ov-m"><span class="ov-mn">{{ m.abnormal_items?.length || 0 }}</span><span class="ov-ml">异常指标</span></div>
          </div>
          <div class="ov-last">
            <template v-if="m.last_checkup_date">最近体检 {{ m.last_checkup_date }}</template>
            <template v-else>暂无体检记录</template>
          </div>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="暂无成员数据，请先在成员管理中添加" />

      <!-- 选中成员详情 -->
      <template v-if="selectedMember && overview.length">
        <a-row :gutter="16" style="margin-top: 20px">
          <a-col :span="14">
            <a-card :bordered="false" size="small" title="指标趋势">
              <div class="trend-controls">
                <a-select v-model:value="selectedItem" placeholder="选择指标" style="width: 200px" @change="loadTrend" :loading="itemLoading">
                  <a-select-option v-for="it in itemOptions" :key="it.item_name" :value="it.item_name">
                    {{ it.item_name }}（{{ it.count }}次）
                  </a-select-option>
                </a-select>
                <span v-if="!itemOptions.length" class="hint">该成员暂无量化指标数据（需在体检中录入数值型指标）</span>
              </div>
              <div class="chart-box">
                <canvas ref="trendChartRef"></canvas>
              </div>
            </a-card>
          </a-col>
          <a-col :span="10">
            <a-card :bordered="false" size="small" title="最近一次体检异常项">
              <template v-if="abnormal && abnormal.items.length">
                <div class="ab-head">
                  <span class="ab-date">{{ abnormal.checkup?.checkup_date }}</span>
                  <span class="ab-hosp">{{ abnormal.checkup?.hospital }}</span>
                </div>
                <div v-for="(it, idx) in abnormal.items" :key="idx" class="ab-row">
                  <span class="ab-name">{{ it.item_name }}</span>
                  <span class="ab-val">{{ it.value ?? it.text_value }} {{ it.unit }}</span>
                  <a-tag :color="flagColor(it.abnormal_flag)" :bordered="false" size="small">{{ it.abnormal_flag }}</a-tag>
                  <span class="ab-ref">参考 {{ it.reference_range || '-' }}</span>
                </div>
              </template>
              <a-empty v-else description="最近一次体检无异常项或暂无体检" :image-style="{ height: '60px' }" />
            </a-card>
          </a-col>
        </a-row>
      </template>
    </a-spin>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { Chart, registerables } from 'chart.js'
import { healthApi } from '@/api'

Chart.register(...registerables)

const loading = ref(false)
const agg = ref(null)
const filters = ref({ member_id: undefined, year: undefined })
const members = ref([])

const overview = ref([])
const selectedMember = ref(null)
const itemOptions = ref([])
const selectedItem = ref(undefined)
const itemLoading = ref(false)
const abnormal = ref(null)

const yearChartRef = ref(null)
const catChartRef = ref(null)
const monthChartRef = ref(null)
const trendChartRef = ref(null)
let yearChart = null, catChart = null, monthChart = null, trendChart = null

// ─── 工具 ───
const fmt = (n) => Number(n || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
const memberName = (id) => members.value.find(m => m.id === id)?.name || ''
const barWidth = (count) => {
  const max = Math.max(...(agg.value?.hospitals || []).map(h => h.count), 1)
  return Math.round((count / max) * 100) + '%'
}
const statusColor = (s) => ({ '治疗中': 'red', '慢性病': 'orange', '已治愈': 'green', '已停访': 'default' }[s] || 'default')
function ageOf(birthday) {
  if (!birthday) return '-'
  const b = new Date(birthday)
  if (isNaN(b.getTime())) return '-'
  const now = new Date()
  let age = now.getFullYear() - b.getFullYear()
  const m = now.getMonth() - b.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < b.getDate())) age--
  return age
}
function flagColor(f) {
  if (f === '偏高') return 'red'
  if (f === '偏低') return 'orange'
  if (f === '异常') return 'volcano'
  return 'green'
}

// ─── 筛选项 ───
const memberOptions = computed(() => [
  { value: undefined, label: '全部成员' },
  ...members.value.map(m => ({ value: m.id, label: `${m.name}（${m.relationship || ''}）` })),
])
const yearOptions = computed(() => [
  { value: undefined, label: '全部年份' },
  ...(agg.value?.years || []).map(y => ({ value: y, label: `${y} 年` })),
])

// ─── KPI ───
const kpis = computed(() => {
  const k = agg.value?.kpi || {}
  return [
    { label: '体检次数', value: k.checkup_count ?? 0, unit: '次', icon: '🩺', color: '#3b82f6', bg: 'rgba(59,130,246,.12)', sub: `体检记录费用 ¥${fmt(k.checkup_cost)}` },
    { label: '就诊次数', value: k.visit_count ?? 0, unit: '次', icon: '🏥', color: '#06b6d4', bg: 'rgba(6,182,212,.12)', sub: '含各疾病复诊' },
    { label: '花费合计', value: fmt(k.expense_total), unit: '元', icon: '💰', color: '#f59e0b', bg: 'rgba(245,158,11,.12)', sub: '医疗费用明细累计' },
    { label: '活动疾病', value: k.disease_active ?? 0, unit: '项', icon: '💊', color: '#ef4444', bg: 'rgba(239,68,68,.12)', sub: `治疗中 + 慢性病` },
    { label: '新增疾病', value: k.disease_new ?? 0, unit: '项', icon: '📌', color: '#8b5cf6', bg: 'rgba(139,92,246,.12)', sub: `档案总数 ${k.disease_total ?? 0}` },
    { label: '异常指标', value: k.abnormal_count ?? 0, unit: '项', icon: '⚠️', color: '#ec4899', bg: 'rgba(236,72,153,.12)', sub: '体检异常项累计' },
  ]
})

// ─── 表格列 ───
const yearColumns = [
  { title: '年份', key: 'year', dataIndex: 'year', width: 90 },
  { title: '体检次数', dataIndex: 'checkup_count', key: 'checkup_count', width: 100 },
  { title: '体检费用', key: 'checkup_cost', width: 110 },
  { title: '就诊次数', dataIndex: 'visit_count', key: 'visit_count', width: 100 },
  { title: '新增疾病', dataIndex: 'disease_new', key: 'disease_new', width: 100 },
  { title: '异常指标', dataIndex: 'abnormal_count', key: 'abnormal_count', width: 100 },
  { title: '花费合计', key: 'cost' },
]
const memberColumns = [
  { title: '成员', key: 'name', width: 160 },
  { title: '体检次数', dataIndex: 'checkup_count', key: 'checkup_count', width: 100 },
  { title: '体检费用', key: 'checkup_cost', width: 110 },
  { title: '就诊次数', dataIndex: 'visit_count', key: 'visit_count', width: 100 },
  { title: '疾病（活动/新增）', key: 'disease', width: 150 },
  { title: '异常指标', dataIndex: 'abnormal_count', key: 'abnormal_count', width: 100 },
  { title: '花费合计', key: 'cost' },
]
const diseaseColumns = [
  { title: '疾病', dataIndex: 'disease_name', key: 'disease_name' },
  { title: '成员', dataIndex: 'member_name', key: 'member_name', width: 100 },
  { title: '状态', key: 'status', width: 100 },
  { title: '确诊日期', dataIndex: 'diagnosed_date', key: 'diagnosed_date', width: 120 },
  { title: '就诊次数', dataIndex: 'visit_count', key: 'visit_count', width: 100 },
  { title: '花费', key: 'expense', width: 110 },
  { title: '最近就诊', dataIndex: 'last_visit', key: 'last_visit', width: 120 },
]

// ─── 数据加载 ───
async function loadAggregate() {
  loading.value = true
  try {
    const { data } = await healthApi.statsAggregate({
      member_id: filters.value.member_id,
      year: filters.value.year,
    })
    agg.value = data
  } catch (e) {
    message.error(e.response?.data?.detail || '加载统计失败')
  } finally {
    loading.value = false
  }
}

async function renderCharts() {
  if (!agg.value) return
  await nextTick()
  const a = agg.value
  const grid = { color: 'rgba(148,163,184,0.15)' }
  const tick = { color: '#94a3b8' }

  // 年度趋势：花费柱 + 就诊折线
  if (yearChartRef.value) {
    if (yearChart) yearChart.destroy()
    yearChart = new Chart(yearChartRef.value, {
      data: {
        labels: a.by_year.map(r => String(r.year)),
        datasets: [
          { type: 'bar', label: '花费（元）', data: a.by_year.map(r => r.expense_total), backgroundColor: 'rgba(59,130,246,.65)', borderRadius: 6, yAxisID: 'y' },
          { type: 'bar', label: '体检费用（元）', data: a.by_year.map(r => r.checkup_cost), backgroundColor: 'rgba(6,182,212,.55)', borderRadius: 6, yAxisID: 'y' },
          { type: 'line', label: '就诊次数', data: a.by_year.map(r => r.visit_count), borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,.15)', tension: 0.35, pointRadius: 4, yAxisID: 'y1' },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, color: tick.color } } },
        scales: {
          y: { beginAtZero: true, ticks: { color: tick.color }, grid, title: { display: true, text: '元', color: tick.color } },
          y1: { beginAtZero: true, position: 'right', ticks: { color: tick.color, precision: 0 }, grid: { display: false }, title: { display: true, text: '次', color: tick.color } },
          x: { ticks: { color: tick.color }, grid: { display: false } },
        },
      },
    })
  }

  // 花费构成
  if (catChartRef.value) {
    if (catChart) catChart.destroy()
    const rows = a.expense_by_category || []
    const palette = ['#3b82f6', '#06b6d4', '#f59e0b', '#ef4444', '#8b5cf6', '#10b981', '#ec4899', '#64748b']
    catChart = new Chart(catChartRef.value, {
      type: 'doughnut',
      data: {
        labels: rows.map(r => r.category),
        datasets: [{ data: rows.map(r => r.amount), backgroundColor: rows.map((_, i) => palette[i % palette.length]), borderWidth: 2, borderColor: '#fff' }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: '58%',
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 10, color: tick.color, font: { size: 11 } } } },
      },
    })
    if (!rows.length) {
      catChart.destroy(); catChart = null
    }
  }

  // 月度趋势
  if (monthChartRef.value) {
    if (monthChart) monthChart.destroy()
    monthChart = new Chart(monthChartRef.value, {
      data: {
        labels: a.monthly.map(m => `${m.month}月`),
        datasets: [
          { type: 'line', label: '花费（元）', data: a.monthly.map(m => m.amount), borderColor: '#3b82f6', backgroundColor: 'rgba(59,130,246,.12)', fill: true, tension: 0.35, pointRadius: 3, yAxisID: 'y' },
          { type: 'line', label: '就诊次数', data: a.monthly.map(m => m.visits), borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,.1)', tension: 0.35, pointRadius: 3, borderDash: [4, 3], yAxisID: 'y1' },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, color: tick.color } } },
        scales: {
          y: { beginAtZero: true, ticks: { color: tick.color }, grid, title: { display: true, text: '元', color: tick.color } },
          y1: { beginAtZero: true, position: 'right', ticks: { color: tick.color, precision: 0 }, grid: { display: false } },
          x: { ticks: { color: tick.color }, grid: { display: false } },
        },
      },
    })
  }
}

async function loadOverview() {
  try {
    const { data } = await healthApi.statsOverview()
    overview.value = data || []
    if (overview.value.length) {
      const first = filters.value.member_id || overview.value[0].id
      if (!selectedMember.value) await selectMember(first)
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  }
}

async function reloadAll() {
  await Promise.all([loadAggregate(), loadOverview()])
  await renderCharts()
}

async function onFilterChange() {
  await loadAggregate()
  await renderCharts()
  if (filters.value.member_id) await selectMember(filters.value.member_id)
}

function onYearRowClick(record) {
  filters.value.year = filters.value.year === record.year ? undefined : record.year
  onFilterChange()
}

function onMemberRowClick(record) {
  filters.value.member_id = filters.value.member_id === record.member_id ? undefined : record.member_id
  onFilterChange()
}

async function selectMember(id) {
  selectedMember.value = id
  selectedItem.value = undefined
  if (trendChart) { trendChart.destroy(); trendChart = null }
  await Promise.all([loadItems(id), loadAbnormal(id)])
  if (itemOptions.value.length) {
    selectedItem.value = itemOptions.value[0].item_name
    await loadTrend()
  }
}

async function loadItems(id) {
  itemLoading.value = true
  try {
    const { data } = await healthApi.statsItems(id)
    itemOptions.value = data || []
  } catch { itemOptions.value = [] } finally { itemLoading.value = false }
}

async function loadAbnormal(id) {
  try {
    const { data } = await healthApi.statsAbnormal(id)
    abnormal.value = data
  } catch { abnormal.value = null }
}

async function loadTrend() {
  if (!selectedItem.value) return
  try {
    const { data } = await healthApi.statsTrends(selectedMember.value, selectedItem.value)
    await nextTick()
    renderTrend(data || [])
  } catch (e) {
    message.error(e.response?.data?.detail || '加载趋势失败')
  }
}

function renderTrend(points) {
  if (trendChart) { trendChart.destroy(); trendChart = null }
  if (!trendChartRef.value) return
  trendChart = new Chart(trendChartRef.value, {
    type: 'line',
    data: {
      labels: points.map(p => p.date),
      datasets: [{
        label: selectedItem.value,
        data: points.map(p => p.value),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.12)',
        fill: true,
        tension: 0.3,
        pointRadius: 5,
        pointBackgroundColor: points.map(p => p.abnormal_flag === '正常' ? '#3b82f6' : '#ef4444'),
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            afterLabel: (ctx) => {
              const p = points[ctx.dataIndex]
              return `${p.unit || ''}  参考 ${p.reference_range || '-'}  ${p.abnormal_flag}`
            },
          },
        },
      },
      scales: {
        y: { beginAtZero: false, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.15)' } },
        x: { ticks: { color: '#94a3b8' }, grid: { display: false } },
      },
    },
  })
}

onMounted(async () => {
  // 成员列表用于筛选下拉
  try {
    const { data } = await healthApi.listMembers()
    members.value = Array.isArray(data) ? data : (data?.items || [])
  } catch { members.value = [] }
  await reloadAll()
})

onBeforeUnmount(() => {
  [yearChart, catChart, monthChart, trendChart].forEach(c => c && c.destroy())
})
</script>

<style scoped>
.health-stats { padding: 4px; }

.filter-bar {
  display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  margin-bottom: 16px; padding: 12px 14px; border-radius: 12px;
  background: var(--bg-card, #fff); border: 1px solid var(--border-color, #eef0f3);
}
.filter-summary { margin-left: auto; font-size: 12px; color: var(--text-tertiary, #94a3b8); }

.kpi-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
@media (min-width: 1600px) { .kpi-grid { grid-template-columns: repeat(6, minmax(0, 1fr)); } }
@media (max-width: 900px) { .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.kpi {
  display: flex; gap: 12px; align-items: center; padding: 14px 16px;
  background: var(--bg-card, #fff); border: 1px solid var(--border-color, #eef0f3);
  border-radius: 14px; transition: box-shadow .2s;
}
.kpi:hover { box-shadow: 0 6px 18px rgba(0,0,0,.06); }
.kpi-icon {
  width: 40px; height: 40px; border-radius: 12px; flex: none;
  display: flex; align-items: center; justify-content: center; font-size: 18px;
}
.kpi-body { min-width: 0; }
.kpi-val { font-size: 22px; font-weight: 700; line-height: 1.15; }
.kpi-unit { font-size: 12px; font-weight: 500; margin-left: 3px; color: var(--text-tertiary, #94a3b8); }
.kpi-label { font-size: 12px; color: var(--text-secondary, #64748b); margin-top: 2px; }
.kpi-sub { font-size: 11px; color: var(--text-tertiary, #94a3b8); margin-top: 2px; }

.chart-box { height: 260px; position: relative; }
.legend-extra { display: flex; gap: 14px; flex-wrap: wrap; margin-top: 8px; font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.legend-item b { color: var(--text-primary, #1e293b); margin-left: 2px; }

.rank-row { display: flex; align-items: center; gap: 10px; padding: 7px 0; font-size: 13px; }
.rank-name { width: 42%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary, #334155); }
.rank-bar { flex: 1; height: 6px; border-radius: 3px; background: var(--bg-secondary, #f1f5f9); overflow: hidden; }
.rank-bar i { display: block; height: 100%; border-radius: 3px; background: linear-gradient(90deg, #60a5fa, #3b82f6); }
.rank-val { width: 46px; text-align: right; color: var(--text-tertiary, #94a3b8); font-size: 12px; }

:deep(.clickable-row) { cursor: pointer; }
:deep(.clickable-row:hover td) { background: rgba(59,130,246,.06) !important; }
.rel { font-size: 12px; color: #3b82f6; margin-left: 6px; }
.danger { color: #ef4444; font-weight: 600; }
.muted { color: var(--text-tertiary, #94a3b8); font-size: 12px; }
.section-title { font-size: 14px; font-weight: 600; color: var(--text-primary, #1e293b); margin-bottom: 12px; }

.overview-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
.ov-card {
  background: var(--bg-card, #fff); border: 1px solid var(--border-color, #eee);
  border-radius: 14px; padding: 16px; cursor: pointer; transition: all 0.2s;
}
.ov-card:hover { box-shadow: 0 6px 18px rgba(0, 0, 0, 0.08); }
.ov-card.active { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15); }
.ov-head { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.ov-avatar {
  width: 44px; height: 44px; border-radius: 50%; overflow: hidden;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  display: flex; align-items: center; justify-content: center; color: #fff; font-size: 18px; font-weight: 600;
}
.ov-avatar img { width: 100%; height: 100%; object-fit: cover; }
.ov-name { font-size: 15px; font-weight: 600; color: var(--text-primary, #1e293b); }
.ov-rel { font-size: 12px; font-weight: 400; color: #3b82f6; margin-left: 6px; }
.ov-age { font-size: 12px; color: var(--text-tertiary, #94a3b8); margin-top: 2px; }
.ov-metrics { display: flex; gap: 10px; margin-bottom: 10px; }
.ov-m { flex: 1; text-align: center; background: var(--bg-secondary, #f8fafc); border-radius: 8px; padding: 8px 4px; }
.ov-mn { display: block; font-size: 18px; font-weight: 700; color: #ef4444; }
.ov-ml { font-size: 11px; color: var(--text-tertiary, #94a3b8); }
.ov-last { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.trend-controls { display: flex; align-items: center; gap: 12px; margin-bottom: 14px; }
.hint { font-size: 12px; color: var(--text-tertiary, #999); }
.ab-head { margin-bottom: 10px; display: flex; gap: 10px; align-items: baseline; }
.ab-date { font-weight: 600; font-size: 14px; }
.ab-hosp { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.ab-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-color, #f0f0f0); font-size: 13px; }
.ab-row:last-child { border-bottom: none; }
.ab-name { flex: 1; color: var(--text-primary, #334155); }
.ab-val { font-weight: 600; color: #ef4444; }
.ab-ref { font-size: 12px; color: var(--text-tertiary, #94a3b8); min-width: 80px; text-align: right; }
</style>
