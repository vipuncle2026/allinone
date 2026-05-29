<template>
  <div class="holding-page">
    <a-card title="📊 持仓分析" size="small" :body-style="{ padding: '12px 16px' }">
      <template #extra>
        <a-space>
          <a-button size="small" @click="refreshAndLoad">🔄 刷新估值</a-button>
          <a-button size="small" @click="exportData">📤 导出</a-button>
          <a-button size="small" @click="$refs.importInput.click()">📥 导入</a-button>
          <input ref="importInput" type="file" accept=".json" style="display: none" @change="importData" />
        </a-space>
      </template>

      <!-- 未设置成本净值提示 -->
      <div v-if="summary.missing_cost_count > 0"
        style="background: #fffbe6; border: 1px solid #ffe58f; border-radius: 6px; padding: 6px 12px; margin-bottom: 12px; font-size: 12px; color: #ad6800">
        ⚠️ {{ summary.missing_cost_count }} 只基金未设置成本净值，累计收益/收益率无法计算。
      </div>

      <!-- 第一行：指标卡片 -->
      <div class="summary-cards">
        <div class="sc-item sc-market">
          <span class="sc-label">总市值</span>
          <span class="sc-val">¥{{ fmtMoney(summary.total_market) }}</span>
        </div>
        <div class="sc-item sc-gain">
          <span class="sc-label">累计收益</span>
          <span v-if="summary.total_cost > 0" class="sc-val"
            :style="{ color: summary.total_gain >= 0 ? '#e63946' : '#16a34a' }">
            {{ summary.total_gain >= 0 ? '+' : '' }}¥{{ fmtMoney(summary.total_gain) }}
          </span>
          <span v-else class="sc-val sc-nodata">-</span>
        </div>
        <div class="sc-item sc-today">
          <span class="sc-label">今日收益</span>
          <span class="sc-val"
            :style="{ color: summary.today_profit >= 0 ? '#e63946' : '#16a34a' }">
            {{ summary.today_profit >= 0 ? '+' : '' }}¥{{ fmtMoney(summary.today_profit) }}
          </span>
        </div>
        <div class="sc-item sc-yesterday">
          <span class="sc-label">昨日收益</span>
          <span v-if="summary.yesterday_profit !== 0" class="sc-val"
            :style="{ color: summary.yesterday_profit >= 0 ? '#e63946' : '#16a34a' }">
            {{ summary.yesterday_profit >= 0 ? '+' : '' }}¥{{ fmtMoney(summary.yesterday_profit) }}
          </span>
          <span v-else class="sc-val sc-nodata">--</span>
        </div>
        <div class="sc-item sc-rate">
          <span class="sc-label">总收益率</span>
          <span v-if="summary.total_cost > 0" class="sc-val"
            :style="{ color: summary.total_rate >= 0 ? '#e63946' : '#16a34a' }">
            {{ summary.total_rate >= 0 ? '+' : '' }}{{ summary.total_rate.toFixed(2) }}%
          </span>
          <span v-else class="sc-val sc-nodata">-</span>
        </div>
      </div>

      <!-- 第二行：饼图 + 基金名称清单 -->
      <div v-if="summary.holdings && summary.holdings.length" class="detail-row">
        <!-- 左侧饼图 -->
        <div class="chart-area">
          <div class="pie-wrap">
            <svg width="150" height="150" viewBox="0 0 150 150" v-html="piePaths"></svg>
            <div class="pie-center">
              <div class="pc-val">{{ summary.total_market >= 10000 ? (summary.total_market / 10000).toFixed(1) + 'w' : summary.total_market.toFixed(0) }}</div>
              <div class="pc-label">总市值</div>
            </div>
          </div>
        </div>

        <!-- 右侧基金名称清单（4列） -->
        <div class="fund-grid">
          <div v-for="col in fundColumns" :key="'col-' + col.idx" class="fund-col">
            <div v-for="item in col.items" :key="item.code" class="fl-item">
              <span class="fl-dot" :style="{ backgroundColor: getColor(item.code) }"></span>
              <span class="fl-name" :title="item.name">{{ item.name }}</span>
              <span class="fl-pct">{{ (item.market_value / summary.total_market * 100).toFixed(1) }}%</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 持仓明细表格 -->
      <a-table v-if="summary.holdings && summary.holdings.length"
        :columns="columns" :data-source="summary.holdings" :pagination="{ pageSize: 25, showSizeChanger: false, showTotal: total => `共 ${total} 支` }" size="small" row-key="code"
        style="margin-top: 12px">
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <span style="font-weight: 600">{{ record.name }}</span>
            <span style="color: #999; margin-left: 6px; font-size: 12px">{{ record.code }}</span>
          </template>
          <template v-if="column.key === 'cur_nav'">
            <span>{{ (record.cur_nav || 0).toFixed(4) }}</span>
            <span :style="{ color: record.day_chg >= 0 ? '#e63946' : '#16a34a', fontSize: '12px', marginLeft: '4px' }">
              {{ record.day_chg ? (record.day_chg >= 0 ? '+' : '') + record.day_chg.toFixed(2) + '%' : '' }}
            </span>
          </template>
          <template v-if="column.key === 'market_value'">
            <span style="font-weight: 600">¥{{ record.market_value.toLocaleString(undefined, { maximumFractionDigits: 2 }) }}</span>
          </template>
          <template v-if="column.key === 'gain'">
            <span v-if="record.has_cost" :style="{ color: record.gain >= 0 ? '#e63946' : '#16a34a', fontWeight: 600 }">
              {{ record.gain >= 0 ? '+' : '' }}¥{{ record.gain.toFixed(2) }}
            </span>
            <span v-else style="color: #ccc">-</span>
          </template>
          <template v-if="column.key === 'rate'">
            <span v-if="record.has_cost" :style="{ color: record.rate >= 0 ? '#e63946' : '#16a34a', fontWeight: 600 }">
              {{ record.rate >= 0 ? '+' : '' }}{{ record.rate.toFixed(2) }}%
            </span>
            <span v-else style="color: #ccc">-</span>
          </template>
          <template v-if="column.key === 'today_gain'">
            <span :style="{ color: record.today_gain >= 0 ? '#e63946' : '#16a34a' }">
              {{ record.today_gain >= 0 ? '+' : '' }}¥{{ record.today_gain.toFixed(2) }}
            </span>
          </template>
        </template>
      </a-table>

      <div v-else style="padding: 40px; text-align: center; color: #999">
        <div style="font-size: 36px; margin-bottom: 8px">📊</div>
        <div>暂无持仓数据</div>
        <div style="font-size: 12px; color: #bbb; margin-top: 4px">请先在「自选基金」中添加基金，并设置持仓份额和成本净值</div>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { fundApi } from '@/api'

