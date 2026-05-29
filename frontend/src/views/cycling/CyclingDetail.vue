<template>
  <div>
    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px">
      <a-button @click="$router.back()">← 返回列表</a-button>
      <a-space>
        <a-button @click="showEditModal">✏️ 编辑</a-button>
        <a-popconfirm title="确认删除此活动？" @confirm="deleteActivity">
          <a-button danger>🗑️ 删除</a-button>
        </a-popconfirm>
      </a-space>
    </div>

    <a-spin :spinning="loading">
      <template v-if="activity">
        <a-card :bordered="false" style="border-radius: 16px; margin-bottom: 24px">
          <template #title>
            <span>{{ activity.title }}</span>
          </template>
          <template #extra>
            <a-space>
              <a-tag :color="activity.file_type === 'fit' ? 'blue' : activity.file_type === 'manual' ? 'orange' : 'green'">
                {{ (activity.file_type || 'manual').toUpperCase() }}
              </a-tag>
              <span style="color: #999">{{ activity.date }}</span>
              <span v-if="activity.weather" style="color: #666">{{ activity.weather }}</span>
            </a-space>
          </template>

          <!-- 核心指标 -->
          <div class="metrics-grid">
            <div v-for="m in metrics" :key="m.label" class="metric-item">
              <div class="metric-value">{{ m.value }}</div>
              <div class="metric-label">{{ m.label }}</div>
              <div class="metric-unit">{{ m.unit }}</div>
            </div>
          </div>
        </a-card>

        <!-- 地图 + 海拔剖面 -->
        <a-row :gutter="16" style="margin-bottom: 24px">
          <a-col :span="16">
            <a-card :bordered="false" style="border-radius: 16px; padding: 0; overflow: hidden">
              <TrackMap
                v-if="trackPoints.length"
                :track-points="trackPoints"
                :show-tile-bar="true"
                style="height: 420px"
              />
              <div v-else style="height: 200px; display: flex; align-items: center; justify-content: center; color: #999">
                暂无轨迹数据
              </div>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card :bordered="false" style="border-radius: 16px; height: 420px" title="🏔️ 海拔剖面">
              <div v-if="elevationData.length" class="elevation-chart-wrap">
                <canvas ref="elevChartRef"></canvas>
              </div>
              <div v-else style="display: flex; align-items: center; justify-content: center; height: 340px; color: #999">
                暂无海拔数据
              </div>
            </a-card>
          </a-col>
        </a-row>

        <!-- 详细数据 -->
        <a-card title="详细数据" :bordered="false" style="border-radius: 16px">
          <a-descriptions bordered :column="3" size="small">
            <a-descriptions-item v-if="activity.avg_power_w" label="平均功率">
              <span style="font-weight: 600; color: #667eea">{{ activity.avg_power_w }}</span> W
            </a-descriptions-item>
            <a-descriptions-item v-if="activity.max_power_w" label="最大功率">{{ activity.max_power_w }} W</a-descriptions-item>
            <a-descriptions-item v-if="activity.normalized_power" label="标准化功率 NP">
              <span style="font-weight: 600; color: #667eea">{{ activity.normalized_power }}</span> W
            </a-descriptions-item>
            <a-descriptions-item v-if="activity.tss" label="训练压力分 TSS">
              <span style="font-weight: 600; color: #f59e0b">{{ activity.tss }}</span>
            </a-descriptions-item>
            <a-descriptions-item v-if="activity.avg_heart_rate" label="平均心率">
              {{ activity.avg_heart_rate }} bpm
            </a-descriptions-item>
            <a-descriptions-item v-if="activity.max_heart_rate" label="最高心率">{{ activity.max_heart_rate }} bpm</a-descriptions-item>
            <a-descriptions-item v-if="activity.avg_cadence" label="平均踏频">{{ activity.avg_cadence }} rpm</a-descriptions-item>
            <a-descriptions-item v-if="activity.max_cadence" label="最高踏频">{{ activity.max_cadence }} rpm</a-descriptions-item>
            <a-descriptions-item v-if="activity.max_elevation" label="最高海拔">{{ activity.max_elevation }} m</a-descriptions-item>
            <a-descriptions-item v-if="activity.min_elevation" label="最低海拔">{{ activity.min_elevation }} m</a-descriptions-item>
            <a-descriptions-item v-if="activity.elevation_loss" label="累计下降">{{ activity.elevation_loss }} m</a-descriptions-item>
            <a-descriptions-item label="路线类型">{{ activity.route_type || '-' }}</a-descriptions-item>
            <a-descriptions-item label="天气">{{ activity.weather || '-' }}</a-descriptions-item>
            <a-descriptions-item v-if="activity.notes" label="备注" :span="3">{{ activity.notes }}</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </template>
    </a-spin>

    <!-- 编辑弹窗 -->
    <a-modal v-model:open="editModalOpen" title="编辑骑行活动" @ok="saveEdit" width="600px">
      <a-form :model="editForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="活动名称" required><a-input v-model:value="editForm.title" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="日期"><a-date-picker v-model:value="editForm.date" valueFormat="YYYY-MM-DD" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="路线类型">
              <a-select v-model:value="editForm.route_type">
                <a-select-option value="公路">公路</a-select-option>
                <a-select-option value="山地">山地</a-select-option>
                <a-select-option value="砾石">砾石</a-select-option>
                <a-select-option value="室内">室内</a-select-option>
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
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { cyclingApi } from '@/api/index'
import TrackMap from '@/components/TrackMap.vue'
import { Chart, registerables } from 'chart.js'

