<template>
  <div>
    <!-- ── 年度总结 Banner ──────────────────────────────────── -->
    <div v-if="yearSummary" class="year-banner">
      <div class="year-banner-left">
        <div class="year-badge">{{ yearSummary.year }} 年度总结</div>
        <div class="year-headline">
          骑行 <em>{{ yearSummary.total_count }}</em> 次 &nbsp;·&nbsp;
          累计 <em>{{ yearSummary.total_km }}</em> km &nbsp;·&nbsp;
          <em>{{ yearSummary.total_hours }}</em> 小时
        </div>
        <div class="year-sub">
          爬升 {{ yearSummary.total_gain }}m &nbsp;·&nbsp;
          消耗 {{ yearSummary.total_calories }} kcal &nbsp;·&nbsp;
          场均 {{ yearSummary.avg_km_per_ride }} km
        </div>
        <!-- 月度里程热力条 -->
        <div class="year-heatbar">
          <span
            v-for="(v, i) in yearSummary.monthly_dist"
            :key="i"
            class="heatbar-cell"
            :class="heatClass(v, yearSummary.monthly_dist)"
            :title="`${i + 1}月：${v} km`"
          >{{ monthLabel(i) }}</span>
        </div>
      </div>
      <div class="year-banner-right">
        <div class="year-record-grid">
          <div v-if="yearSummary.best_dist" class="yr-item" @click="goActivity(yearSummary.best_dist.id)">
            <div class="yr-icon">🏅</div>
            <div class="yr-body">
              <div class="yr-label">最远骑行</div>
              <div class="yr-val">{{ yearSummary.best_dist.distance_km }} km</div>
              <div class="yr-date">{{ yearSummary.best_dist.date }}</div>
            </div>
          </div>
          <div v-if="yearSummary.best_speed" class="yr-item" @click="goActivity(yearSummary.best_speed.id)">
            <div class="yr-icon">⚡</div>
            <div class="yr-body">
              <div class="yr-label">最快均速</div>
              <div class="yr-val">{{ yearSummary.best_speed.avg_speed_kmh }} km/h</div>
              <div class="yr-date">{{ yearSummary.best_speed.date }}</div>
            </div>
          </div>
          <div v-if="yearSummary.best_gain" class="yr-item" @click="goActivity(yearSummary.best_gain.id)">
            <div class="yr-icon">⛰️</div>
            <div class="yr-body">
              <div class="yr-label">最大爬升</div>
              <div class="yr-val">{{ yearSummary.best_gain.elevation_gain }} m</div>
              <div class="yr-date">{{ yearSummary.best_gain.date }}</div>
            </div>
          </div>
          <div v-if="yearSummary.best_duration" class="yr-item" @click="goActivity(yearSummary.best_duration.id)">
            <div class="yr-icon">⏱️</div>
            <div class="yr-body">
              <div class="yr-label">最长骑行</div>
              <div class="yr-val">{{ fmtSec(yearSummary.best_duration.duration_sec) }}</div>
              <div class="yr-date">{{ yearSummary.best_duration.date }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <!-- 5 项 KPI 卡片 -->
    <div class="kpi-grid">
      <div v-for="k in kpiData" :key="k.label" class="kpi-card" :class="k.cls">
        <div class="kpi-label">{{ k.label }}</div>
        <div class="kpi-val">{{ k.value }}</div>
        <div class="kpi-unit">{{ k.unit }}</div>
        <div class="kpi-bg-icon">{{ k.icon }}</div>
      </div>
    </div>

    <!-- 图表区域 -->
    <div class="charts-grid">
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">📊 年度骑行里程（近10年）</div>
        <div class="chart-box"><canvas ref="yearlyDistChartRef"></canvas></div>
      </a-card>
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">📊 月度骑行次数</div>
        <div class="chart-box"><canvas ref="monthlyChartRef"></canvas></div>
      </a-card>
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">🛣️ 月度骑行里程（km）</div>
        <div class="chart-box"><canvas ref="monthlyDistChartRef"></canvas></div>
      </a-card>
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">⚡ 近15次骑行均速（km/h）</div>
        <div class="chart-box"><canvas ref="speedChartRef"></canvas></div>
      </a-card>
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">❤️ 近15次骑行均心率（bpm）</div>
        <div class="chart-box"><canvas ref="hrChartRef"></canvas></div>
      </a-card>
      <a-card :bordered="false" class="chart-card">
        <div class="chart-title">🚴 近15次骑行均踏频（rpm）</div>
        <div class="chart-box"><canvas ref="cadenceChartRef"></canvas></div>
      </a-card>
    </div>

    <!-- 个人最佳记录 -->
    <a-card :bordered="false" class="pr-card-wrap" style="margin-bottom: 24px">
      <div class="chart-title">🏆 个人最佳记录</div>
      <div class="pr-grid">
        <div v-for="pr in prRecords" :key="pr.label" class="pr-item">
          <div class="pr-label">{{ pr.label }}</div>
          <div class="pr-value">{{ pr.value }}</div>
          <div class="pr-date">{{ pr.date }}</div>
        </div>
      </div>
    </a-card>

    <!-- 汇总统计表格 -->
    <a-card :bordered="false">
      <div class="chart-title">📋 骑行汇总统计</div>
      <a-table
        :columns="summaryColumns"
        :data-source="summaryData"
        :pagination="false"
        size="small"
        bordered
      />
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { cyclingApi } from '@/api/index'
import { Chart, registerables } from 'chart.js'
import dayjs from 'dayjs'

Chart.register(...registerables)

const router = useRouter()

// ─── 年度总结 ───
const yearSummary = ref(null)

function heatClass(v, arr) {
  const max = Math.max(...arr)
  if (!v || !max) return 'heat-0'
  const ratio = v / max
  if (ratio > 0.75) return 'heat-4'
  if (ratio > 0.5) return 'heat-3'
  if (ratio > 0.25) return 'heat-2'
  return 'heat-1'
}

function monthLabel(i) {
  return ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'][i]
}

function fmtSec(sec) {
  if (!sec) return '—'
  const h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60)
  return h ? `${h}h${String(m).padStart(2, '0')}m` : `${m}min`
}

