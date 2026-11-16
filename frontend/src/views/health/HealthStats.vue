<template>
  <div class="health-stats">
    <a-spin :spinning="loading">
      <!-- 成员概览卡片 -->
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
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { Chart, registerables } from 'chart.js'
import { healthApi } from '@/api'

Chart.register(...registerables)

const loading = ref(false)
const overview = ref([])
const selectedMember = ref(null)
const itemOptions = ref([])
const selectedItem = ref(undefined)
const itemLoading = ref(false)
const abnormal = ref(null)
const trendChartRef = ref(null)
let chartInstance = null

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

async function loadOverview() {
  loading.value = true
  try {
    const { data } = await healthApi.statsOverview()
    overview.value = data || []
    if (overview.value.length) await selectMember(overview.value[0].id)
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function selectMember(id) {
  selectedMember.value = id
  selectedItem.value = undefined
  destroyChart()
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

function destroyChart() {
  if (chartInstance) { chartInstance.destroy(); chartInstance = null }
}

async function loadTrend() {
  if (!selectedItem.value) return
  try {
    const { data } = await healthApi.statsTrends(selectedMember.value, selectedItem.value)
    await nextTick()
    renderChart(data || [])
  } catch (e) {
    message.error(e.response?.data?.detail || '加载趋势失败')
  }
}

function renderChart(points) {
  destroyChart()
  if (!trendChartRef.value) return
  chartInstance = new Chart(trendChartRef.value, {
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

onMounted(loadOverview)
onBeforeUnmount(destroyChart)
</script>

<style scoped>
.health-stats { padding: 4px; }
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
.chart-box { height: 300px; position: relative; }
.ab-head { margin-bottom: 10px; display: flex; gap: 10px; align-items: baseline; }
.ab-date { font-weight: 600; font-size: 14px; }
.ab-hosp { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.ab-row { display: flex; align-items: center; gap: 8px; padding: 8px 0; border-bottom: 1px solid var(--border-color, #f0f0f0); font-size: 13px; }
.ab-row:last-child { border-bottom: none; }
.ab-name { flex: 1; color: var(--text-primary, #334155); }
.ab-val { font-weight: 600; color: #ef4444; }
.ab-ref { font-size: 12px; color: var(--text-tertiary, #94a3b8); min-width: 80px; text-align: right; }
</style>
