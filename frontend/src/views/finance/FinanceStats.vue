<template>
  <div>
    <!-- ── 资产总览 Banner ────────────────────────────────── -->
    <div v-if="overview" class="asset-banner">
      <div class="asset-banner-left">
        <div class="asset-badge">💰 资产总览</div>
        <div class="asset-headline">
          净资产 <em>¥{{ fmtAmt(overview.net_assets) }}</em>
        </div>
        <div class="asset-sub">
          总资产 ¥{{ fmtAmt(overview.total_assets) }} &nbsp;·&nbsp;
          总负债 <span :style="{ color: overview.total_debt > 0 ? '#f87171' : '#86efac' }">¥{{ fmtAmt(overview.total_debt) }}</span>
        </div>
        <div class="asset-row">
          <div class="asset-kpi">
            <span class="ak-icon">📈</span>
            <div>
              <div class="ak-label">本月收入</div>
              <div class="ak-val income">+¥{{ fmtAmt(overview.month_income) }}</div>
            </div>
          </div>
          <div class="asset-kpi">
            <span class="ak-icon">📉</span>
            <div>
              <div class="ak-label">本月支出</div>
              <div class="ak-val expense">-¥{{ fmtAmt(overview.month_expense) }}</div>
            </div>
          </div>
          <div class="asset-kpi">
            <span class="ak-icon">🏦</span>
            <div>
              <div class="ak-label">账户数量</div>
              <div class="ak-val">{{ overview.account_count }}</div>
            </div>
          </div>
        </div>
      </div>
      <div class="asset-banner-right">
        <!-- 资产分布饼图 -->
        <div class="asset-pie-wrap" v-if="assetBreakdownData.length">
          <canvas ref="assetPieRef"></canvas>
        </div>
        <div v-else class="no-data">暂无资产数据</div>
      </div>
    </div>

    <!-- ── KPI 卡片 ──────────────────────────────────────── -->
    <div class="kpi-grid">
      <div v-for="k in kpiData" :key="k.label" class="kpi-card" :class="k.cls">
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-val">{{ k.value }}</div>
        <div class="kpi-unit">{{ k.unit }}</div>
        <div class="kpi-bg-icon">{{ k.icon }}</div>
      </div>
    </div>

    <!-- ── 图表区域 ──────────────────────────────────────── -->
    <div class="charts-grid">
      <!-- 月度收支趋势 -->
      <a-card :bordered="false" class="chart-card" style="grid-column: 1 / -1">
        <div class="chart-title">📊 月度收支趋势</div>
        <div class="chart-box"><canvas ref="monthlyTrendChartRef"></canvas></div>
      </a-card>

      <!-- 支出分类饼图 -->
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">🛒 支出分类（近12个月）</div>
        <div class="chart-box"><canvas ref="expensePieChartRef"></canvas></div>
      </a-card>

      <!-- 收入分类饼图 -->
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">💰 收入分类（近12个月）</div>
        <div class="chart-box"><canvas ref="incomePieChartRef"></canvas></div>
      </a-card>
    </div>

    <!-- ── 年度对比表格 ──────────────────────────────────── -->
    <a-card :bordered="false" style="margin-top: 24px">
      <div class="chart-title">📋 年度收支汇总</div>
      <a-select v-model:value="selectedYear" size="small" style="width: 120px; margin-bottom: 16px" @change="loadMonthlyData">
        <a-select-option v-for="y in yearOptions" :key="y" :value="y">{{ y }} 年</a-select-option>
      </a-select>
      <a-table
        :columns="yearColumns"
        :data-source="yearTableData"
        :pagination="false"
        size="small"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'income'">
            <span style="color: #16a34a; font-weight: 600">+¥{{ fmtAmt(record.income) }}</span>
          </template>
          <template v-if="column.key === 'expense'">
            <span style="color: #dc2626; font-weight: 600">-¥{{ fmtAmt(record.expense) }}</span>
          </template>
          <template v-if="column.key === 'balance'">
            <span :style="{ color: record.balance >= 0 ? '#16a34a' : '#dc2626', fontWeight: 700 }">
              {{ record.balance >= 0 ? '+' : '' }}¥{{ fmtAmt(record.balance) }}
            </span>
          </template>
          <template v-if="column.key === 'expense_change'">
            <span v-if="record.expense_change_pct !== 0"
              :style="{ color: record.expense_change_pct > 0 ? '#dc2626' : '#16a34a', fontWeight: 600 }">
              {{ record.expense_change_pct > 0 ? '↑' : '↓' }} {{ Math.abs(record.expense_change_pct) }}%
            </span>
            <span v-else style="color: #94a3b8">—</span>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- ── 平台统计 & TOP商户 ───────────────────────────── -->
    <div class="charts-grid" style="margin-top: 24px">
      <!-- 按平台统计 -->
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">📱 支付平台分布（近12个月）</div>
        <div class="chart-box"><canvas ref="platformPieRef"></canvas></div>
      </a-card>

      <!-- TOP商户 -->
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">🏪 TOP 10 支出商户（近12个月）</div>
        <div class="chart-box"><canvas ref="topMerchantRef"></canvas></div>
      </a-card>
    </div>

    <!-- 转账类汇总 -->
    <a-card v-if="transferStats" :bordered="false" style="margin-top: 18px">
      <div class="chart-title">🔄 转账类汇总（不计入收支统计）</div>
      <a-row :gutter="16" style="text-align: center">
        <a-col :span="8">
          <a-statistic title="转账笔数" :value="transferStats.count" />
        </a-col>
        <a-col :span="8">
          <a-statistic title="转账金额" :value="transferStats.total_amount" :precision="2" prefix="¥"
            :value-style="{ color: '#94a3b8' }" />
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { financeApi } from '@/api/index'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

