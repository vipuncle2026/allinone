<template>
  <div class="snapshot-page">
    <!-- 顶部操作栏 -->
    <a-card size="small" :bordered="false" style="margin-bottom: 16px">
      <a-space>
        <a-button type="primary" size="small" @click="takeSnapshot" :loading="snapshotting">
          📸 拍摄快照
        </a-button>
        <a-select v-model:value="daysFilter" size="small" style="width: 120px" @change="loadSnapshots">
          <a-select-option :value="30">近 30 天</a-select-option>
          <a-select-option :value="90">近 90 天</a-select-option>
          <a-select-option :value="180">近半年</a-select-option>
          <a-select-option :value="365">近 1 年</a-select-option>
          <a-select-option :value="730">近 2 年</a-select-option>
        </a-select>
        <a-button size="small" @click="loadSnapshots">🔄 刷新</a-button>
      </a-space>
    </a-card>

    <!-- 主内容区：左右布局 -->
    <a-row :gutter="16">
      <!-- 左侧：快照数据表格 -->
      <a-col :span="14">
        <a-card title="📋 快照记录" size="small">
          <template #extra>
            <span style="font-size: 12px; color: #999">共 {{ snapshotsTotal }} 条</span>
          </template>
          <a-table
            :columns="snapshotColumns"
            :data-source="snapshots"
            :pagination="snapshotPagination"
            :loading="loading"
            size="small"
            row-key="id"
            @change="handleTableChange"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'total_assets'">
                <span style="font-weight: 600">¥{{ formatMoney(record.total_assets) }}</span>
              </template>
              <template v-if="column.key === 'total_debt'">
                <span :style="{ color: record.total_debt > 0 ? '#e63946' : '#16a34a' }">
                  ¥{{ formatMoney(record.total_debt) }}
                </span>
              </template>
              <template v-if="column.key === 'net_assets'">
                <span :style="{ fontWeight: 700, color: '#1a56db' }">
                  ¥{{ formatMoney(record.net_assets) }}
                </span>
              </template>
              <template v-if="column.key === 'actions'">
                <a-popconfirm title="确定删除该快照？" @confirm="deleteSnap(record.id)">
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </template>
            </template>
            <template #emptyText>
              <div style="padding: 30px; text-align: center; color: #999">
                <div style="font-size: 24px; margin-bottom: 8px">📸</div>
                <div>暂无快照记录</div>
                <div style="font-size: 12px; color: #bbb; margin-top: 4px">点击「拍摄快照」保存当前资产状态</div>
              </div>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <!-- 右侧：月度统计 -->
      <a-col :span="10">
        <!-- 净资产趋势图 -->
        <a-card title="📈 净资产趋势" size="small" style="margin-bottom: 16px">
          <div style="height: 220px"><canvas ref="trendChartRef"></canvas></div>
          <div v-if="!monthlyStats.length" style="text-align: center; color: #ccc; padding: 30px 0">
            至少需要 2 个月快照数据
          </div>
        </a-card>

        <!-- 账户变化明细 -->
        <a-card title="📊 月度账户变化" size="small">
          <a-table
            :columns="changeColumns"
            :data-source="monthlyStats.filter(m => m.breakdown_changes)"
            :pagination="false"
            size="small"
            row-key="month"
            :scroll="{ y: 300 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'month'">
                <span style="font-weight: 600">{{ record.month }}</span>
              </template>
              <template v-if="column.key === 'net_assets'">
                <span style="font-weight: 600; color: #1a56db">¥{{ formatMoney(record.net_assets) }}</span>
              </template>
              <template v-if="column.key === 'net_change'">
                <span :style="{ fontWeight: 600, color: record.net_change >= 0 ? '#e63946' : '#16a34a' }">
                  {{ record.net_change >= 0 ? '+' : '' }}¥{{ formatMoney(record.net_change) }}
                </span>
              </template>
            </template>
            <template #expandedRowRender="{ record }">
              <div v-if="record.breakdown_changes" style="padding: 4px 0">
                <div v-for="(item, key) in record.breakdown_changes" :key="key"
                  style="display: flex; align-items: center; padding: 4px 8px; border-bottom: 1px solid #f5f5f5; font-size: 13px">
                  <span style="width: 100px; color: #333">{{ key }}</span>
                  <span style="width: 120px; text-align: right; font-weight: 600">¥{{ formatMoney(item.value) }}</span>
                  <span style="width: 120px; text-align: right"
                    :style="{ color: item.change >= 0 ? '#e63946' : '#16a34a', fontWeight: 600 }">
                    {{ item.change >= 0 ? '+' : '' }}¥{{ formatMoney(item.change) }}
                  </span>
                  <span style="width: 80px; text-align: right"
                    :style="{ color: item.change_pct >= 0 ? '#e63946' : '#16a34a' }">
                    {{ item.change_pct >= 0 ? '+' : '' }}{{ item.change_pct.toFixed(2) }}%
                  </span>
                </div>
              </div>
            </template>
            <template #emptyText>
              <div style="padding: 20px; text-align: center; color: #ccc">需要多月快照数据</div>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick, onBeforeUnmount } from 'vue'
