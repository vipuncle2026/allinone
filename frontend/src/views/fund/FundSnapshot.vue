<template>
  <div class="snapshot-page">
    <!-- 顶部操作栏 + 指标卡片 -->
    <a-card title="📈 持仓快照" size="small" :body-style="{ padding: '12px 16px' }" style="margin-bottom: 14px">
      <template #extra>
        <a-space>
          <a-radio-group v-model:value="days" size="small" button-style="solid" @change="loadSnapshots">
            <a-radio-button :value="7">7天</a-radio-button>
            <a-radio-button :value="30">30天</a-radio-button>
            <a-radio-button :value="90">90天</a-radio-button>
            <a-radio-button :value="0">全部</a-radio-button>
          </a-radio-group>
          <a-button type="primary" size="small" :loading="taking" @click="handleTakeSnapshot">
            📷 立即快照
          </a-button>
        </a-space>
      </template>

      <!-- 指标卡片（取最新快照） -->
      <div v-if="latestSnap" class="summary-cards">
        <div class="sc-item sc-market">
          <span class="sc-label">最新总市值</span>
          <span class="sc-val">¥{{ fmtMoney(latestSnap.total_market) }}</span>
          <span class="sc-sub">{{ latestSnap.date }}</span>
        </div>
        <div class="sc-item sc-gain">
          <span class="sc-label">累计收益</span>
          <span class="sc-val" :style="{ color: latestSnap.total_gain >= 0 ? '#e63946' : '#16a34a' }">
            {{ latestSnap.total_gain >= 0 ? '+' : '' }}¥{{ fmtMoney(latestSnap.total_gain) }}
          </span>
        </div>
        <div class="sc-item sc-rate">
          <span class="sc-label">总收益率</span>
          <span class="sc-val" :style="{ color: latestSnap.total_rate >= 0 ? '#e63946' : '#16a34a' }">
            {{ latestSnap.total_rate >= 0 ? '+' : '' }}{{ latestSnap.total_rate.toFixed(2) }}%
          </span>
        </div>
        <div class="sc-item sc-today">
          <span class="sc-label">当日收益</span>
          <span class="sc-val" :style="{ color: latestSnap.today_profit >= 0 ? '#e63946' : '#16a34a' }">
            {{ latestSnap.today_profit >= 0 ? '+' : '' }}¥{{ fmtMoney(latestSnap.today_profit) }}
          </span>
        </div>
        <div class="sc-item sc-count">
          <span class="sc-label">快照条数</span>
          <span class="sc-val">{{ snapshots.length }}</span>
          <span class="sc-sub">条历史记录</span>
        </div>
      </div>
      <div v-else style="text-align:center; padding: 20px; color: #bbb">
        暂无快照数据，点击「立即快照」记录当前持仓
      </div>
    </a-card>

    <!-- 折线图 -->
    <a-card v-if="snapshots.length >= 2" title="市值历史曲线" size="small" :body-style="{ padding: '16px' }" style="margin-bottom: 14px">
      <div class="chart-container">
        <svg :width="chartWidth" :height="chartHeight" class="line-chart">
          <!-- 背景网格 -->
          <g class="grid">
            <line v-for="y in gridYLines" :key="'gy-'+y"
              :x1="PAD.left" :y1="y" :x2="chartWidth - PAD.right" :y2="y"
              stroke="#f0f0f0" stroke-width="1" />
            <line v-for="(x, i) in gridXLines" :key="'gx-'+i"
              :x1="x" :y1="PAD.top" :x2="x" :y2="chartHeight - PAD.bottom"
              stroke="#f0f0f0" stroke-width="1" />
          </g>

          <!-- 左Y轴：市值 -->
          <g class="y-axis-left">
            <line :x1="PAD.left" :y1="PAD.top" :x1-end="PAD.left" :x2="PAD.left" :y2="chartHeight - PAD.bottom"
              stroke="#d1d5db" stroke-width="1" />
            <text v-for="(label, i) in yLeftLabels" :key="'yl-'+i"
              :x="PAD.left - 6" :y="yLeftPositions[i] + 4"
              text-anchor="end" font-size="10" fill="#9ca3af">{{ label }}</text>
          </g>

          <!-- 右Y轴：收益率 -->
          <g class="y-axis-right">
            <line :x1="chartWidth - PAD.right" :y1="PAD.top" :x2="chartWidth - PAD.right" :y2="chartHeight - PAD.bottom"
              stroke="#d1d5db" stroke-width="1" />
            <text v-for="(label, i) in yRightLabels" :key="'yr-'+i"
              :x="chartWidth - PAD.right + 6" :y="yRightPositions[i] + 4"
              text-anchor="start" font-size="10" fill="#a855f7">{{ label }}</text>
          </g>

          <!-- X轴 -->
          <g class="x-axis">
            <line :x1="PAD.left" :y1="chartHeight - PAD.bottom" :x2="chartWidth - PAD.right" :y2="chartHeight - PAD.bottom"
              stroke="#d1d5db" stroke-width="1" />
            <text v-for="(label, i) in xLabels" :key="'xl-'+i"
              :x="xPositions[i]" :y="chartHeight - PAD.bottom + 14"
              text-anchor="middle" font-size="10" fill="#9ca3af">{{ label }}</text>
          </g>

          <!-- 市值填充区域 -->
          <path v-if="marketAreaPath" :d="marketAreaPath"
            fill="url(#marketGradient)" opacity="0.3" />

          <!-- 市值折线 -->
          <polyline v-if="marketLinePath" :points="marketLinePath"
            fill="none" stroke="#6366f1" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />

          <!-- 收益率折线（虚线） -->
          <polyline v-if="rateLinePath" :points="rateLinePath"
            fill="none" stroke="#a855f7" stroke-width="1.5" stroke-dasharray="4,3"
            stroke-linecap="round" stroke-linejoin="round" />

          <!-- 渐变定义 -->
          <defs>
            <linearGradient id="marketGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#6366f1" stop-opacity="0.6" />
              <stop offset="100%" stop-color="#6366f1" stop-opacity="0.02" />
            </linearGradient>
          </defs>

          <!-- 数据点 -->
          <circle v-for="(pt, i) in marketPoints" :key="'mp-'+i"
            :cx="pt.x" :cy="pt.y" r="3" fill="#6366f1" stroke="white" stroke-width="1.5">
            <title>{{ snapshots[i].date }} ¥{{ fmtMoney(snapshots[i].total_market) }}</title>
          </circle>

          <!-- 图例 -->
          <g transform="translate(60, 14)">
            <rect x="0" y="-7" width="16" height="3" fill="#6366f1" rx="1.5" />
            <text x="20" y="0" font-size="11" fill="#6366f1">总市值（左轴）</text>
            <line x1="140" y1="-5" x2="156" y2="-5" stroke="#a855f7" stroke-width="1.5" stroke-dasharray="4,3" />
            <text x="160" y="0" font-size="11" fill="#a855f7">收益率%（右轴）</text>
          </g>
        </svg>
      </div>
    </a-card>

    <!-- 历史记录表格 -->
    <a-card title="历史快照记录" size="small" :body-style="{ padding: '12px 16px' }">
      <a-table
        :data-source="snapshots"
        :columns="columns"
        :pagination="{ pageSize: 20, showTotal: total => `共 ${total} 条` }"
        size="small"
        row-key="date"
        :loading="loading"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'total_market'">
            <span style="font-weight: 600">¥{{ fmtMoney(record.total_market) }}</span>
          </template>
          <template v-if="column.key === 'total_gain'">
            <span :style="{ color: record.total_gain >= 0 ? '#e63946' : '#16a34a', fontWeight: 600 }">
              {{ record.total_gain >= 0 ? '+' : '' }}¥{{ fmtMoney(record.total_gain) }}
            </span>
          </template>
          <template v-if="column.key === 'total_rate'">
            <span :style="{ color: record.total_rate >= 0 ? '#e63946' : '#16a34a' }">
              {{ record.total_rate >= 0 ? '+' : '' }}{{ record.total_rate.toFixed(2) }}%
            </span>
          </template>
          <template v-if="column.key === 'today_profit'">
            <span :style="{ color: record.today_profit >= 0 ? '#e63946' : '#16a34a' }">
              {{ record.today_profit >= 0 ? '+' : '' }}¥{{ fmtMoney(record.today_profit) }}
            </span>
          </template>
          <template v-if="column.key === 'action'">
            <a-popconfirm title="删除此条快照？" @confirm="deleteSnap(record.date)" ok-text="删除" cancel-text="取消">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { fundApi } from '@/api'