// ─── 状态 ──────────────────────────────────────────────
const overview = ref(null)
const kpiData = ref([
  { cls: 'kpi-green', icon: '📈', label: '本月收入', value: '-', unit: '元' },
  { cls: 'kpi-blue', icon: '📉', label: '本月支出', value: '-', unit: '元' },
  { cls: 'kpi-purple', icon: '🏦', label: '净资产', value: '-', unit: '元' },
  { cls: 'kpi-red', icon: '💸', label: '累计支出', value: '-', unit: '元' },
  { cls: 'kpi-yellow', icon: '📊', label: '累计收入', value: '-', unit: '元' },
])

// 年份选项
const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 5 }, (_, i) => currentYear - i)
const selectedYear = ref(currentYear)

// 年度表格
const yearColumns = [
  { title: '月份', dataIndex: 'month', key: 'month', width: 100 },
  { title: '收入', key: 'income', width: 150 },
  { title: '支出', key: 'expense', width: 150 },
  { title: '结余', key: 'balance', width: 150 },
  { title: '支出环比', key: 'expense_change', width: 100, align: 'center' },
]
const yearTableData = ref([])

// ─── 图表 Ref ──────────────────────────────────────────
const monthlyTrendChartRef = ref(null)
const expensePieChartRef = ref(null)
const incomePieChartRef = ref(null)
const assetPieRef = ref(null)
const platformPieRef = ref(null)
const topMerchantRef = ref(null)
let charts = []

// ─── 资产分布饼图数据 ──────────────────────────────────
const assetBreakdownData = ref([])
const transferStats = ref(null)
const platformData = ref([])
const topMerchantData = ref([])

// ─── 工具函数 ──────────────────────────────────────────
function fmtAmt(v) {
  if (!v && v !== 0) return '—'
  return Math.abs(v) >= 10000
    ? Math.abs(v).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
    : Math.abs(v).toFixed(2)
}

function destroyCharts() {
  charts.forEach(c => c.destroy())
  charts = []
}