const summary = ref({
  total_market: 0, total_cost: 0, total_gain: 0,
  total_rate: 0, today_profit: 0, yesterday_profit: 0, holdings: [],
})
const loading = ref(false)
const colors = ['#1a56db', '#e63946', '#16a34a', '#f59e0b', '#7c3aed', '#0891b2', '#f97316', '#8b5cf6']

// 基金名称清单：4列，每列最多10只
const COLS = 4
const MAX_PER_COL = 10
const fundColumns = computed(() => {
  const items = summary.value.holdings || []
  const cols = Array.from({ length: COLS }, () => ({ idx: 0, items: [] }))
  items.forEach((item, i) => {
    const colIdx = Math.floor(i / MAX_PER_COL)
    if (colIdx < COLS) {
      cols[colIdx].items.push(item)
      cols[colIdx].idx = colIdx
    }
  })
  return cols.filter(c => c.items.length > 0)
})

// 根据基金在列表中的位置返回颜色
function getColor(code) {
  const idx = (summary.value.holdings || []).findIndex(h => h.code === code)
  return idx >= 0 ? colors[idx % colors.length] : '#999'
}

const columns = [
  { title: '基金名称', dataIndex: 'name', key: 'name', width: 180 },
  { title: '代码', dataIndex: 'code', key: 'code', width: 80 },
  { title: '持仓份额', dataIndex: 'shares', key: 'shares', width: 100, customRender: ({ text }) => text?.toLocaleString() },
  { title: '成本净值', dataIndex: 'cost_nav', key: 'cost_nav', width: 100, customRender: ({ text }) => (text || 0).toFixed(4) },
  { title: '当前净值/估值', key: 'cur_nav', width: 140 },
  { title: '持仓市值', key: 'market_value', width: 120 },
  { title: '累计收益', key: 'gain', width: 120 },
  { title: '收益率', key: 'rate', width: 100 },
  { title: '今日估算收益', key: 'today_gain', width: 120 },
]