const snapshots = ref([])
const loading = ref(false)
const taking = ref(false)
const days = ref(30)

// 图表尺寸
const chartWidth = ref(900)
const chartHeight = 260
const PAD = { top: 24, bottom: 28, left: 72, right: 64 }

const latestSnap = computed(() => snapshots.value[0] || null)

function fmtMoney(val) {
  if (val === undefined || val === null) return '0.00'
  return val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadSnapshots() {
  loading.value = true
  try {
    const res = await fundApi.snapshotList(days.value)
    // 按日期升序排列（图表需要）
    snapshots.value = [...(res.data.snapshots || [])].sort((a, b) => a.date.localeCompare(b.date))
  } catch {
    message.error('加载快照失败')
  } finally {
    loading.value = false
  }
}

async function handleTakeSnapshot() {
  taking.value = true
  try {
    const res = await fundApi.takeSnapshot()
    message.success(res.data.message || '快照已保存')
    await loadSnapshots()
  } catch (e) {
    message.error('快照失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    taking.value = false
  }
}

async function deleteSnap(date) {
  try {
    await fundApi.deleteSnapshot(date)
    message.success(`已删除 ${date} 快照`)
    await loadSnapshots()
  } catch {
    message.error('删除失败')
  }
}

// ────── 折线图计算 ──────
const marketPoints = computed(() => {
  if (snapshots.value.length < 2) return []
  const data = snapshots.value
  const markets = data.map(s => s.total_market)
  const minM = Math.min(...markets)
  const maxM = Math.max(...markets)
  const rangeM = maxM - minM || 1
  const w = chartWidth.value - PAD.left - PAD.right
  const h = chartHeight - PAD.top - PAD.bottom
  return data.map((s, i) => ({
    x: PAD.left + (i / (data.length - 1)) * w,
    y: PAD.top + (1 - (s.total_market - minM) / rangeM) * h,
  }))
})

const marketLinePath = computed(() => {
  return marketPoints.value.map((p, i) => `${i === 0 ? '' : ''}${p.x},${p.y}`).join(' ')
})

const marketAreaPath = computed(() => {
  if (marketPoints.value.length < 2) return ''
  const pts = marketPoints.value
  const bottom = chartHeight - PAD.bottom
  const first = pts[0], last = pts[pts.length - 1]
  return `M${first.x},${bottom} L${pts.map(p => `${p.x},${p.y}`).join(' L')} L${last.x},${bottom} Z`
})

const ratePoints = computed(() => {
  if (snapshots.value.length < 2) return []
  const data = snapshots.value
  const rates = data.map(s => s.total_rate)
  const minR = Math.min(...rates)
  const maxR = Math.max(...rates)
  const rangeR = maxR - minR || 1
  const w = chartWidth.value - PAD.left - PAD.right
  const h = chartHeight - PAD.top - PAD.bottom
  return data.map((s, i) => ({
    x: PAD.left + (i / (data.length - 1)) * w,
    y: PAD.top + (1 - (s.total_rate - minR) / rangeR) * h,
  }))
})

const rateLinePath = computed(() => {
  return ratePoints.value.map(p => `${p.x},${p.y}`).join(' ')
})

// X轴标签（最多显示6个）
const xPositions = computed(() => {
  if (!snapshots.value.length) return []
  const n = snapshots.value.length
  const w = chartWidth.value - PAD.left - PAD.right
  if (n <= 6) return snapshots.value.map((_, i) => PAD.left + (i / Math.max(n - 1, 1)) * w)
  const step = Math.ceil(n / 6)
  return snapshots.value
    .map((_, i) => i)
    .filter(i => i % step === 0 || i === n - 1)
    .map(i => PAD.left + (i / (n - 1)) * w)
})

const xLabels = computed(() => {
  if (!snapshots.value.length) return []
  const n = snapshots.value.length
  if (n <= 6) return snapshots.value.map(s => s.date.slice(5))
  const step = Math.ceil(n / 6)
  return snapshots.value
    .map((s, i) => ({ date: s.date, i }))
    .filter(({ i }) => i % step === 0 || i === n - 1)
    .map(({ date }) => date.slice(5))
})

// Y轴左侧（市值）
const yLeftLabels = computed(() => {
  if (!snapshots.value.length) return []
  const markets = snapshots.value.map(s => s.total_market)
  const minM = Math.min(...markets), maxM = Math.max(...markets)
  const ticks = 4
  return Array.from({ length: ticks + 1 }, (_, i) => {
    const v = minM + (maxM - minM) * (i / ticks)
    return v >= 10000 ? (v / 10000).toFixed(1) + 'w' : v.toFixed(0)
  }).reverse()
})

const yLeftPositions = computed(() => {
  const h = chartHeight - PAD.top - PAD.bottom
  const ticks = 4
  return Array.from({ length: ticks + 1 }, (_, i) => PAD.top + (i / ticks) * h)
})

// Y轴右侧（收益率）
const yRightLabels = computed(() => {
  if (!snapshots.value.length) return []
  const rates = snapshots.value.map(s => s.total_rate)
  const minR = Math.min(...rates), maxR = Math.max(...rates)
  const ticks = 4
  return Array.from({ length: ticks + 1 }, (_, i) => {
    const v = minR + (maxR - minR) * (i / ticks)
    return (v >= 0 ? '+' : '') + v.toFixed(1) + '%'
  }).reverse()
})

const yRightPositions = computed(() => yLeftPositions.value)

// 网格线
const gridYLines = computed(() => yLeftPositions.value)
const gridXLines = computed(() => xPositions.value)

const columns = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 120, defaultSortOrder: 'descend', sorter: (a, b) => b.date.localeCompare(a.date) },
  { title: '总市值', key: 'total_market', width: 130 },
  { title: '当日收益', key: 'today_profit', width: 130 },
  { title: '累计收益', key: 'total_gain', width: 130 },
  { title: '收益率', key: 'total_rate', width: 100 },
  { title: '操作', key: 'action', width: 80 },
]