// ─── 数据加载 ──────────────────────────────────────────
async function loadData() {
  try {
    const [overviewRes, monthlyRes, expCatRes, incCatRes, platformRes, merchantRes, transferRes] = await Promise.all([
      financeApi.getStats(),
      financeApi.getMonthlyStats(selectedYear.value),
      financeApi.getCategoryStats({ type: 'expense', start_date: getRolling12Start(), end_date: getToday() }),
      financeApi.getCategoryStats({ type: 'income', start_date: getRolling12Start(), end_date: getToday() }),
      financeApi.getPlatformStats({ start_date: getRolling12Start(), end_date: getToday() }),
      financeApi.getTopMerchants({ start_date: getRolling12Start(), end_date: getToday(), limit: 10 }),
      financeApi.getTransferStats({ start_date: getRolling12Start(), end_date: getToday() }),
    ])

    overview.value = overviewRes.data
    const monthly = monthlyRes.data || []
    const expCats = expCatRes.data || []
    const incCats = incCatRes.data || []
    platformData.value = platformRes.data || []
    topMerchantData.value = merchantRes.data || []
    transferStats.value = transferRes.data || null

    // 资产分布
    if (overviewRes.data?.asset_breakdown) {
      assetBreakdownData.value = Object.entries(overviewRes.data.asset_breakdown)
        .filter(([, v]) => v > 0)
        .map(([k, v]) => ({ label: k, value: v }))
    }

    // KPI
    const ov = overviewRes.data
    kpiData.value[0].value = ov.month_income ? '¥' + (ov.month_income >= 10000 ? (ov.month_income / 10000).toFixed(1) + 'w' : ov.month_income.toFixed(0)) : '¥0'
    kpiData.value[1].value = ov.month_expense ? '¥' + (ov.month_expense >= 10000 ? (ov.month_expense / 10000).toFixed(1) + 'w' : ov.month_expense.toFixed(0)) : '¥0'
    kpiData.value[2].value = '¥' + (ov.net_assets >= 10000 ? (ov.net_assets / 10000).toFixed(1) + 'w' : ov.net_assets.toFixed(0))

    // 累计收支
    const totalIncome = monthly.reduce((s, m) => s + (m.income || 0), 0)
    const totalExpense = monthly.reduce((s, m) => s + (m.expense || 0), 0)
    kpiData.value[3].value = '¥' + (totalExpense >= 10000 ? (totalExpense / 10000).toFixed(1) + 'w' : totalExpense.toFixed(0))
    kpiData.value[4].value = '¥' + (totalIncome >= 10000 ? (totalIncome / 10000).toFixed(1) + 'w' : totalIncome.toFixed(0))

    // 年度表格（含环比）
    const monthlyWithCompare = monthly.map((m, i) => {
      const prev = i > 0 ? monthly[i - 1] : null
      const expenseChange = prev ? m.expense - (prev.expense || 0) : 0
      const expenseChangePct = prev && prev.expense ? Math.round(expenseChange / prev.expense * 100) : 0
      return {
        month: m.month,
        income: m.income || 0,
        expense: m.expense || 0,
        balance: (m.income || 0) - (m.expense || 0),
        expense_change: expenseChange,
        expense_change_pct: expenseChangePct,
      }
    })
    yearTableData.value = monthlyWithCompare

    await nextTick()
    renderCharts(monthly, expCats, incCats)
  } catch (e) {
    console.error('加载财务统计失败', e)
  }
}

function getYearStart() {
  return `${selectedYear.value}-01-01`
}
function getYearEnd() {
  return `${selectedYear.value}-12-31`
}
// 滚动12个月（近12个月）日期范围
function getRolling12Start() {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().slice(0, 10)
}
function getToday() {
  return new Date().toISOString().slice(0, 10)
}

async function loadMonthlyData() {
  try {
    const res = await financeApi.getMonthlyStats(selectedYear.value)
    const monthly = res.data || []
    yearTableData.value = monthly.map(m => ({
      month: m.month,
      income: m.income || 0,
      expense: m.expense || 0,
      balance: (m.income || 0) - (m.expense || 0),
    }))
    // 重新渲染趋势图
    const expRes = await financeApi.getCategoryStats({ type: 'expense', start_date: getYearStart(), end_date: getYearEnd() })
    const incRes = await financeApi.getCategoryStats({ type: 'income', start_date: getYearStart(), end_date: getYearEnd() })
    await nextTick()
    renderCharts(monthly, expRes.data || [], incRes.data || [])
  } catch (e) {
    console.error('加载月度数据失败', e)
  }
}

