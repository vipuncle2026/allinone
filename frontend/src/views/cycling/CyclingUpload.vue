<template>
  <div>
    <!-- 上传区域 -->
    <a-card title="上传骑行活动" :bordered="false" style="border-radius: 12px; margin-bottom: 24px">
      <a-upload-dragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        accept=".gpx,.fit"
        :disabled="uploading"
        style="margin-bottom: 16px"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined style="font-size: 48px; color: #667eea" />
        </p>
        <p class="ant-upload-text">点击或拖拽 GPX / FIT 文件到此处</p>
        <p class="ant-upload-hint">支持 Garmin、Wahoo、Strava 等设备导出的文件格式</p>
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
      <!-- 标题与基础信息编辑 -->
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="活动名称" required>
              <a-input v-model:value="form.title" size="large" placeholder="请输入活动名称" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="路线类型">
              <a-select v-model:value="form.route_type" placeholder="请选择">
                <a-select-option value="公路">公路</a-select-option>
                <a-select-option value="山地">山地</a-select-option>
                <a-select-option value="砾石">砾石</a-select-option>
                <a-select-option value="室内">室内</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="关联车辆">
              <a-select v-model:value="form.bike_id" placeholder="请选择" allow-clear>
                <a-select-option v-for="b in bikes" :key="b.id" :value="b.id">
                  {{ b.name }}
                </a-select-option>
              </a-select>
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
          <a-descriptions-item label="最高速">
            <span class="stat-value">{{ parsed.max_speed_kmh || '-' }}</span>
            <span v-if="parsed.max_speed_kmh"> km/h</span>
          </a-descriptions-item>
          <a-descriptions-item label="爬升">
            <span class="stat-value">{{ parsed.elevation_gain }}</span> m
          </a-descriptions-item>
          <a-descriptions-item label="下降">
            <span class="stat-value">{{ parsed.elevation_loss }}</span> m
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_power_w" label="均功率">
            <span class="stat-value">{{ parsed.avg_power_w }}</span> W
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.normalized_power" label="NP">
            <span class="stat-value">{{ parsed.normalized_power }}</span> W
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_heart_rate" label="均心率">
            <span class="stat-value">{{ parsed.avg_heart_rate }}</span> bpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.max_heart_rate" label="最高心率">
            <span class="stat-value">{{ parsed.max_heart_rate }}</span> bpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_cadence" label="均踏频">
            <span class="stat-value">{{ parsed.avg_cadence }}</span> rpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.tss" label="TSS">
            <span class="stat-value">{{ displayedTss }}</span>
            <a-input-number
              v-if="parsed.avg_power_w"
              v-model:value="form.ftp"
              size="small"
              :min="50"
              :max="500"
              :step="5"
              addon-after="W"
              style="width: 120px; margin-left: 8px; font-size: 12px"
              @change="recalcTss"
            />
          </a-descriptions-item>
        </a-descriptions>

        <!-- 地图 -->
        <TrackMap
          v-if="trackPoints.length"
          :track-points="trackPoints"
          style="height: 360px; border-radius: 8px; overflow: hidden; margin-bottom: 16px"
        />

        <a-form-item label="备注">
          <a-textarea v-model:value="form.notes" :rows="3" placeholder="添加备注（可选）" />
        </a-form-item>

        <a-button type="primary" size="large" :loading="saving" @click="saveActivity">
          💾 保存活动
        </a-button>
        <a-button style="margin-left: 12px" @click="resetForm">重新上传</a-button>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { cyclingApi } from '@/api/index'
import TrackMap from '@/components/TrackMap.vue'

const router = useRouter()

const uploading = ref(false)
const saving = ref(false)
const parsed = ref(null)
const trackPoints = ref([])
const bikes = ref([])
const displayedTss = ref(null)

const form = ref({
  title: '',
  date: '',
  route_type: '公路',
  bike_id: null,
  notes: '',
  ftp: 200,
})

// 用用户指定的 FTP 重新计算 TSS
function recalcTss() {
  const np = parsed.value?.normalized_power || parsed.value?.avg_power_w
  const duration = parsed.value?.duration_sec
  const ftp = form.value.ftp || 200
  if (np && duration) {
    const intensity_factor = np / ftp
    const tss = (duration * np * intensity_factor) / (ftp * 3600) * 100
    displayedTss.value = Math.round(tss * 10) / 10
  }
}

onMounted(async () => {
  try {
    const [bikesRes, defaultsRes] = await Promise.all([
      cyclingApi.listBikes(),
      cyclingApi.getDefaults(),
    ])
    bikes.value = bikesRes.data
    form.value.ftp = defaultsRes.data.default_ftp || 200
  } catch (e) {}
})

async function beforeUpload(file) {
  uploading.value = true
  parsed.value = null
  trackPoints.value = []

  try {
    const { data } = await cyclingApi.upload(file)
    parsed.value = data

    // 初始化表单
    form.value.title = data.suggested_title || '骑行活动'
    form.value.date = data.start_time
      ? dayjs(data.start_time).format('YYYY-MM-DD')
      : dayjs().format('YYYY-MM-DD')
    form.value.ftp = 200  // 每次上传重置 FTP
    displayedTss.value = data.tss  // 解析时默认 200W 的 TSS

    // 解析轨迹点（可能是 JSON 字符串）
    if (data.track_json) {
      try {
        trackPoints.value = typeof data.track_json === 'string'
          ? JSON.parse(data.track_json)
          : data.track_json
      } catch (e) {}
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '文件解析失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
  return false // 阻止默认上传
}

async function saveActivity() {
  if (!form.value.title) {
    message.warning('请填写活动名称')
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
      avg_power_w: parsed.value.avg_power_w,
      max_power_w: parsed.value.max_power_w,
      normalized_power: parsed.value.normalized_power,
      tss: displayedTss.value ?? parsed.value.tss,
      ftp: form.value.ftp,
      avg_heart_rate: parsed.value.avg_heart_rate,
      max_heart_rate: parsed.value.max_heart_rate,
      avg_cadence: parsed.value.avg_cadence,
      max_cadence: parsed.value.max_cadence,
      calories: parsed.value.calories,
      start_time: parsed.value.start_time,
      end_time: parsed.value.end_time,
      file_type: parsed.value.file_type,
      file_path: parsed.value.file_path,
      track_json: parsed.value.track_json,
    }
    await cyclingApi.saveActivity(payload)
    message.success('活动保存成功！')
    router.push('/sports/cycling/list')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

function resetForm() {
  parsed.value = null
  trackPoints.value = []
  form.value = { title: '', date: '', route_type: '公路', bike_id: null, notes: '', ftp: 200 }
  displayedTss.value = null
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}
</script>

<style scoped>
.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #667eea;
}
</style>