onMounted(async () => {
  await loadSnapshots()
  // 响应式宽度
  await nextTick()
  const el = document.querySelector('.chart-container')
  if (el) chartWidth.value = Math.max(600, el.clientWidth - 2)
})
</script>

<style scoped>
.snapshot-page { max-width: 1400px; }

.summary-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 4px;
}
.sc-item {
  border-radius: 10px;
  padding: 10px 14px;
  text-align: center;
}
.sc-label {
  display: block; font-size: 12px; color: #8896a7; margin-bottom: 4px; font-weight: 500;
}
.sc-val {
  display: block; font-size: 17px; font-weight: 700; color: #1f2937;
}
.sc-sub {
  display: block; font-size: 11px; color: #bbb; margin-top: 2px;
}
.sc-market { background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%); border-left: 3px solid #6366f1; }
.sc-gain   { background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%); border-left: 3px solid #3b82f6; }
.sc-rate   { background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%); border-left: 3px solid #a855f7; }
.sc-today  { background: linear-gradient(135deg, #fef2f2 0%, #ffe4e6 100%); border-left: 3px solid #f43f5e; }
.sc-count  { background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-left: 3px solid #22c55e; }

.chart-container { width: 100%; overflow-x: auto; }
.line-chart { display: block; margin: 0 auto; }
</style>