// ─── 渲染图表 ──────────────────────────────────────────
function renderCharts(monthly, expCats, incCats) {
  destroyCharts()

  // 1. 月度收支趋势（柱状+折线）
  if (monthlyTrendChartRef.value) {
    const labels = monthly.map(m => m.month.slice(5) + '月')
    charts.push(new Chart(monthlyTrendChartRef.value, {
      type: 'bar',
      data: {
        labels,
        datasets: [
          {
            label: '收入',
            data: monthly.map(m => m.income || 0),
            backgroundColor: 'rgba(34,197,94,.7)',
            borderColor: '#16a34a',
            borderWidth: 1,
          },
          {
            label: '支出',
            data: monthly.map(m => m.expense || 0),
            backgroundColor: 'rgba(239,68,68,.7)',
            borderColor: '#dc2626',
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
          y: { beginAtZero: true, ticks: { callback: v => '¥' + (v >= 10000 ? (v / 10000).toFixed(0) + 'w' : v) }, grid: { color: '#f1f5f9' } },
        },
      },
    }))
  }

  // 2. 支出分类饼图
  if (expensePieChartRef.value && expCats.length) {
    const colors = ['#ef4444', '#f97316', '#f59e0b', '#eab308', '#84cc16', '#22c55e', '#14b8a6', '#06b6d4', '#0ea5e9', '#6366f1', '#8b5cf6', '#ec4899']
    charts.push(new Chart(expensePieChartRef.value, {
      type: 'doughnut',
      data: {
        labels: expCats.map(c => c.category),
        datasets: [{
          data: expCats.map(c => c.amount),
          backgroundColor: expCats.map((_, i) => colors[i % colors.length]),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, padding: 8, font: { size: 11 } } },
          tooltip: { callbacks: { label: ctx => ctx.label + ': ¥' + ctx.parsed.toLocaleString() } },
        },
      },
    }))
  }

  // 3. 收入分类饼图
  if (incomePieChartRef.value && incCats.length) {
    const colors = ['#22c55e', '#10b981', '#059669', '#14b8a6', '#06b6d4', '#0ea5e9', '#6366f1']
    charts.push(new Chart(incomePieChartRef.value, {
      type: 'doughnut',
      data: {
        labels: incCats.map(c => c.category),
        datasets: [{
          data: incCats.map(c => c.amount),
          backgroundColor: incCats.map((_, i) => colors[i % colors.length]),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, padding: 8, font: { size: 11 } } },
          tooltip: { callbacks: { label: ctx => ctx.label + ': ¥' + ctx.parsed.toLocaleString() } },
        },
      },
    }))
  }

  // 4. 资产分布饼图
  if (assetPieRef.value && assetBreakdownData.value.length) {
    const colors = ['#22c55e', '#0ea5e9', '#f59e0b', '#8b5cf6', '#ef4444', '#64748b', '#ec4899']
    const typeMap = { cash: '现金', debt: '负债', fund: '基金', stock: '股票', bond: '债券', bank: '银行卡', other: '其他' }
    charts.push(new Chart(assetPieRef.value, {
      type: 'doughnut',
      data: {
        labels: assetBreakdownData.value.map(d => typeMap[d.label] || d.label),
        datasets: [{
          data: assetBreakdownData.value.map(d => d.value),
          backgroundColor: assetBreakdownData.value.map((_, i) => colors[i % colors.length]),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'bottom', labels: { boxWidth: 12, padding: 8, font: { size: 11 }, color: '#e2e8f0' } },
          tooltip: { callbacks: { label: ctx => ctx.label + ': ¥' + ctx.parsed.toLocaleString() } },
        },
      },
    }))
  }

  // 5. 平台分布饼图
  if (platformPieRef.value && platformData.value.length) {
    const colors = ['#1677ff', '#22c55e', '#f59e0b', '#8b5cf6']
    charts.push(new Chart(platformPieRef.value, {
      type: 'doughnut',
      data: {
        labels: platformData.value.map(p => p.platform_label),
        datasets: [{
          data: platformData.value.map(p => p.count),
          backgroundColor: platformData.value.map((_, i) => colors[i % colors.length]),
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { position: 'right', labels: { boxWidth: 12, padding: 10, font: { size: 12 } } },
          tooltip: { callbacks: { label: ctx => ctx.label + ': ' + ctx.parsed + ' 笔' } },
        },
      },
    }))
  }

  // 6. TOP 商户水平柱状图
  if (topMerchantRef.value && topMerchantData.value.length) {
    const top10 = topMerchantData.value.slice(0, 10).reverse()
    charts.push(new Chart(topMerchantRef.value, {
      type: 'bar',
      data: {
        labels: top10.map(m => m.counterparty),
        datasets: [{
          label: '支出金额',
          data: top10.map(m => m.amount),
          backgroundColor: 'rgba(239,68,68,.7)',
          borderColor: '#dc2626',
          borderWidth: 1,
          borderRadius: 4,
        }],
      },
      options: {
        indexAxis: 'y',
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: { callbacks: { label: ctx => '¥' + ctx.parsed.x.toLocaleString() } },
        },
        scales: {
          x: { beginAtZero: true, ticks: { callback: v => '¥' + (v >= 10000 ? (v / 10000).toFixed(0) + 'w' : v) }, grid: { color: '#f1f5f9' } },
          y: { grid: { display: false }, ticks: { font: { size: 11 } } },
        },
      },
    }))
  }
}

