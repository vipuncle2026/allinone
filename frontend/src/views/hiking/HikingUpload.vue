<template>
  <div>
    <!-- 上传区域 -->
    <a-card title="导入徒步活动" :bordered="false" style="border-radius: 12px; margin-bottom: 24px">
      <a-upload-dragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        accept=".gpx,.fit,.tcx"
        :disabled="uploading"
        style="margin-bottom: 16px"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined style="font-size: 48px; color: #2d9a4e" />
        </p>
        <p class="ant-upload-text">点击或拖拽 GPX / FIT / TCX 文件到此处</p>
        <p class="ant-upload-hint">支持 Garmin、两步路、六只脚等设备/APP 导出的轨迹文件</p>
      </a-upload-dragger>
      <a-spin v-if="uploading" tip="正在解析文件..." />
    </a-card>

    <!-- 解析预览 -->
    <a-card
      v-if="parsed"
      title="📊 活动预览"
      :bordered="false"
      style="border-radius: 12px; margin-bottom: 24px"
    >
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="活动名称" required>
              <a-input v-model:value="form.title" size="large" placeholder="请输入活动名称" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="难度">
              <a-select v-model:value="form.difficulty" placeholder="请选择">
                <a-select-option value="简单">简单</a-select-option>
                <a-select-option value="中等">中等</a-select-option>
                <a-select-option value="困难">困难</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="天气">
              <a-input v-model:value="form.weather" placeholder="晴/多云/雨…" />
            </a-form-item>
          </a-col>
        </a-row>

        <!-- 核心指标展示 -->
        <a-descriptions :column="4" bordered size="small" style="margin-bottom: 16px">
          <a-descriptions-item label="距离">
            <span class="stat-value">{{ parsed.distance_km }}</span> km
          </a-descriptions-item>
          <a-descriptions-item label="时长">
            <span class="stat-value">{{ formatDuration(parsed.duration_sec) }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="均速">
            <span class="stat-value">{{ parsed.avg_speed_kmh }}</span> km/h
          </a-descriptions-item>
          <a-descriptions-item label="配速">
            <span class="stat-value">{{ parsed.pace_min_km ? formatPace(parsed.pace_min_km) : '-' }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="爬升">
            <span class="stat-value">{{ parsed.elevation_gain }}</span> m
          </a-descriptions-item>
          <a-descriptions-item label="下降">
            <span class="stat-value">{{ parsed.elevation_loss }}</span> m
          </a-descriptions-item>
          <a-descriptions-item label="最高海拔">
            <span class="stat-value">{{ parsed.max_elevation || '-' }}</span>
            <span v-if="parsed.max_elevation"> m</span>
          </a-descriptions-item>
          <a-descriptions-item label="最低海拔">
            <span class="stat-value">{{ parsed.min_elevation || '-' }}</span>
            <span v-if="parsed.min_elevation"> m</span>
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_heart_rate" label="均心率">
            <span class="stat-value">{{ parsed.avg_heart_rate }}</span> bpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.max_heart_rate" label="最高心率">
            <span class="stat-value">{{ parsed.max_heart_rate }}</span> bpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.max_speed_kmh" label="最快速度">
            <span class="stat-value">{{ parsed.max_speed_kmh }}</span> km/h
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_cadence" label="平均步频">
            <span class="stat-value">{{ parsed.avg_cadence }}</span> spm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.max_cadence" label="最高步频">
            <span class="stat-value">{{ parsed.max_cadence }}</span> spm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.calories" label="热量消耗">
            <span class="stat-value">{{ parsed.calories }}</span> kcal
          </a-descriptions-item>
        </a-descriptions>

        <!-- 地图 -->
        <TrackMap
          v-if="trackPoints.length"
          :track-points="trackPoints"
          style="height: 360px; border-radius: 8px; overflow: hidden; margin-bottom: 16px"
        />

        <a-form-item label="路线名称">
          <a-input v-model:value="form.trail_name" placeholder="例如：武功山登山路线" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="form.notes" :rows="3" placeholder="添加备注（可选）" />
        </a-form-item>

        <a-button type="primary" size="large" :loading="saving" @click="saveActivity" style="background: #2d9a4e; border-color: #2d9a4e">
          💾 保存活动
        </a-button>
        <a-button style="margin-left: 12px" @click="resetForm">重新上传</a-button>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { hikingApi } from '@/api/index'
import TrackMap from '@/components/TrackMap.vue'

const router = useRouter()

const uploading = ref(false)
const saving = ref(false)
const parsed = ref(null)
const trackPoints = ref([])

const form = ref({
  title: '',
  date: '',
  difficulty: '',
  weather: '',
  trail_name: '',
  notes: '',
})

async function beforeUpload(file) {
  uploading.value = true
  parsed.value = null
  trackPoints.value = []

  try {
    const { data } = await hikingApi.upload(file)
    parsed.value = data

    form.value.title = data.suggested_title || '徒步活动'
    form.value.date = data.start_time
      ? dayjs(data.start_time).format('YYYY-MM-DD')
      : dayjs().format('YYYY-MM-DD')

    if (data.track_json) {
      try {
        const tj = typeof data.track_json === 'string' ? JSON.parse(data.track_json) : data.track_json
        // 新格式：{ map: [...], chart: [...] }；旧格式：直接是数组
        trackPoints.value = Array.isArray(tj) ? tj : (tj.map || [])
      } catch (e) {}
    } else if (data.track_points) {
      trackPoints.value = data.track_points
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '文件解析失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
  return false
}

async function saveActivity() {
  if (!form.value.title) {
    message.warning('请填写活动名称')
    return
  }
  if (!form.value.date) {
    message.warning('日期解析失败，请检查文件')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form.value,
      distance_km: parsed.value.distance_km,
      duration_sec: parsed.value.duration_sec,
      elevation_gain: parsed.value.elevation_gain,
      elevation_loss: parsed.value.elevation_loss,
      max_elevation: parsed.value.max_elevation,
      min_elevation: parsed.value.min_elevation,
      avg_speed_kmh: parsed.value.avg_speed_kmh,
      max_speed_kmh: parsed.value.max_speed_kmh,
      pace_min_km: parsed.value.pace_min_km,
      avg_heart_rate: parsed.value.avg_heart_rate,
      max_heart_rate: parsed.value.max_heart_rate,
      calories: parsed.value.calories,
      avg_cadence: parsed.value.avg_cadence,
      max_cadence: parsed.value.max_cadence,
      start_time: parsed.value.start_time || null,
      end_time: parsed.value.end_time || null,
      file_type: parsed.value.file_type,
      file_path: parsed.value.file_path,
      track_json: parsed.value.track_json || null,
    }
    await hikingApi.saveActivity(payload)
    message.success('活动保存成功！')
    router.push('/sports/hiking/list')
  } catch (e) {
    const detail = e.response?.data?.detail
    const msg = Array.isArray(detail)
      ? detail.map(d => d.msg).join('; ')
      : (detail || '保存失败，请检查数据')
    message.error(msg)
  } finally {
    saving.value = false
  }
}

function resetForm() {
  parsed.value = null
  trackPoints.value = []
  form.value = { title: '', date: '', difficulty: '', weather: '', trail_name: '', notes: '' }
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

function formatPace(minPerKm) {
  if (!minPerKm) return '-'
  const m = Math.floor(minPerKm)
  const s = Math.round((minPerKm - m) * 60)
  return `${m}'${s.toString().padStart(2, '0')}"`
}
</script>

<style scoped>
.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #2d9a4e;
}
</style>
