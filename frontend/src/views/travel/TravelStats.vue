<template>
  <div class="travel-stats">
    <a-page-header title="旅行统计分析" sub-title="查看所有旅行的数据统计" @back="$router.push('/travel')" />

    <!-- ═══════ 总览卡片 ═══════ -->
    <a-row :gutter="16" style="margin-bottom: 20px">
      <a-col :span="6" v-for="(item, idx) in overviewCards" :key="idx">
        <div :class="['overview-card', `overview-card-${item.theme}`]">
          <div class="overview-icon">{{ item.icon }}</div>
          <div class="overview-body">
            <div class="overview-value">{{ item.prefix }}{{ item.value }}</div>
            <div class="overview-label">{{ item.label }}</div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- ═══════ 分类 & 排行 ═══════ -->
    <a-row :gutter="16">
      <a-col :span="12">
        <a-card
          :bordered="false"
          size="small"
          class="section-card"
          :body-style="{ padding: '20px' }"
        >
          <div class="section-title">
            <span class="section-title-icon">📊</span>
            分类支出统计
          </div>
          <a-table
            :columns="categoryColumns"
            :data-source="categoryStats"
            :pagination="false"
            size="small"
            row-key="category"
            class="stats-table"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'icon'">
                <span class="cat-icon">{{ record.icon }}</span>
                <span class="cat-name">{{ record.category }}</span>
              </template>
              <template v-if="column.key === 'total'">
                <span class="amount-text">¥{{ record.total?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
              </template>
              <template v-if="column.key === 'percent'">
                <div class="percent-bar-wrap">
                  <div class="percent-bar" :style="{ width: record.percent + '%', background: record.color }"></div>
                  <span class="percent-text">{{ record.percent }}%</span>
                </div>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <a-col :span="12">
        <a-card
          :bordered="false"
          size="small"
          class="section-card"
          :body-style="{ padding: '20px' }"
        >
          <div class="section-title">
            <span class="section-title-icon">🏆</span>
            旅行支出排行
          </div>
          <a-table
            :columns="tripColumns"
            :data-source="tripRanking"
            :pagination="false"
            size="small"
            row-key="id"
            class="stats-table"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'rank'">
                <span :class="['rank-badge', record.rank <= 3 ? `rank-${record.rank}` : '']">{{ record.rank }}</span>
              </template>
              <template v-if="column.key === 'total_expense'">
                <span class="amount-text">¥{{ record.total_expense?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
              </template>
              <template v-if="column.key === 'total_km'">
                <span class="km-text">{{ record.total_km?.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) }} km</span>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- ═══════ 按年统计 ═══════ -->
    <a-card
      :bordered="false"
      size="small"
      class="section-card yearly-section"
      :body-style="{ padding: '24px' }"
    >
      <div class="yearly-header">
        <div class="section-title" style="margin-bottom: 0">
          <span class="section-title-icon">📅</span>
          按年统计分析
        </div>
        <a-select
          v-model:value="selectedYear"
          style="width: 130px"
          placeholder="选择年份"
          @change="onYearChange"
        >
          <a-select-option value="all">全部年份</a-select-option>
          <a-select-option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</a-select-option>
        </a-select>
      </div>

      <a-spin :spinning="yearlyLoading">
        <!-- ─── 全部年份视图 ─── -->
        <template v-if="selectedYear === 'all' && yearlyData.length > 0">
          <a-row :gutter="16" style="margin-top: 20px">
            <a-col :span="12">
              <div class="chart-panel">
                <div class="chart-panel-title">💰 年度支出对比</div>
                <div class="chart-box"><canvas ref="yearlyExpenseChartRef"></canvas></div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="chart-panel">
                <div class="chart-panel-title">🧳 年度旅行次数 & 里程</div>
                <div class="chart-box"><canvas ref="yearlyTripChartRef"></canvas></div>
              </div>
            </a-col>
          </a-row>

          <div class="yearly-table-wrap">
            <a-table
              :columns="yearlySummaryColumns"
              :data-source="yearlyData"
              :pagination="false"
              size="small"
              row-key="year"
              class="yearly-summary-table"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'year'">
                  <span class="year-badge">{{ record.year }}</span>
                </template>
                <template v-if="column.key === 'total_expense'">
                  <span class="expense-text">¥{{ record.total_expense?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                </template>
                <template v-if="column.key === 'avg_expense_per_day'">
                  <span class="sub-amount">¥{{ record.avg_expense_per_day?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                </template>
                <template v-if="column.key === 'avg_expense_per_trip'">
                  <span class="sub-amount">¥{{ record.avg_expense_per_trip?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                </template>
                <template v-if="column.key === 'trip_count'">
                  <span class="count-badge">{{ record.trip_count }}</span>
                </template>
              </template>
            </a-table>
          </div>
        </template>

        <!-- ─── 单年详情视图 ─── -->
        <template v-if="selectedYear !== 'all' && currentYearData">
          <a-row :gutter="16" style="margin-top: 20px">
            <a-col :span="6" v-for="(kpi, idx) in yearKpis" :key="idx">
              <div :class="['year-kpi', `year-kpi-${kpi.theme}`]">
                <div class="year-kpi-icon">{{ kpi.icon }}</div>
                <div class="year-kpi-value">{{ kpi.display }}</div>
                <div class="year-kpi-label">{{ kpi.label }}</div>
              </div>
            </a-col>
          </a-row>

          <a-row :gutter="16" style="margin-top: 20px">
            <a-col :span="12">
              <div class="chart-panel">
                <div class="chart-panel-title">📊 支出分类占比</div>
                <div class="chart-box"><canvas ref="yearCatChartRef"></canvas></div>
              </div>
            </a-col>
            <a-col :span="12">
              <div class="chart-panel">
                <div class="chart-panel-title">🚀 交通方式里程</div>
                <div class="chart-box"><canvas ref="yearTransportChartRef"></canvas></div>
              </div>
            </a-col>
          </a-row>

          <div class="yearly-table-wrap" style="margin-top: 20px">
            <a-table
              :columns="yearTripColumns"
              :data-source="currentYearData.trips"
              :pagination="false"
              size="small"
              row-key="id"
              class="yearly-summary-table"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'date_range'">
                  <span class="date-range-text">{{ record.start_date || '?' }} ~ {{ record.end_date || '?' }}</span>
                </template>
                <template v-if="column.key === 'total_expense'">
                  <span class="expense-text">¥{{ record.total_expense?.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</span>
                </template>
                <template v-if="column.key === 'budget_usage'">
                  <div v-if="record.budget > 0" class="budget-bar-wrap">
                    <a-progress
                      :percent="Math.min(100, Math.round(record.total_expense / record.budget * 100))"
                      :size="4"
                      :stroke-color="record.total_expense > record.budget ? '#ef4444' : '#10b981'"
                      :show-info="false"
                    />
                    <span class="budget-pct" :class="{ over: record.total_expense > record.budget }">
                      {{ Math.round(record.total_expense / record.budget * 100) }}%
                    </span>
                  </div>
                  <span v-else class="no-budget">未设预算</span>
                </template>
              </template>
            </a-table>
          </div>
        </template>

        <!-- 无数据 -->
        <a-empty v-if="yearlyData.length === 0 && !yearlyLoading" description="暂无旅行数据" style="padding: 40px 0" />
      </a-spin>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { travelApi } from '@/api'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

// ─── 全局统计 ───
const stats = ref({ tripCount: 0, totalExpense: 0, totalKm: 0, avgExpense: 0 })
const categoryStats = ref([])
const tripRanking = ref([])

const overviewCards = computed(() => [
  { icon: '🧳', label: '总旅行次数', value: stats.value.tripCount, prefix: '', theme: 'blue' },
  { icon: '💰', label: '总支出', value: stats.value.totalExpense.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), prefix: '¥', theme: 'rose' },
  { icon: '🗺️', label: '总里程', value: stats.value.totalKm.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }), prefix: '', theme: 'amber' },
  { icon: '🏷️', label: '平均每次支出', value: stats.value.avgExpense.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), prefix: '¥', theme: 'violet' },
])

const categoryColumns = [
  { title: '分类', dataIndex: 'category', key: 'icon' },
  { title: '金额', key: 'total', width: 130, align: 'right' },
  { title: '占比', key: 'percent' },
]

const tripColumns = [
  { title: '#', key: 'rank', width: 50, align: 'center' },
  { title: '旅行名称', dataIndex: 'name', ellipsis: true },
  { title: '支出', key: 'total_expense', width: 130, align: 'right' },
  { title: '里程', key: 'total_km', width: 110, align: 'right' },
]

// ─── 按年统计 ───
const yearlyData = ref([])
const selectedYear = ref('all')
const yearlyLoading = ref(false)
const yearOptions = ref([])

const yearlyExpenseChartRef = ref(null)
const yearlyTripChartRef = ref(null)
const yearCatChartRef = ref(null)
const yearTransportChartRef = ref(null)

let charts = []

const EXPENSE_CATEGORIES = {
  '交通': { icon: '🚄', color: '#3B82F6' },
  '住宿': { icon: '🏨', color: '#8B5CF6' },
  '餐饮': { icon: '🍜', color: '#F59E0B' },
  '景点': { icon: '🎫', color: '#10B981' },
  '购物': { icon: '🛍️', color: '#EC4899' },
  '通讯': { icon: '📱', color: '#6366F1' },
  '其他': { icon: '📌', color: '#6B7280' },
}

const TRANSPORT_TYPES = {
  '飞机': { color: '#3B82F6' },
  '高铁': { color: '#2D7D6F' },
  '汽车': { color: '#F59E0B' },
  '巴士': { color: '#8B5CF6' },
  '轮船': { color: '#06B6D4' },
  '步行': { color: '#10B981' },
  '骑行': { color: '#EC4899' },
  '其他': { color: '#6B7280' },
}

const yearlySummaryColumns = [
  { title: '年份', dataIndex: 'year', key: 'year', width: 90 },
  { title: '旅行次数', dataIndex: 'trip_count', key: 'trip_count', width: 100, align: 'center' },
  { title: '旅行天数', dataIndex: 'total_days', width: 100, align: 'center' },
  { title: '总里程(km)', dataIndex: 'total_km', width: 120, align: 'right' },
  { title: '总支出', key: 'total_expense', width: 140, align: 'right' },
  { title: '次均支出', key: 'avg_expense_per_trip', width: 120, align: 'right' },
  { title: '日均支出', key: 'avg_expense_per_day', width: 120, align: 'right' },
]

const yearTripColumns = [
  { title: '旅行名称', dataIndex: 'name', ellipsis: true },
  { title: '目的地', dataIndex: 'destination', width: 100, ellipsis: true },
  { title: '日期范围', key: 'date_range', width: 180 },
  { title: '天数', dataIndex: 'days', width: 70, align: 'center' },
  { title: '里程(km)', dataIndex: 'total_km', width: 100, align: 'right' },
  { title: '支出', key: 'total_expense', width: 120, align: 'right' },
  { title: '预算使用', key: 'budget_usage', width: 160 },
]

const currentYearData = computed(() => {
  if (selectedYear.value === 'all') return null
  return yearlyData.value.find(y => y.year === selectedYear.value) || null
})

const yearKpis = computed(() => {
  const d = currentYearData.value
  if (!d) return []
  return [
    { icon: '🧳', label: '旅行次数', display: d.trip_count, theme: 'blue' },
    { icon: '💰', label: '总支出', display: '¥' + d.total_expense?.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 }), theme: 'rose' },
    { icon: '🗺️', label: '总里程(km)', display: d.total_km?.toLocaleString(undefined, { minimumFractionDigits: 1, maximumFractionDigits: 1 }), theme: 'amber' },
    { icon: '📅', label: '旅行天数', display: d.total_days, theme: 'violet' },
  ]
})

function onYearChange() {
  renderYearlyCharts()
}

function destroyCharts() {
  charts.forEach(c => c.destroy())
  charts = []
}

function renderYearlyCharts() {
  destroyCharts()
  nextTick(() => {
    if (selectedYear.value === 'all') {
      renderAllYearsCharts()
    } else if (currentYearData.value) {
      renderSingleYearCharts(currentYearData.value)
    }
  })
}

function renderAllYearsCharts() {
  if (yearlyExpenseChartRef.value) {
    const sorted = [...yearlyData.value].sort((a, b) => a.year - b.year)
    const chart = new Chart(yearlyExpenseChartRef.value, {
      type: 'bar',
      data: {
        labels: sorted.map(y => y.year + '年'),
        datasets: [{
          label: '总支出(¥)',
          data: sorted.map(y => y.total_expense),
          backgroundColor: sorted.map((_, i) => i === sorted.length - 1 ? 'rgba(244, 63, 94, 0.75)' : 'rgba(99, 102, 241, 0.55)'),
          borderColor: sorted.map((_, i) => i === sorted.length - 1 ? '#f43f5e' : '#6366f1'),
          borderWidth: 1,
          borderRadius: 8,
          barThickness: 36,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          y: { beginAtZero: true, ticks: { callback: v => '¥' + v.toLocaleString(), color: '#94a3b8', font: { size: 11 } }, grid: { color: 'rgba(148,163,184,0.12)' } },
          x: { ticks: { color: '#64748b', font: { size: 11 } }, grid: { display: false } },
        },
      },
    })
    charts.push(chart)
  }

  if (yearlyTripChartRef.value) {
    const sorted = [...yearlyData.value].sort((a, b) => a.year - b.year)
    const chart = new Chart(yearlyTripChartRef.value, {
      type: 'bar',
      data: {
        labels: sorted.map(y => y.year + '年'),
        datasets: [
          {
            label: '旅行次数',
            data: sorted.map(y => y.trip_count),
            backgroundColor: 'rgba(16, 185, 129, 0.55)',
            borderColor: '#10b981',
            borderWidth: 1,
            borderRadius: 8,
            barThickness: 36,
            yAxisID: 'y',
          },
          {
            label: '里程(km)',
            data: sorted.map(y => y.total_km),
            type: 'line',
            borderColor: '#f59e0b',
            backgroundColor: 'rgba(245, 158, 11, 0.08)',
            fill: true,
            tension: 0.4,
            pointRadius: 5,
            pointBackgroundColor: '#f59e0b',
            pointBorderColor: '#fff',
            pointBorderWidth: 2,
            yAxisID: 'y1',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { position: 'top', labels: { boxWidth: 12, padding: 16, color: '#64748b' } } },
        scales: {
          y: { beginAtZero: true, position: 'left', title: { display: true, text: '次数', color: '#64748b' }, ticks: { color: '#94a3b8' }, grid: { color: 'rgba(148,163,184,0.12)' } },
          y1: { beginAtZero: true, position: 'right', grid: { drawOnChartArea: false }, title: { display: true, text: 'km', color: '#64748b' }, ticks: { color: '#94a3b8' } },
          x: { ticks: { color: '#64748b', font: { size: 11 } }, grid: { display: false } },
        },
      },
    })
    charts.push(chart)
  }
}

function renderSingleYearCharts(yearData) {
  const catBreakdown = yearData.category_breakdown || {}
  const tpBreakdown = yearData.transport_breakdown || {}

  if (yearCatChartRef.value && Object.keys(catBreakdown).length > 0) {
    const cats = Object.entries(catBreakdown).sort((a, b) => b[1] - a[1])
    const chart = new Chart(yearCatChartRef.value, {
      type: 'doughnut',
      data: {
        labels: cats.map(([k]) => `${EXPENSE_CATEGORIES[k]?.icon || '📌'} ${k}`),
        datasets: [{
          data: cats.map(([, v]) => v),
          backgroundColor: cats.map(([k]) => EXPENSE_CATEGORIES[k]?.color || '#6B7280'),
          borderWidth: 3,
          borderColor: '#fff',
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '55%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 14, padding: 14, color: '#475569', font: { size: 12 } } },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            titleColor: '#f8fafc',
            bodyColor: '#e2e8f0',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: ctx => ` ${ctx.label}: ¥${ctx.parsed.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
            },
          },
        },
      },
    })
    charts.push(chart)
  }

  if (yearTransportChartRef.value && Object.keys(tpBreakdown).length > 0) {
    const tps = Object.entries(tpBreakdown).sort((a, b) => b[1] - a[1])
    const chart = new Chart(yearTransportChartRef.value, {
      type: 'doughnut',
      data: {
        labels: tps.map(([k]) => k),
        datasets: [{
          data: tps.map(([, v]) => v),
          backgroundColor: tps.map(([k]) => TRANSPORT_TYPES[k]?.color || '#6B7280'),
          borderWidth: 3,
          borderColor: '#fff',
          hoverOffset: 8,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '55%',
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 14, padding: 14, color: '#475569', font: { size: 12 } } },
          tooltip: {
            backgroundColor: 'rgba(15, 23, 42, 0.85)',
            titleColor: '#f8fafc',
            bodyColor: '#e2e8f0',
            padding: 12,
            cornerRadius: 8,
            callbacks: {
              label: ctx => ` ${ctx.label}: ${ctx.parsed.toLocaleString(undefined, { minimumFractionDigits: 1 })} km`,
            },
          },
        },
      },
    })
    charts.push(chart)
  }
}

onMounted(async () => {
  try {
    const { data: trips } = await travelApi.listTrips()
    const list = trips || []
    const totalExpense = list.reduce((s, t) => s + (t.total_expense || 0), 0)
    const totalKm = list.reduce((s, t) => s + (t.total_km || 0), 0)
    stats.value = {
      tripCount: list.length,
      totalExpense: Math.round(totalExpense * 100) / 100,
      totalKm: Math.round(totalKm * 10) / 10,
      avgExpense: list.length > 0 ? Math.round(totalExpense / list.length * 100) / 100 : 0,
    }

    const sorted = [...list].sort((a, b) => (b.total_expense || 0) - (a.total_expense || 0))
    tripRanking.value = sorted.map((t, i) => ({ ...t, rank: i + 1 }))
  } catch (e) { /* ignore */ }

  try {
    const { data: cats } = await travelApi.getCategoryStats()
    const total = cats.reduce((s, c) => s + (c.total || 0), 0)
    categoryStats.value = (cats || []).map(c => ({
      ...c,
      percent: total > 0 ? Math.round(c.total / total * 1000) / 10 : 0,
    }))
  } catch (e) { /* ignore */ }

  yearlyLoading.value = true
  try {
    const { data } = await travelApi.getYearlyStats()
    yearlyData.value = data || []
    yearOptions.value = (data || []).map(y => y.year).sort((a, b) => b - a)
    await nextTick()
    renderYearlyCharts()
  } catch (e) {
    console.error('加载年度统计失败', e)
  } finally {
    yearlyLoading.value = false
  }
})

onBeforeUnmount(() => {
  destroyCharts()
})
</script>

<style scoped>
.travel-stats {
  padding: 0 8px;
}

/* ═══════ 总览卡片 ═══════ */
.overview-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s, box-shadow 0.2s;
  cursor: default;
}
.overview-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.1);
}
.overview-icon {
  font-size: 32px;
  flex-shrink: 0;
}
.overview-value {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.3px;
}
.overview-label {
  font-size: 13px;
  color: #64748b;
  margin-top: 2px;
}
.overview-card-blue {
  background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 100%);
  color: #3730a3;
}
.overview-card-rose {
  background: linear-gradient(135deg, #ffe4e6 0%, #fecdd3 100%);
  color: #9f1239;
}
.overview-card-amber {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  color: #92400e;
}
.overview-card-violet {
  background: linear-gradient(135deg, #ede9fe 0%, #ddd6fe 100%);
  color: #5b21b6;
}

/* ═══════ 区块卡片 ═══════ */
.section-card {
  border-radius: 14px !important;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06) !important;
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #1e293b;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 6px;
}
.section-title-icon {
  font-size: 16px;
}

/* ═══════ 分类表格 ═══════ */
.cat-icon {
  font-size: 16px;
  margin-right: 6px;
}
.cat-name {
  color: #334155;
  font-weight: 500;
}
.amount-text {
  font-weight: 600;
  color: #e11d48;
}
.km-text {
  color: #6366f1;
  font-weight: 500;
}
.percent-bar-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}
.percent-bar {
  flex: 1;
  height: 8px;
  border-radius: 4px;
  background: #f1f5f9;
  transition: width 0.4s ease;
}
.percent-text {
  font-size: 12px;
  font-weight: 600;
  color: #475569;
  min-width: 36px;
  text-align: right;
}

/* ═══════ 排行表格 ═══════ */
.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
  background: #f1f5f9;
  color: #94a3b8;
}
.rank-1 { background: linear-gradient(135deg, #fbbf24, #f59e0b); color: #fff; box-shadow: 0 2px 6px rgba(245, 158, 11, 0.4); }
.rank-2 { background: linear-gradient(135deg, #cbd5e1, #94a3b8); color: #fff; box-shadow: 0 2px 6px rgba(148, 163, 184, 0.3); }
.rank-3 { background: linear-gradient(135deg, #fdba74, #fb923c); color: #fff; box-shadow: 0 2px 6px rgba(251, 146, 60, 0.4); }

/* ═══════ 按年统计 ═══════ */
.yearly-section {
  margin-top: 20px;
}
.yearly-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

/* 图表面板 */
.chart-panel {
  background: #fafbfc;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #f1f5f9;
}
.chart-panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
  margin-bottom: 12px;
}
.chart-box {
  height: 280px;
  position: relative;
}

/* 年度 KPI */
.year-kpi {
  text-align: center;
  padding: 20px 12px;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.06);
  transition: transform 0.2s;
}
.year-kpi:hover { transform: translateY(-2px); }
.year-kpi-blue { background: linear-gradient(135deg, #dbeafe, #bfdbfe); }
.year-kpi-rose { background: linear-gradient(135deg, #ffe4e6, #fecdd3); }
.year-kpi-amber { background: linear-gradient(135deg, #fef3c7, #fde68a); }
.year-kpi-violet { background: linear-gradient(135deg, #ede9fe, #ddd6fe); }
.year-kpi-icon {
  font-size: 28px;
  margin-bottom: 6px;
}
.year-kpi-value {
  font-size: 22px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.3px;
}
.year-kpi-label {
  font-size: 12px;
  color: #64748b;
  margin-top: 4px;
}

/* 年度表格 */
.yearly-table-wrap {
  margin-top: 20px;
}
.year-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 6px;
  background: #eff6ff;
  color: #2563eb;
  font-weight: 600;
  font-size: 13px;
}
.expense-text {
  font-weight: 700;
  color: #e11d48;
}
.sub-amount {
  color: #64748b;
  font-size: 13px;
}
.count-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 6px;
  background: #ecfdf5;
  color: #059669;
  font-weight: 600;
  font-size: 13px;
}
.date-range-text {
  color: #475569;
  font-size: 13px;
}
.budget-bar-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.budget-pct {
  font-size: 12px;
  font-weight: 600;
  color: #059669;
}
.budget-pct.over {
  color: #e11d48;
}
.no-budget {
  font-size: 12px;
  color: #94a3b8;
}

/* ═══════ 全局表格美化 ═══════ */
:deep(.stats-table) {
  border-radius: 8px;
}
:deep(.stats-table .ant-table-thead > tr > th) {
  background: #f8fafc;
  color: #475569;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
}
:deep(.stats-table .ant-table-tbody > tr > td) {
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
}
:deep(.stats-table .ant-table-tbody > tr:hover > td) {
  background: #fafbfc;
}
:deep(.yearly-summary-table .ant-table-thead > tr > th) {
  background: #f1f5f9;
  color: #475569;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
}
:deep(.yearly-summary-table .ant-table-tbody > tr > td) {
  border-bottom: 1px solid #f1f5f9;
}
:deep(.yearly-summary-table .ant-table-tbody > tr:hover > td) {
  background: #f8fafc;
}
</style>