function goActivity(id) {
  router.push(`/sports/cycling/${id}`)
}

const yearlyDistChartRef = ref(null)
const monthlyChartRef = ref(null)
const monthlyDistChartRef = ref(null)
const speedChartRef = ref(null)
const hrChartRef = ref(null)
const cadenceChartRef = ref(null)

let charts = []
const activities = ref([])

// ─── KPI 数据 ───
const kpiData = ref([
  { cls: 'kpi-green', icon: '🎯', label: '骑行次数', value: '-', unit: '次' },
  { cls: 'kpi-blue', icon: '📏', label: '总里程', value: '-', unit: 'km' },
  { cls: 'kpi-yellow', icon: '⏱️', label: '总时长', value: '-', unit: '小时' },
  { cls: 'kpi-purple', icon: '🔥', label: '总消耗', value: '-', unit: 'kcal' },
  { cls: 'kpi-cyan', icon: '⛰️', label: '总爬升', value: '-', unit: 'm' },
])

// ─── 个人最佳记录 ───
const prRecords = ref([
  { label: '最快骑行速度', value: '—', date: '' },
  { label: '最长骑行距离', value: '—', date: '' },
  { label: '最长骑行时长', value: '—', date: '' },
  { label: '最大爬升', value: '—', date: '' },
  { label: '最高心率', value: '—', date: '' },
])

// ─── 汇总表格 ───
const summaryColumns = [
  { title: '统计项', dataIndex: 'key', width: 150 },
  { title: '数值', dataIndex: 'value', width: 150 },
]
const summaryData = ref([])

// ─── 工具函数 ───
function formatDur(sec) {
  if (!sec) return '—'
  const h = Math.floor(sec / 3600), m = Math.round((sec % 3600) / 60)
  return h ? `${h}h${String(m).padStart(2, '0')}m` : `${m}m`
}