onMounted(loadData)
onBeforeUnmount(destroyCharts)
</script>

<style scoped>
/* ── Banner ──────────────────────────────────────── */
.asset-banner {
  display: flex;
  gap: 24px;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
  border-radius: 18px;
  padding: 24px 28px;
  margin-bottom: 20px;
  color: #fff;
  box-shadow: 0 8px 30px rgba(0,0,0,.2);
}
.asset-banner-left { flex: 1; min-width: 0; }
.asset-badge {
  display: inline-block;
  background: rgba(234,179,8,.2);
  border: 1px solid rgba(234,179,8,.4);
  color: #fbbf24;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: 20px;
  margin-bottom: 10px;
}
.asset-headline { font-size: 26px; font-weight: 800; color: #f0f9ff; margin-bottom: 6px; }
.asset-headline em { font-style: normal; color: #34d399; }
.asset-sub { font-size: 13px; color: #94a3b8; margin-bottom: 16px; }
.asset-row { display: flex; gap: 16px; flex-wrap: wrap; }
.asset-kpi {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 12px;
  padding: 10px 14px;
}
.ak-icon { font-size: 18px; }
.ak-label { font-size: 11px; color: #94a3b8; margin-bottom: 2px; }
.ak-val { font-size: 16px; font-weight: 700; }
.ak-val.income { color: #4ade80; }
.ak-val.expense { color: #f87171; }
.asset-banner-right { display: flex; align-items: center; justify-content: center; min-width: 220px; }
.asset-pie-wrap { width: 200px; height: 200px; position: relative; }
.no-data { color: #64748b; font-size: 13px; }

/* ── KPI ──────────────────────────────────────────── */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
  margin-bottom: 24px;
}
@media (max-width: 1200px) { .kpi-grid { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 700px) { .kpi-grid { grid-template-columns: repeat(2, 1fr); } }

.kpi-card {
  border-radius: 16px;
  padding: 18px 16px 14px;
  position: relative;
  overflow: hidden;
  color: #fff;
  box-shadow: 0 4px 20px rgba(0,0,0,.1);
  transition: transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform: translateY(-3px); box-shadow: 0 12px 40px rgba(0,0,0,.15); }
.kpi-green { background: linear-gradient(135deg, #16a34a, #22c55e); }
.kpi-blue { background: linear-gradient(135deg, #dc2626, #ef4444); }
.kpi-red { background: linear-gradient(135deg, #b45309, #d97706); }
.kpi-purple { background: linear-gradient(135deg, #7c3aed, #8b5cf6); }
.kpi-yellow { background: linear-gradient(135deg, #0ea5e9, #38bdf8); }
.kpi-bg-icon { position: absolute; right: -8px; bottom: -8px; font-size: 56px; opacity: .15; line-height: 1; }
.kpi-label { font-size: 11.5px; font-weight: 600; opacity: .85; margin-bottom: 8px; }
.kpi-val { font-size: 22px; font-weight: 800; line-height: 1; text-shadow: 0 1px 4px rgba(0,0,0,.35); }
.kpi-unit { font-size: 12px; opacity: .8; margin-top: 5px; }

/* ── Charts ───────────────────────────────────────── */
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 24px;
}
@media (max-width: 850px) { .charts-grid { grid-template-columns: 1fr; } }

.chart-card { border-radius: 16px !important; }
.chart-title {
  font-size: 14px;
  font-weight: 700;
  color: #0284c7;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.chart-title::before {
  content: '';
  display: inline-block;
  width: 4px;
  height: 16px;
  border-radius: 99px;
  background: linear-gradient(180deg, #0ea5e9, #0284c7);
}
.chart-box { height: 280px; position: relative; }
</style>