// SVG 饼图路径计算
const piePaths = computed(() => {
  const holdings = summary.value.holdings
  if (!holdings || !holdings.length) return ''
  const values = holdings.map(h => h.market_value)
  const sum = values.reduce((a, b) => a + b, 0)
  if (sum === 0) return ''

  const cx = 75, cy = 75, r = 65, ir = 42
  let startAngle = -Math.PI / 2
  let paths = ''

  values.forEach((v, i) => {
    const angle = (v / sum) * 2 * Math.PI
    const endAngle = startAngle + angle
    const x1 = cx + r * Math.cos(startAngle), y1 = cy + r * Math.sin(startAngle)
    const x2 = cx + r * Math.cos(endAngle), y2 = cy + r * Math.sin(endAngle)
    const ix1 = cx + ir * Math.cos(startAngle), iy1 = cy + ir * Math.sin(startAngle)
    const ix2 = cx + ir * Math.cos(endAngle), iy2 = cy + ir * Math.sin(endAngle)
    const large = angle > Math.PI ? 1 : 0
    paths += `<path d="M${ix1},${iy1} L${x1},${y1} A${r},${r} 0 ${large} 1 ${x2},${y2} L${ix2},${iy2} A${ir},${ir} 0 ${large} 0 ${ix1},${iy1}" fill="${colors[i % colors.length]}" opacity="0.88"/>`
    startAngle = endAngle
  })
  return paths
})

function fmtMoney(val) {
  if (val === undefined || val === null) return '0.00'
  return Math.abs(val) >= 10000 ? val.toFixed(2) : val.toFixed(2)
}

async function loadSummary() {
  loading.value = true
  try {
    const res = await fundApi.holdingSummary()
    summary.value = res.data
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function refreshAndLoad() {
  try {
    await fundApi.refresh()
    message.success('估值已刷新')
    await loadSummary()
  } catch (e) {
    message.error('刷新失败')
  }
}

async function exportData() {
  try {
    const res = await fundApi.exportData()
    const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `allinone-funds-${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) {
    message.error('导出失败')
  }
}

async function importData(e) {
  const file = e.target.files[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = async (ev) => {
    try {
      const json = JSON.parse(ev.target.result)
      const fundsObj = json.funds || json
      if (typeof fundsObj !== 'object') {
        message.error('文件格式无效')
        return
      }
      const items = Object.values(fundsObj).map(f => ({
        code: f.code,
        name: f.name,
        type: f.type,
        is_etf: f.is_etf,
        group_id: f.group_id,
        shares: f.shares,
        cost_nav: f.cost_nav,
        nav: f.nav,
        est_nav: f.est_nav,
        day_chg: f.day_chg,
        nav_date: f.nav_date,
        val_time: f.val_time,
        manager: f.manager,
        company: f.company,
        scale: f.scale,
      }))
      const res = await fundApi.importData(items)
      message.success(res.data.message)
      await loadSummary()
    } catch (err) {
      message.error('文件解析失败')
    }
  }
  reader.readAsText(file)
  e.target.value = ''
}

onMounted(() => {
  loadSummary()
})
</script>

<style scoped>
.holding-page { max-width: 1400px; }

/* 第一行：指标卡片 */
.summary-cards {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.sc-item {
  border-radius: 10px;
  padding: 12px 14px;
  text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
}
.sc-item:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}
.sc-label {
  display: block;
  font-size: 12px;
  color: #8896a7;
  margin-bottom: 6px;
  font-weight: 500;
}
.sc-val {
  display: block;
  font-size: 17px;
  font-weight: 700;
  color: #1f2937;
}
.sc-val.sc-nodata {
  color: #cbd5e1;
  font-weight: 400;
}

/* 各卡片独立淡雅背景 */
.sc-market {
  background: linear-gradient(135deg, #eef2ff 0%, #e0e7ff 100%);
  border-left: 3px solid #6366f1;
}
.sc-gain {
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
  border-left: 3px solid #3b82f6;
}
.sc-today {
  background: linear-gradient(135deg, #fef2f2 0%, #ffe4e6 100%);
  border-left: 3px solid #f43f5e;
}
.sc-yesterday {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%);
  border-left: 3px solid #22c55e;
}
.sc-rate {
  background: linear-gradient(135deg, #faf5ff 0%, #f3e8ff 100%);
  border-left: 3px solid #a855f7;
}

/* 第二行：饼图 + 基金名称清单 */
.detail-row {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 12px;
}

/* 左侧饼图 */
.chart-area {
  flex-shrink: 0;
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pie-wrap { position: relative; }
.pie-center {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%); text-align: center;
}
.pc-val { font-size: 14px; font-weight: 700; }
.pc-label { font-size: 10px; color: #999; }

/* 右侧基金名称清单（4列） */
.fund-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  background: #f8fafc;
  border-radius: 8px;
  padding: 10px 12px;
}
.fund-col { display: flex; flex-direction: column; gap: 2px; }
.fl-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 3px 4px;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.5;
}
.fl-item:hover { background: #eef2ff; }
.fl-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
.fl-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: #333; }
.fl-pct { flex-shrink: 0; font-weight: 600; color: #666; min-width: 36px; text-align: right; }
</style>