Chart.register(...registerables)

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const activity = ref(null)
const trackPoints = ref([])
const elevationData = ref([])
const elevChartRef = ref(null)
let elevChart = null

// 编辑
const editModalOpen = ref(false)
const editForm = ref({ title: '', date: '', route_type: '', weather: '', notes: '' })

const metrics = computed(() => {
  if (!activity.value) return []
  const a = activity.value
  const items = [
    { label: '距离', value: a.distance_km || '-', unit: 'km' },
    { label: '时长', value: formatDuration(a.duration_sec), unit: '' },
    { label: '平均速度', value: a.avg_speed_kmh || '-', unit: 'km/h' },
    { label: '最高速度', value: a.max_speed_kmh || '-', unit: 'km/h' },
    { label: '累计爬升', value: a.elevation_gain || '-', unit: 'm' },
    { label: '累计下降', value: a.elevation_loss || '-', unit: 'm' },
  ]
  if (a.avg_power_w) items.push({ label: '平均功率', value: a.avg_power_w, unit: 'W' })
  if (a.tss) items.push({ label: 'TSS', value: a.tss, unit: '' })
  if (a.avg_heart_rate) items.push({ label: '平均心率', value: a.avg_heart_rate, unit: 'bpm' })
  if (a.avg_cadence) items.push({ label: '平均踏频', value: a.avg_cadence, unit: 'rpm' })
  return items
})

onMounted(async () => {
  try {
    const { data } = await cyclingApi.getActivity(route.params.id)
    activity.value = data
    if (data.track_json) {
      const pts = typeof data.track_json === 'string' ? JSON.parse(data.track_json) : data.track_json
      trackPoints.value = pts
      // 提取海拔数据
      elevationData.value = pts.filter(p => p.ele && p.ele > -400 && p.ele < 9000).map(p => +p.ele)
    }
    await nextTick()
    renderElevationChart()
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => { if (elevChart) { elevChart.destroy(); elevChart = null } })

function renderElevationChart() {
  if (!elevChartRef.value || !elevationData.value.length) return
  if (elevChart) elevChart.destroy()
  // 降采样到最多 200 点
  let data = elevationData.value
  if (data.length > 200) {
    const step = Math.ceil(data.length / 200)
    data = data.filter((_, i) => i % step === 0)
  }
  const labels = data.map((_, i) => i)
  elevChart = new Chart(elevChartRef.value, {
    type: 'line',
    data: {
      labels,
      datasets: [{
        label: '海拔 (m)',
        data,
        borderColor: '#667eea',
        backgroundColor: 'rgba(102,126,234,.15)',
        fill: true,
        tension: .3,
        pointRadius: 0,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { display: false },
        y: { grid: { color: '#f1f5f9' }, ticks: { font: { size: 10 } } }
      }
    }
  })
}

function showEditModal() {
  const a = activity.value
  editForm.value = {
    title: a.title,
    date: a.date,
    route_type: a.route_type || '',
    weather: a.weather || '',
    notes: a.notes || '',
  }
  editModalOpen.value = true
}

async function saveEdit() {
  if (!editForm.value.title) { message.warning('请填写活动名称'); return }
  try {
    await cyclingApi.updateActivity(activity.value.id, editForm.value)
    message.success('保存成功')
    editModalOpen.value = false
    // 刷新数据
    const { data } = await cyclingApi.getActivity(route.params.id)
    activity.value = data
  } catch (e) {
    message.error('保存失败')
  }
}

async function deleteActivity() {
  await cyclingApi.deleteActivity(activity.value.id)
  message.success('已删除')
  router.push('/sports/cycling/list')
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}
</script>

<style scoped>
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}
.metric-item {
  text-align: center;
  padding: 14px 8px;
  background: #f8f9ff;
  border-radius: 10px;
}
.metric-value {
  font-size: 22px;
  font-weight: 800;
  color: #667eea;
  line-height: 1;
}
.metric-label {
  font-size: 12px;
  color: #999;
  margin-top: 6px;
}
.metric-unit {
  font-size: 11px;
  color: #ccc;
}
.elevation-chart-wrap {
  height: 340px;
  position: relative;
}
</style>