function weekMonday(dateStr) {
  const [y, mo, d] = dateStr.split('-').map(Number)
  const dt = new Date(y, mo - 1, d)
  const day = dt.getDay()
  const diff = day === 0 ? -6 : 1 - day
  dt.setDate(dt.getDate() + diff)
  return dt.toISOString().slice(0, 10)
}

function getRecentWeeks(n) {
  const weeks = []
  const today = new Date()
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(today)
    d.setDate(d.getDate() - i * 7)
    const iso = d.toISOString().slice(0, 10)
    weeks.push(weekMonday(iso))
  }
  return [...new Set(weeks)]
}

function getDataMonths(acts) {
  // 根据实际数据动态计算月份范围
  if (!acts.length) return { labels: [], keys: [] }
  const allMonths = acts.map(a => a.date?.slice(0, 7)).filter(Boolean)
  const minMonth = allMonths.sort()[0]
  const maxMonth = new Date().toISOString().slice(0, 7)
  const labels = [], keys = []
  let [y, m] = minMonth.split('-').map(Number)
  const [ey, em] = maxMonth.split('-').map(Number)
  while (y < ey || (y === ey && m <= em)) {
    const key = `${y}-${String(m).padStart(2, '0')}`
    keys.push(key)
    labels.push(key.replace('-', '/'))
    m++
    if (m > 12) { m = 1; y++ }
  }
  return { labels, keys }
}

function getMonths(n) {
  const labels = [], keys = []
  for (let i = n - 1; i >= 0; i--) {
    const d = new Date(); d.setDate(1); d.setMonth(d.getMonth() - i)
    keys.push(d.toISOString().slice(0, 7))
    labels.push(d.toISOString().slice(0, 7).replace('-', '/'))
  }
  return { labels, keys }
}

function destroyCharts() {
  charts.forEach(c => c.destroy())
  charts = []
}

const chartDefaults = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } },
    tooltip: { enabled: true },
  },
  scales: {
    x: { grid: { display: false } },
    y: { grid: { color: '#f1f5f9' } }
  }
}

