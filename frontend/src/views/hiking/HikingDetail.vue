<template>
  <div v-if="activity" class="detail-wrap">
    <!-- 顶部标题栏 -->
    <div class="detail-header">
      <div class="detail-header-row">
        <div>
          <div class="back-btn" @click="$router.back()">← 返回</div>
          <div class="header-title">
            <span class="activity-title">{{ activity.title }}</span>
            <a-tag :color="fileTypeColor(activity.file_type)" style="margin-left: 8px">
              {{ (activity.file_type || 'manual').toUpperCase() }}
            </a-tag>
          </div>
          <div class="header-meta">{{ activity.date }} &nbsp;·&nbsp; {{ activity.trail_name || '' }}</div>
        </div>
        <a-space>
          <a-button @click="showEditModal">✏️ 编辑</a-button>
          <a-popconfirm title="确认删除此活动？" @confirm="deleteActivity">
            <a-button danger>🗑️ 删除</a-button>
          </a-popconfirm>
        </a-space>
      </div>
    </div>

    <!-- 核心数据卡片 -->
    <div class="stats-grid">
      <div class="stat-card" v-for="s in coreStats" :key="s.label">
        <div class="stat-icon">{{ s.icon }}</div>
        <div class="stat-value" :style="{ color: s.color || '#2d9a4e' }">{{ s.value }}</div>
        <div class="stat-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 地图 + 海拔剖面（同行） -->
    <div v-if="mapPoints.length || altData.length" class="map-alt-row">
      <!-- 轨迹地图 -->
      <div v-if="mapPoints.length" class="section-card map-card">
        <div class="section-title">🗺️ 轨迹地图</div>
        <div ref="mapRef" class="map-container"></div>
      </div>
      <!-- 海拔剖面 -->
      <div v-if="altData.length" class="section-card alt-card">
        <div class="section-title">⛰️ 海拔剖面</div>
        <div class="chart-wrap-tall"><canvas ref="altChartRef"></canvas></div>
      </div>
    </div>

    <!-- 其余图表（心率 + 速度） -->
    <div v-if="heartRateData.length || speedData.length" style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px">
      <!-- 心率折线图 -->
      <div class="section-card" v-if="heartRateData.length">
        <div class="section-title">❤️ 心率变化</div>
        <div class="chart-wrap"><canvas ref="hrChartRef"></canvas></div>
      </div>
      <!-- 速度折线图 -->
      <div class="section-card" v-if="speedData.length">
        <div class="section-title">⚡ 速度变化</div>
        <div class="chart-wrap"><canvas ref="speedChartRef"></canvas></div>
      </div>
    </div>

    <!-- 详细信息表 -->
    <div class="section-card">
      <div class="section-title">📋 活动详情</div>
      <a-descriptions :column="3" bordered size="small">
        <a-descriptions-item label="活动日期">{{ activity.date }}</a-descriptions-item>
        <a-descriptions-item label="开始时间">{{ formatTime(activity.start_time) }}</a-descriptions-item>
        <a-descriptions-item label="结束时间">{{ formatTime(activity.end_time) }}</a-descriptions-item>
        <a-descriptions-item label="总距离">{{ activity.distance_km ? activity.distance_km + ' km' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="总时长">{{ formatDuration(activity.duration_sec) }}</a-descriptions-item>
        <a-descriptions-item label="平均配速">{{ activity.pace_min_km ? formatPace(activity.pace_min_km) : '-' }}</a-descriptions-item>
        <a-descriptions-item label="累计爬升">{{ activity.elevation_gain != null ? activity.elevation_gain + ' m' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="累计下降">{{ activity.elevation_loss != null ? activity.elevation_loss + ' m' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="最高海拔">{{ activity.max_elevation != null ? activity.max_elevation + ' m' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="最低海拔">{{ activity.min_elevation != null ? activity.min_elevation + ' m' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="平均速度">{{ activity.avg_speed_kmh != null ? activity.avg_speed_kmh + ' km/h' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="最大速度">{{ activity.max_speed_kmh != null ? activity.max_speed_kmh + ' km/h' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="平均心率">{{ activity.avg_heart_rate != null ? activity.avg_heart_rate + ' bpm' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="最高心率">{{ activity.max_heart_rate != null ? activity.max_heart_rate + ' bpm' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="热量消耗">{{ activity.calories != null ? activity.calories + ' kcal' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="平均步频">{{ activity.avg_cadence != null ? activity.avg_cadence + ' spm' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="最高步频">{{ activity.max_cadence != null ? activity.max_cadence + ' spm' : '-' }}</a-descriptions-item>
        <a-descriptions-item label="步数">{{ activity.steps != null ? activity.steps : '-' }}</a-descriptions-item>
        <a-descriptions-item label="路线名称">{{ activity.trail_name || '-' }}</a-descriptions-item>
        <a-descriptions-item label="难度">
          <a-tag :color="difficultyColor(activity.difficulty)">{{ activity.difficulty || '-' }}</a-tag>
        </a-descriptions-item>
        <a-descriptions-item label="天气">{{ activity.weather || '-' }}</a-descriptions-item>
        <a-descriptions-item label="备注" :span="3">{{ activity.notes || '-' }}</a-descriptions-item>
      </a-descriptions>
    </div>

    <!-- 编辑弹窗 -->
    <a-modal v-model:open="editModalOpen" title="编辑徒步活动" @ok="saveEdit" width="600px">
      <a-form :model="editForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="活动名称" required><a-input v-model:value="editForm.title" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="日期"><a-date-picker v-model:value="editForm.date" valueFormat="YYYY-MM-DD" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="路线名称"><a-input v-model:value="editForm.trail_name" placeholder="如：太行山穿越" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="难度">
              <a-select v-model:value="editForm.difficulty">
                <a-select-option value="简单">简单</a-select-option>
                <a-select-option value="中等">中等</a-select-option>
                <a-select-option value="困难">困难</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="天气"><a-input v-model:value="editForm.weather" placeholder="晴/多云/雨…" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model:value="editForm.notes" :rows="3" /></a-form-item>
      </a-form>
    </a-modal>
  </div>

  <div v-else-if="loading" style="text-align: center; padding: 80px">
    <a-spin size="large" />
  </div>
  <div v-else style="text-align: center; padding: 80px; color: #999">活动不存在</div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { hikingApi } from '@/api/index'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { Chart, registerables } from 'chart.js'
Chart.register(...registerables)

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const activity = ref(null)
const mapPoints = ref([])
const chartPoints = ref([])

// 编辑
const editModalOpen = ref(false)
const editForm = ref({ title: '', date: '', trail_name: '', difficulty: '', weather: '', notes: '' })

const mapRef = ref(null)
const hrChartRef = ref(null)
const altChartRef = ref(null)
const speedChartRef = ref(null)

let mapInstance = null
let hrChart = null
let altChart = null
let speedChart = null

// ─── 解析轨迹数据 ─────────────────────────────────────────
function parseTrackJson(trackJson) {
  if (!trackJson) return { map: [], chart: [] }
  try {
    const parsed = typeof trackJson === 'string' ? JSON.parse(trackJson) : trackJson
    if (Array.isArray(parsed)) {
      // 旧格式：直接是数组（地图点）
      return { map: parsed, chart: [] }
    }
    return { map: parsed.map || [], chart: parsed.chart || [] }
  } catch {
    return { map: [], chart: [] }
  }
}

// ─── 图表数据 ─────────────────────────────────────────────
const heartRateData = computed(() => chartPoints.value.filter(p => p.heart_rate != null))
const altData = computed(() => chartPoints.value.filter(p => p.alt != null))
const speedData = computed(() => chartPoints.value.filter(p => p.speed != null && p.speed > 0))
const hasChartData = computed(() => heartRateData.value.length || altData.value.length || speedData.value.length)

// ─── 核心统计卡片 ──────────────────────────────────────────
const coreStats = computed(() => {
  if (!activity.value) return []
  const a = activity.value
  return [
    { icon: '📏', label: '距离', value: a.distance_km ? a.distance_km + ' km' : '-', color: '#2d9a4e' },
    { icon: '⏱️', label: '时长', value: formatDuration(a.duration_sec), color: '#1677ff' },
    { icon: '🚶', label: '配速', value: a.pace_min_km ? formatPace(a.pace_min_km) : '-', color: '#7c3aed' },
    { icon: '↑', label: '爬升', value: a.elevation_gain != null ? a.elevation_gain + ' m' : '-', color: '#d97706' },
    { icon: '⛰️', label: '最高海拔', value: a.max_elevation != null ? a.max_elevation + ' m' : '-', color: '#0891b2' },
    { icon: '❤️', label: '均心率', value: a.avg_heart_rate != null ? a.avg_heart_rate + ' bpm' : '-', color: '#e11d48' },
    { icon: '⚡', label: '最大速度', value: a.max_speed_kmh != null ? a.max_speed_kmh + ' km/h' : '-', color: '#ea580c' },
    { icon: '🔥', label: '热量', value: a.calories != null ? a.calories + ' kcal' : '-', color: '#dc2626' },
  ]
})

// ─── 工具函数 ─────────────────────────────────────────────
function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

function formatPace(minPerKm) {
  const m = Math.floor(minPerKm)
  const s = Math.round((minPerKm - m) * 60)
  return `${m}'${s.toString().padStart(2, '0')}"/km`
}

function formatTime(t) {
  if (!t) return '-'
  return t.replace('T', ' ').replace('Z', '').slice(0, 19)
}

function difficultyColor(d) {
  return { '简单': 'green', '中等': 'orange', '困难': 'red' }[d] || 'default'
}

function fileTypeColor(t) {
  return { 'fit': 'blue', 'tcx': 'purple', 'gpx': 'green', 'manual': 'orange' }[t] || 'default'
}

function showEditModal() {
  const a = activity.value
  editForm.value = {
    title: a.title || '',
    date: a.date || '',
    trail_name: a.trail_name || '',
    difficulty: a.difficulty || '',
    weather: a.weather || '',
    notes: a.notes || '',
  }
  editModalOpen.value = true
}

async function saveEdit() {
  if (!editForm.value.title) { message.warning('请填写活动名称'); return }
  try {
    await hikingApi.updateActivity(activity.value.id, editForm.value)
    message.success('保存成功')
    editModalOpen.value = false
    // 刷新数据
    const { data } = await hikingApi.getActivity(route.params.id)
    activity.value = data
    const { map, chart } = parseTrackJson(data.track_json)
    mapPoints.value = map
    chartPoints.value = chart
    await nextTick()
    initMap()
    initCharts()
  } catch (e) {
    message.error('保存失败')
  }
}

async function deleteActivity() {
  await hikingApi.deleteActivity(activity.value.id)
  message.success('已删除')
  router.push('/sports/hiking/list')
}

// ─── 初始化地图 ───────────────────────────────────────────
function initMap() {
  if (!mapRef.value || !mapPoints.value.length) return
  if (mapInstance) { mapInstance.remove(); mapInstance = null }

  const center = [mapPoints.value[0].lat, mapPoints.value[0].lon]
  mapInstance = L.map(mapRef.value, { zoomControl: true }).setView(center, 15)

  L.tileLayer(
    'https://webrd0{s}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scale=1&style=8&x={x}&y={y}&z={z}',
    { subdomains: '1234', maxZoom: 18, attribution: '© 高德地图' }
  ).addTo(mapInstance)

  const latlngs = mapPoints.value.map(p => [p.lat, p.lon])
  const polyline = L.polyline(latlngs, { color: '#22c55e', weight: 4, opacity: 0.85 }).addTo(mapInstance)
  mapInstance.fitBounds(polyline.getBounds(), { padding: [20, 20] })

  // 起点/终点标记
  const startIcon = L.divIcon({ html: '<div style="background:#22c55e;color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)">S</div>', iconSize: [20, 20], iconAnchor: [10, 10], className: '' })
  const endIcon = L.divIcon({ html: '<div style="background:#ef4444;color:#fff;border-radius:50%;width:20px;height:20px;display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:bold;border:2px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.3)">F</div>', iconSize: [20, 20], iconAnchor: [10, 10], className: '' })

  L.marker([latlngs[0][0], latlngs[0][1]], { icon: startIcon }).addTo(mapInstance).bindPopup('起点')
  L.marker([latlngs[latlngs.length - 1][0], latlngs[latlngs.length - 1][1]], { icon: endIcon }).addTo(mapInstance).bindPopup('终点')
}

// ─── 初始化图表 ───────────────────────────────────────────
function initCharts() {
  // 心率图
  if (hrChartRef.value && heartRateData.value.length) {
    const labels = heartRateData.value.map((_, i) => i)
    const hrValues = heartRateData.value.map(p => p.heart_rate)
    hrChart = new Chart(hrChartRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '心率 (bpm)',
          data: hrValues,
          borderColor: '#e11d48',
          backgroundColor: 'rgba(225,29,72,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 1.5,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: {
            title: { display: true, text: 'bpm', font: { size: 11 } },
            ticks: { font: { size: 11 } },
          }
        }
      }
    })
  }

  // 海拔图
  if (altChartRef.value && altData.value.length) {
    const labels = altData.value.map(p => p.distance != null ? (p.distance / 1000).toFixed(2) + ' km' : '')
    const altValues = altData.value.map(p => p.alt)
    altChart = new Chart(altChartRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '海拔 (m)',
          data: altValues,
          borderColor: '#0891b2',
          backgroundColor: 'rgba(8,145,178,0.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 1.5,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { maxTicksLimit: 6, font: { size: 10 } } },
          y: {
            title: { display: true, text: 'm', font: { size: 11 } },
            ticks: { font: { size: 11 } },
          }
        }
      }
    })
  }

  // 速度图
  if (speedChartRef.value && speedData.value.length) {
    const labels = speedData.value.map((_, i) => i)
    const speedValues = speedData.value.map(p => p.speed)
    speedChart = new Chart(speedChartRef.value, {
      type: 'line',
      data: {
        labels,
        datasets: [{
          label: '速度 (km/h)',
          data: speedValues,
          borderColor: '#ea580c',
          backgroundColor: 'rgba(234,88,12,0.08)',
          fill: true,
          tension: 0.3,
          pointRadius: 0,
          borderWidth: 1.5,
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: {
            title: { display: true, text: 'km/h', font: { size: 11 } },
            ticks: { font: { size: 11 } },
          }
        }
      }
    })
  }
}

// ─── 加载数据 ─────────────────────────────────────────────
onMounted(async () => {
  const id = route.params.id
  try {
    const { data } = await hikingApi.getActivity(id)
    activity.value = data
    const { map, chart } = parseTrackJson(data.track_json)
    mapPoints.value = map
    chartPoints.value = chart

    await nextTick()
    initMap()
    initCharts()
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
})

onUnmounted(() => {
  if (mapInstance) { mapInstance.remove(); mapInstance = null }
  hrChart?.destroy()
  altChart?.destroy()
  speedChart?.destroy()
})
</script>

<style scoped>
.detail-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 0 4px;
}

.detail-header {
  margin-bottom: 20px;
}

.detail-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
}

.back-btn {
  color: #666;
  cursor: pointer;
  font-size: 13px;
  margin-bottom: 8px;
  display: inline-block;
}
.back-btn:hover { color: #2d9a4e; }

.header-title {
  font-size: 22px;
  font-weight: 700;
  color: #1a1a1a;
  display: flex;
  align-items: center;
}

.header-meta {
  font-size: 13px;
  color: #888;
  margin-top: 4px;
}

/* 核心统计卡片 */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}

.stat-card {
  background: #fff;
  border-radius: 12px;
  padding: 14px 8px;
  text-align: center;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}

.stat-icon {
  font-size: 20px;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  font-size: 11px;
  color: #999;
  margin-top: 3px;
}

/* 地图 */
.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  box-shadow: 0 1px 4px rgba(0,0,0,.06);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 12px;
}

.map-container {
  height: 400px;
  border-radius: 8px;
  overflow: hidden;
}

/* 地图 + 海拔并排 */
.map-alt-row {
  display: grid;
  grid-template-columns: 1fr 380px;
  gap: 16px;
  margin-bottom: 16px;
  align-items: stretch;
}

/* 只有地图（无海拔）时占满宽度 */
.map-alt-row:has(.map-card:only-child) {
  grid-template-columns: 1fr;
}

.map-card,
.alt-card {
  margin-bottom: 0 !important;
}

.alt-card {
  display: flex;
  flex-direction: column;
}

/* 海拔剖面图撑满卡片剩余高度 */
.chart-wrap-tall {
  position: relative;
  flex: 1;
  min-height: 280px;
}

/* 图表 */
.chart-wrap {
  position: relative;
  height: 200px;
}
</style>
