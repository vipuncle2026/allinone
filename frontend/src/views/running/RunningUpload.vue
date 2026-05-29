<template>
  <div>
    <!-- 上传区域 -->
    <a-card title="导入跑步活动" :bordered="false" style="border-radius: 12px; margin-bottom: 24px">
      <a-upload-dragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        accept=".gpx,.fit,.tcx"
        :disabled="uploading"
        style="margin-bottom: 16px"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined style="font-size: 48px; color: #f97316" />
        </p>
        <p class="ant-upload-text">点击或拖拽 GPX / FIT / TCX 文件到此处</p>
        <p class="ant-upload-hint">支持 Garmin、佳明、Keep、悦跑圈等设备/APP 导出的轨迹文件</p>
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
          <a-col :span="8">
            <a-form-item label="日期" required>
              <a-date-picker v-model:value="form.date" valueFormat="YYYY-MM-DD" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="活动名称" required>
              <a-input v-model:value="form.title" size="large" placeholder="请输入活动名称" />
            </a-form-item>
          </a-col>
          <a-col :span="4">
            <a-form-item label="跑步路线">
              <a-input v-model:value="form.running_route" placeholder="CBD 环线" />
            </a-form-item>
          </a-col>
          <a-col :span="4">
            <a-form-item label="天气">
              <a-input v-model:value="form.weather" placeholder="晴/多云/雨" />
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
          <a-descriptions-item label="爬升" v-if="parsed.elevation_gain">
            <span class="stat-value">{{ parsed.elevation_gain }}</span> m
          </a-descriptions-item>
          <a-descriptions-item label="下降" v-if="parsed.elevation_loss">
            <span class="stat-value">{{ parsed.elevation_loss }}</span> m
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_heart_rate" label="均心率">
            <span class="stat-value">{{ parsed.avg_heart_rate }}</span> bpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.max_heart_rate" label="最大心率">
            <span class="stat-value">{{ parsed.max_heart_rate }}</span> bpm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.avg_cadence" label="平均步频">
            <span class="stat-value">{{ parsed.avg_cadence }}</span> spm
          </a-descriptions-item>
          <a-descriptions-item v-if="parsed.calories" label="热量">
            <span class="stat-value">{{ parsed.calories }}</span> kcal
          </a-descriptions-item>
        </a-descriptions>

        <a-form-item label="备注"><a-textarea v-model:value="form.notes" :rows="2" placeholder="可选…" /></a-form-item>

        <a-button type="primary" size="large" :loading="saving" @click="saveActivity">保存活动</a-button>
      </a-form>
    </a-card>

    <!-- 轨迹地图 -->
    <a-card v-if="mapPoints.length" title="🗺️ 轨迹预览" :bordered="false" style="border-radius: 12px; margin-bottom: 24px">
      <TrackMap :track-points="mapPoints" :show-tile-bar="true" style="height: 400px; border-radius: 8px" />
    </a-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import { runningApi, invalidateCache } from '@/api/index'
import TrackMap from '@/components/TrackMap.vue'

const router = useRouter()
const uploading = ref(false)
const saving = ref(false)
const parsed = ref(null)
const mapPoints = ref([])
const form = ref({ title: '', date: '', running_route: '', weather: '', notes: '' })

async function beforeUpload(file) {
  uploading.value = true
  parsed.value = null
  mapPoints.value = []
  form.value.date = ''
  try {
    const res = await runningApi.upload(file)
    parsed.value = res.data
    form.value.title = res.data.suggested_title || ''
    // 自动填充日期（后端已从 start_time 推导）
    form.value.date = res.data.date || ''
    // 提取地图轨迹
    if (res.data.track_json) {
      try {
        const track = JSON.parse(res.data.track_json)
        mapPoints.value = track.map || []
      } catch {}
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '文件解析失败')
  } finally {
    uploading.value = false
  }
  return false
}

async function saveActivity() {
  if (!form.value.title) { message.warning('请填写活动名称'); return }
  if (!form.value.date) { message.warning('请选择日期'); return }
  saving.value = true
  try {
    const payload = { ...parsed.value, ...form.value }
    // 清理不在 Schema 中的多余字段
    const allowed = new Set([
      'title', 'date', 'start_time', 'end_time', 'distance_km', 'duration_sec',
      'elevation_gain', 'elevation_loss', 'max_elevation', 'min_elevation',
      'avg_speed_kmh', 'max_speed_kmh', 'pace_min_km',
      'avg_heart_rate', 'max_heart_rate', 'calories',
      'avg_cadence', 'max_cadence', 'steps',
      'running_route', 'weather', 'notes',
      'file_type', 'file_path', 'track_json',
    ])
    Object.keys(payload).forEach(k => { if (!allowed.has(k)) delete payload[k] })
    await runningApi.saveActivity(payload)
    // 清除看板缓存，确保回看板时能显示新数据
    invalidateCache('/dashboard')
    message.success('保存成功')
    router.push({ name: 'running-list' })
  } catch (e) {
    const detail = e.response?.data?.detail
    message.error(detail ? `保存失败：${detail}` : '保存失败')
  } finally {
    saving.value = false
  }
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m ${s}s`
  return `${m}m ${s}s`
}

function formatPace(minPerKm) {
  const m = Math.floor(minPerKm)
  const s = Math.round((minPerKm - m) * 60)
  return `${m}'${s.toString().padStart(2, '0')}"`
}
</script>

<style scoped>
.stat-value { color: #f97316; font-weight: 600; font-size: 15px; }
</style>