// ─── 渲染 ───
async function loadData() {
  try {
    // 年度总结
    const { data: ys } = await cyclingApi.getYearSummary()
    yearSummary.value = ys
    // 获取所有活动（不分页）
    const { data: statsData } = await cyclingApi.getStats()
    const { data: listData } = await cyclingApi.listActivities({ page: 1, limit: 9999 })
    activities.value = listData.items || []

    const acts = activities.value

    // 更新 KPI
    const totalDist = acts.reduce((s, a) => s + (a.distance_km || 0), 0)
    const totalDur = acts.reduce((s, a) => s + (a.duration_sec || 0), 0)
    const totalElev = acts.reduce((s, a) => s + (a.elevation_gain || 0), 0)
    // 卡路里：优先使用实际数据
    const totalCal = acts.reduce((s, a) => s + (a.calories || 0), 0) || Math.round(totalDist * 30)

    kpiData.value[0].value = acts.length
    kpiData.value[1].value = totalDist.toFixed(0)
    kpiData.value[2].value = (totalDur / 3600).toFixed(0)
    kpiData.value[3].value = totalCal.toFixed(0)
    kpiData.value[4].value = totalElev.toFixed(0)

    // 个人最佳
    if (acts.length) {
      // 最快速度（最大速度）
      const withMaxSpeed = acts.filter(a => a.max_speed_kmh)
      if (withMaxSpeed.length) {
        const fastest = withMaxSpeed.reduce((p, c) => (c.max_speed_kmh || 0) > (p.max_speed_kmh || 0) ? c : p)
        prRecords.value[0].value = (fastest.max_speed_kmh || 0).toFixed(1) + ' km/h'
        prRecords.value[0].date = fastest.date
      }
      // 最远距离
      const farthest = acts.reduce((p, c) => (c.distance_km || 0) > (p.distance_km || 0) ? c : p)
      prRecords.value[1].value = (farthest.distance_km || 0).toFixed(2) + ' km'
      prRecords.value[1].date = farthest.date
      // 最长时长
      const longest = acts.reduce((p, c) => (c.duration_sec || 0) > (p.duration_sec || 0) ? c : p)
      prRecords.value[2].value = formatDur(longest.duration_sec)
      prRecords.value[2].date = longest.date
      // 最大爬升
      const maxClimb = acts.reduce((p, c) => (c.elevation_gain || 0) > (p.elevation_gain || 0) ? c : p)
      if (maxClimb.elevation_gain) {
        prRecords.value[3].value = Math.round(maxClimb.elevation_gain) + ' m'
        prRecords.value[3].date = maxClimb.date
      }
      // 最高心率
      const maxHR = acts.filter(a => a.avg_heart_rate).reduce((p, c) => (c.avg_heart_rate || 0) > (p.avg_heart_rate || 0) ? c : p, { avg_heart_rate: 0 })
      if (maxHR.avg_heart_rate) {
        prRecords.value[4].value = maxHR.avg_heart_rate + ' bpm'
        prRecords.value[4].date = maxHR.date
      }
    }

    // 汇总表格
    const withSpeed = acts.filter(a => a.avg_speed_kmh)
    const avgSpeed = withSpeed.length
      ? (withSpeed.reduce((s, a) => s + (a.avg_speed_kmh || 0), 0) / withSpeed.length).toFixed(1) + ' km/h'
      : '—'
    const withCadence = acts.filter(a => a.avg_cadence)
    const avgCadence = withCadence.length
      ? Math.round(withCadence.reduce((s, a) => s + (a.avg_cadence || 0), 0) / withCadence.length) + ' rpm'
      : '—'
    summaryData.value = [
      { key: '骑行次数', value: acts.length + ' 次' },
      { key: '总里程', value: totalDist.toFixed(1) + ' km' },
      { key: '总时长', value: formatDur(totalDur) },
      { key: '平均每次里程', value: acts.length ? (totalDist / acts.length).toFixed(1) + ' km' : '—' },
      { key: '平均速度', value: avgSpeed },
      { key: '平均踏频', value: avgCadence },
      { key: '总爬升', value: totalElev.toFixed(0) + ' m' },
      { key: '总消耗', value: totalCal + ' kcal' },
    ]

    // 等待 DOM 渲染后画图表
    await nextTick()
    renderCharts(acts)
  } catch (e) {
    console.error('加载统计数据失败', e)
  }
}