import { message } from 'ant-design-vue'
import { financeApi } from '@/api'
import Chart from 'chart.js/auto'

const loading = ref(false)
const snapshotting = ref(false)
const snapshots = ref([])
const snapshotsTotal = ref(0)
const daysFilter = ref(365)
const currentPage = ref(1)
const pageSize = ref(25)
const monthlyStats = ref([])
const trendChartRef = ref(null)
let trendChart = null

// 快照列表分页
const snapshotPagination = computed(() => ({
  current: currentPage.value,
  pageSize: pageSize.value,
  total: snapshotsTotal.value,
  showSizeChanger: false,
  showTotal: total => `共 ${total} 条`,
}))

const snapshotColumns = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
  { title: '总资产', key: 'total_assets', width: 140 },
  { title: '总负债', key: 'total_debt', width: 120 },
  { title: '净资产', key: 'net_assets', width: 140 },
  { title: '操作', key: 'actions', width: 70 },
]

const changeColumns = [
  { title: '月份', key: 'month', width: 90 },
  { title: '净资产', key: 'net_assets', width: 130 },
  { title: '环比变化', key: 'net_change', width: 120 },
]

function formatMoney(val) {
  if (!val && val !== 0) return '0.00'
  return Math.abs(val) >= 10000
    ? val.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    : val.toFixed(2)
}

function handleTableChange(pag) {
  currentPage.value = pag.current
  loadSnapshots()
}

async function loadSnapshots() {
  loading.value = true
  try {
    const res = await financeApi.listSnapshots(daysFilter.value, currentPage.value, pageSize.value)
    const d = res.data
    snapshots.value = d.items || []
    snapshotsTotal.value = d.total || 0
    // 如果当前页没数据了，回到上一页
    if (snapshots.value.length === 0 && currentPage.value > 1) {
      currentPage.value -= 1
      await loadSnapshots()
    }
  } catch (e) {
    message.error('加载快照失败')
  } finally {
    loading.value = false
  }
}

async function loadMonthlyStats() {
  try {
    const res = await financeApi.getSnapshotStats()
    monthlyStats.value = res.data || []
    await nextTick()
    drawTrendChart()
  } catch (e) {
    // ignore
  }
}

async function takeSnapshot() {
  snapshotting.value = true
  try {
    const res = await financeApi.createSnapshot()
    message.success(res.data.message || '快照拍摄成功')
    await loadSnapshots()
    await loadMonthlyStats()
  } catch (e) {
    message.error(e.response?.data?.detail || '拍摄失败')
  } finally {
    snapshotting.value = false
  }
}

async function deleteSnap(id) {
  try {
    await financeApi.deleteSnapshot(id)
    message.success('已删除')
    await loadSnapshots()
    await loadMonthlyStats()
  } catch (e) {
    message.error('删除失败')
  }
}

function drawTrendChart() {
  const canvas = trendChartRef.value
  if (!canvas) return
  if (trendChart) { trendChart.destroy(); trendChart = null }
  const items = monthlyStats.value
  if (items.length < 2) return

  const labels = items.map(m => m.month.slice(5)) // MM
  const netData = items.map(m => m.net_assets)
  const debtData = items.map(m => m.total_debt)

  trendChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: '净资产',
          data: netData,
          borderColor: '#1a56db',
          backgroundColor: 'rgba(26,86,219,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointHoverRadius: 5,
          borderWidth: 2,
        },
        {
          label: '负债',
          data: debtData,
          borderColor: '#e63946',
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.3,
          pointRadius: 2,
          borderWidth: 1.5,
          borderDash: [4, 4],
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: 'index' },
      plugins: {
        legend: { position: 'top', labels: { font: { size: 11 }, boxWidth: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => ctx.dataset.label + ': ¥' + ctx.parsed.y.toLocaleString('zh-CN', { minimumFractionDigits: 2 }),
          },
        },
      },
      scales: {
        x: { ticks: { font: { size: 11 } }, grid: { display: false } },
        y: {
          ticks: {
            font: { size: 10 },
            callback: v => v >= 10000 ? (v / 10000).toFixed(0) + 'w' : v,
          },
          grid: { color: '#f0f0f0' },
        },
      },
    },
  })
}

onBeforeUnmount(() => {
  if (trendChart) { trendChart.destroy(); trendChart = null }
})

onMounted(() => {
  loadSnapshots()
  loadMonthlyStats()
})
</script>

<style scoped>
.snapshot-page { max-width: 1400px; }
</style>
