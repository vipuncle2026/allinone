<template>
  <div>
    <a-spin v-if="loading" style="display:block;text-align:center;padding:60px" />
    <template v-else-if="activity">
      <!-- 顶部信息卡 -->
      <a-row :gutter="16" style="margin-bottom: 20px">
        <a-col :span="24">
          <a-card :bordered="false" style="border-radius: 12px; background: linear-gradient(135deg, #7c2d12, #9a3412); color: #fff">
            <div style="display: flex; justify-content: space-between; align-items: flex-start">
              <div>
                <div style="font-size: 13px; color: #fed7aa; margin-bottom: 4px">{{ activity.date }} {{ activity.running_route || '' }}</div>
                <div style="font-size: 22px; font-weight: 700">{{ activity.title }}</div>
                <div v-if="activity.weather" style="font-size: 12px; color: #fed7aa; margin-top: 4px">天气：{{ activity.weather }}</div>
              </div>
              <a-space>
                <a-button size="small" @click="goBack">返回</a-button>
                <a-button type="primary" danger size="small" @click="confirmDelete">删除</a-button>
              </a-space>
            </div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 核心数据 -->
      <a-row :gutter="16" style="margin-bottom: 20px">
        <a-col :span="4" v-for="kpi in kpiData" :key="kpi.label" style="margin-bottom: 12px">
          <a-card :bordered="false" size="small" class="kpi-card" :style="{ background: kpi.bg }">
            <div style="font-size: 12px; color: rgba(255,255,255,.75)">{{ kpi.label }}</div>
            <div style="font-size: 22px; font-weight: 700; color: #fff; margin-top: 2px">{{ kpi.value }}</div>
            <div style="font-size: 11px; color: rgba(255,255,255,.6)">{{ kpi.unit }}</div>
          </a-card>
        </a-col>
      </a-row>

      <!-- 轨迹地图 -->
      <a-card v-if="mapPoints.length" title="🗺️ 轨迹" :bordered="false" style="border-radius: 12px; margin-bottom: 20px">
        <TrackMap :track-points="mapPoints" :show-tile-bar="true" style="height: 400px; border-radius: 8px" />
      </a-card>
      <a-card v-else-if="activity" title="🗺️ 轨迹" :bordered="false" style="border-radius: 12px; margin-bottom: 20px">
        <div style="height: 200px; display: flex; align-items: center; justify-content: center; color: #999">
          暂无轨迹数据
        </div>
      </a-card>

      <!-- 详情备注 -->
      <a-card title="详细信息" :bordered="false" style="border-radius: 12px" v-if="activity.notes || hasDetails">
        <a-descriptions :column="2" bordered size="small">
          <a-descriptions-item v-if="activity.running_route" label="跑步路线">{{ activity.running_route }}</a-descriptions-item>
          <a-descriptions-item v-if="activity.max_elevation" label="最高海拔">{{ activity.max_elevation }} m</a-descriptions-item>
          <a-descriptions-item v-if="activity.min_elevation" label="最低海拔">{{ activity.min_elevation }} m</a-descriptions-item>
          <a-descriptions-item v-if="activity.max_speed_kmh" label="最大速度">{{ activity.max_speed_kmh }} km/h</a-descriptions-item>
          <a-descriptions-item v-if="activity.max_heart_rate" label="最大心率">{{ activity.max_heart_rate }} bpm</a-descriptions-item>
          <a-descriptions-item v-if="activity.max_cadence" label="最大步频">{{ activity.max_cadence }} spm</a-descriptions-item>
          <a-descriptions-item v-if="activity.steps" label="步数">{{ (activity.steps || 0).toLocaleString() }} 步</a-descriptions-item>
        </a-descriptions>
        <div v-if="activity.notes" style="margin-top: 16px">
          <div style="font-size: 12px; color: #999; margin-bottom: 6px">备注</div>
          <div style="background: #fafafa; border-radius: 8px; padding: 12px; color: #333">{{ activity.notes }}</div>
        </div>
      </a-card>
    </template>
    <a-empty v-else description="活动不存在" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import { runningApi } from '@/api/index'
import TrackMap from '@/components/TrackMap.vue'

const router = useRouter()
const route = useRoute()
const loading = ref(true)
const activity = ref(null)
const mapPoints = ref([])

const hasDetails = computed(() =>
  activity.value &&
  (activity.value.max_elevation || activity.value.min_elevation ||
   activity.value.max_speed_kmh || activity.value.max_heart_rate ||
   activity.value.max_cadence || activity.value.steps)
)

const kpiData = computed(() => {
  if (!activity.value) return []
  const a = activity.value
  return [
    { label: '距离', value: a.distance_km || '-', unit: 'km', bg: 'linear-gradient(135deg, #ea580c, #f97316)' },
    { label: '时长', value: fmtDur(a.duration_sec), unit: '', bg: 'linear-gradient(135deg, #c2410c, #ea580c)' },
    { label: '配速', value: a.pace_min_km ? fmtPace(a.pace_min_km) : '-', unit: 'min/km', bg: 'linear-gradient(135deg, #b45309, #d97706)' },
    { label: '爬升', value: a.elevation_gain || '-', unit: 'm', bg: 'linear-gradient(135deg, #92400e, #b45309)' },
    { label: '均速', value: a.avg_speed_kmh || '-', unit: 'km/h', bg: 'linear-gradient(135deg, #dc2626, #f87171)' },
    { label: '热量', value: a.calories || '-', unit: 'kcal', bg: 'linear-gradient(135deg, #7c3aed, #a78bfa)' },
    { label: '均心率', value: a.avg_heart_rate || '-', unit: 'bpm', bg: 'linear-gradient(135deg, #be123c, #e11d48)' },
    { label: '步频', value: a.avg_cadence || '-', unit: 'spm', bg: 'linear-gradient(135deg, #0891b2, #06b6d4)' },
  ]
})

function fmtDur(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  return `${m}m ${s}s`
}

function fmtPace(minPerKm) {
  const m = Math.floor(minPerKm)
  const s = Math.round((minPerKm - m) * 60)
  return `${m}'${s.toString().padStart(2, '0')}"`
}

onMounted(async () => {
  try {
    const { data } = await runningApi.getActivity(route.params.id)
    activity.value = data
    if (data.track_json) {
      try {
        const track = JSON.parse(data.track_json)
        mapPoints.value = track.map || []
      } catch {}
    }
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
})

function goBack() { router.back() }

async function confirmDelete() {
  Modal.confirm({
    title: '确认删除？', content: '此操作不可恢复',
    okText: '删除', okType: 'danger',
    async onOk() {
      await runningApi.deleteActivity(route.params.id)
      message.success('已删除')
      router.push({ name: 'running-list' })
    }
  })
}
</script>

<style scoped>
.kpi-card { border-radius: 10px; text-align: center; color: #fff; }
</style>