function renderCharts(acts) {
  destroyCharts()

  // 年度骑行里程（近10年，按年汇总）
  if (yearlyDistChartRef.value) {
    const cy = new Date().getFullYear()
    const years = Array.from({ length: 10 }, (_, i) => cy - 9 + i)
    const labels = years.map(String)
    const dist = Array(10).fill(0)
    acts.forEach(a => {
      if (!a.date) return
      const y = a.date.slice(0, 4)
      const i = years.indexOf(Number(y))
      if (i >= 0) dist[i] += a.distance_km || 0
    })
    charts.push(new Chart(yearlyDistChartRef.value, {
      type: 'bar',
      data: { labels, datasets: [{ label: '骑行里程', data: dist.map(v => +v.toFixed(1)), backgroundColor: 'rgba(14,165,233,.7)', borderRadius: 4 }] },
      options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, beginAtZero: true } } }
    }))
  }

  // 近15次骑行均速（acts 已按 date desc 排序，取前15再反转为时间正序）
  if (speedChartRef.value) {
    const recent = acts.filter(a => a.avg_speed_kmh).slice(0, 15).reverse()
    if (recent.length) {
      charts.push(new Chart(speedChartRef.value, {
        type: 'line',
        data: {
          labels: recent.map(a => a.name?.slice(0, 8) || a.date?.slice(5) || ''),
          datasets: [{ label: '均速 (km/h)', data: recent.map(a => +a.avg_speed_kmh.toFixed(1)), borderColor: '#f97316', backgroundColor: 'rgba(249,115,22,.15)', fill: true, tension: .35, pointRadius: 4, pointHoverRadius: 6 }]
        },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, beginAtZero: false } } }
      }))
    }
  }

  // 近15次骑行均心率
  if (hrChartRef.value) {
    const recent = acts.filter(a => a.avg_heart_rate).slice(0, 15).reverse()
    if (recent.length) {
      charts.push(new Chart(hrChartRef.value, {
        type: 'line',
        data: {
          labels: recent.map(a => a.name?.slice(0, 8) || a.date?.slice(5) || ''),
          datasets: [{ label: '均心率 (bpm)', data: recent.map(a => a.avg_heart_rate), borderColor: '#f5222d', backgroundColor: 'rgba(245,34,45,.15)', fill: true, tension: .35, pointRadius: 4, pointHoverRadius: 6 }]
        },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, beginAtZero: false } } }
      }))
    }
  }

  // 近15次骑行均踏频
  if (cadenceChartRef.value) {
    const recent = acts.filter(a => a.avg_cadence).slice(0, 15).reverse()
    if (recent.length) {
      charts.push(new Chart(cadenceChartRef.value, {
        type: 'line',
        data: {
          labels: recent.map(a => a.name?.slice(0, 8) || a.date?.slice(5) || ''),
          datasets: [{ label: '均踏频 (rpm)', data: recent.map(a => a.avg_cadence), borderColor: '#722ed1', backgroundColor: 'rgba(114,46,209,.15)', fill: true, tension: .35, pointRadius: 4, pointHoverRadius: 6 }]
        },
        options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, beginAtZero: false } } }
      }))
    }
  }

  // 月度骑行次数（近12个月）
  if (monthlyChartRef.value) {
    const { labels, keys } = getMonths(12)
    const cnt = Array(12).fill(0)
    acts.forEach(a => { const i = keys.indexOf(a.date?.slice(0, 7)); if (i >= 0) cnt[i]++ })
    charts.push(new Chart(monthlyChartRef.value, {
      type: 'bar',
      data: { labels, datasets: [{ label: '骑行次数', data: cnt, backgroundColor: 'rgba(14,165,233,.7)', borderRadius: 4 }] },
      options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, beginAtZero: true, ticks: { stepSize: 1 } } } }
    }))
  }

  // 月度骑行里程（近12个月）
  if (monthlyDistChartRef.value) {
    const { labels, keys } = getMonths(12)
    const dist = Array(12).fill(0)
    acts.forEach(a => { const i = keys.indexOf(a.date?.slice(0, 7)); if (i >= 0) dist[i] += a.distance_km || 0 })
    charts.push(new Chart(monthlyDistChartRef.value, {
      type: 'line',
      data: { labels, datasets: [{ label: '骑行里程', data: dist.map(v => +v.toFixed(1)), borderColor: '#2d9a4e', backgroundColor: 'rgba(45,154,78,.15)', fill: true, tension: .35, pointRadius: 3, pointHoverRadius: 5 }] },
      options: { ...chartDefaults, scales: { ...chartDefaults.scales, y: { ...chartDefaults.scales.y, beginAtZero: true } } }
    }))
  }

}

onMounted(loadData)
onBeforeUnmount(destroyCharts)
</script>

<style scoped>
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
.kpi-green { background: linear-gradient(135deg, #059669, #10b981); }
.kpi-blue { background: linear-gradient(135deg, #0ea5e9, #38bdf8); }
.kpi-yellow { background: linear-gradient(135deg, #b45309, #d97706); }
.kpi-purple { background: linear-gradient(135deg, #8b5cf6, #a78bfa); }
.kpi-cyan { background: linear-gradient(135deg, #06b6d4, #22d3ee); }
.kpi-bg-icon { position: absolute; right: -8px; bottom: -8px; font-size: 56px; opacity: .15; line-height: 1; }
.kpi-label { font-size: 11.5px; font-weight: 600; opacity: .85; margin-bottom: 8px; }
.kpi-val { font-size: 30px; font-weight: 800; line-height: 1; }
.kpi-unit { font-size: 12px; opacity: .8; margin-top: 5px; }

.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 18px;
  margin-bottom: 24px;
}
.charts-grid .full-width { grid-column: 1 / -1; }
@media (max-width: 850px) { .charts-grid { grid-template-columns: 1fr; } }

.chart-card { border-radius: 16px !important; }
.chart-title {
  font-size: 14px;
  font-weight: 700;
  color: #0284c7;
  text-transform: uppercase;
  letter-spacing: .6px;
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

.pr-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}
.pr-item {
  padding: 16px;
  border-radius: 12px;
  border: 1.5px solid #bae6fd;
  background: linear-gradient(135deg, #f0f9ff, #fff);
  transition: transform .2s;
}
.pr-item:hover { transform: translateY(-2px); box-shadow: 0 4px 20px rgba(0,0,0,.08); }
.pr-label { font-size: 12px; color: #0284c7; font-weight: 600; margin-bottom: 6px; }
.pr-value { font-size: 24px; font-weight: 800; color: #0ea5e9; }
.pr-date { font-size: 11px; color: #999; margin-top: 4px; }

/* ── 年度总结 Banner ─────────────────────────────────────── */
.year-banner {
  display: flex;
  gap: 24px;
  background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0c4a6e 100%);
  border-radius: 18px;
  padding: 24px 28px;
  margin-bottom: 20px;
  color: #fff;
  box-shadow: 0 8px 30px rgba(14,165,233,.2);
  overflow: hidden;
  position: relative;
}
.year-banner::before {
  content: '🚴';
  position: absolute;
  right: -10px;
  top: -10px;
  font-size: 120px;
  opacity: 0.06;
  pointer-events: none;
}
.year-banner-left {
  flex: 1;
  min-width: 0;
}
.year-badge {
  display: inline-block;
  background: rgba(14,165,233,.3);
  border: 1px solid rgba(14,165,233,.5);
  color: #7dd3fc;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 12px;
  border-radius: 20px;
  margin-bottom: 10px;
  letter-spacing: .5px;
}
.year-headline {
  font-size: 20px;
  font-weight: 700;
  color: #f0f9ff;
  line-height: 1.4;
  margin-bottom: 6px;
}
.year-headline em {
  font-style: normal;
  color: #38bdf8;
  font-size: 24px;
}
.year-sub {
  font-size: 13px;
  color: #94a3b8;
  margin-bottom: 16px;
}
/* 月度热力条 */
.year-heatbar {
  display: flex;
  gap: 4px;
  align-items: flex-end;
}
.heatbar-cell {
  flex: 1;
  text-align: center;
  font-size: 10px;
  color: #64748b;
  border-radius: 4px;
  padding: 14px 0 4px;
  cursor: default;
  transition: opacity .2s;
}
.heatbar-cell:hover { opacity: .8; }
.heat-0 { background: rgba(255,255,255,.05); color: #475569; }
.heat-1 { background: rgba(14,165,233,.2); color: #7dd3fc; }
.heat-2 { background: rgba(14,165,233,.4); color: #bae6fd; }
.heat-3 { background: rgba(14,165,233,.65); color: #e0f2fe; }
.heat-4 { background: rgba(14,165,233,.9); color: #fff; }

/* 右侧记录区 */
.year-banner-right {
  display: flex;
  align-items: center;
}
.year-record-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  min-width: 320px;
}
.yr-item {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255,255,255,.06);
  border: 1px solid rgba(255,255,255,.08);
  border-radius: 12px;
  padding: 10px 14px;
  cursor: pointer;
  transition: background .2s;
}
.yr-item:hover { background: rgba(14,165,233,.2); }
.yr-icon { font-size: 22px; flex-shrink: 0; }
.yr-label { font-size: 11px; color: #94a3b8; margin-bottom: 2px; }
.yr-val { font-size: 16px; font-weight: 700; color: #f0f9ff; }
.yr-date { font-size: 11px; color: #64748b; margin-top: 2px; }
</style>
