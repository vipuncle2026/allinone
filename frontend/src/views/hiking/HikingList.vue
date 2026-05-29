<template>
  <div>
    <!-- 统计概览 -->
    <a-row :gutter="16" style="margin-bottom: 20px">
      <a-col :span="4" v-for="card in statCards" :key="card.label">
        <a-card :bordered="false" size="small" class="stat-card" :style="{ background: card.bg }">
          <div style="color: rgba(255,255,255,0.85); font-size: 12px">{{ card.label }}</div>
          <div class="stat-value">{{ card.value }}</div>
          <div style="color: rgba(255,255,255,0.65); font-size: 11px">{{ card.unit }}</div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 运动成就 -->
    <a-card
      v-if="Object.keys(achievements).length"
      title="🏆 运动成就"
      :bordered="false"
      size="small"
      style="border-radius: 12px; margin-bottom: 20px"
    >
      <a-row :gutter="12">
        <a-col :span="6" v-for="(ach, key) in achievements" :key="key">
          <div class="achievement-card" @click="goDetail(ach.activity_id)">
            <div class="achievement-icon">{{ achievementIcons[key] }}</div>
            <div class="achievement-label">{{ achievementLabels[key] }}</div>
            <div class="achievement-value">{{ ach.value }} {{ ach.unit }}</div>
            <div class="achievement-meta">{{ ach.title }} · {{ ach.date }}</div>
            <div v-if="ach.note" class="achievement-note">{{ ach.note }}</div>
          </div>
        </a-col>
      </a-row>
    </a-card>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <a-input-search
        v-model:value="searchText"
        placeholder="搜索活动名称…"
        style="width: 200px"
        allow-clear
      />
      <a-range-picker
        v-model:value="dateRange"
        :placeholder="['开始日期', '结束日期']"
        format="YYYY-MM-DD"
        @change="loadList"
        style="width: 240px"
      />
      <a-select v-model:value="filterDifficulty" placeholder="难度筛选" allow-clear style="width: 140px" @change="loadList">
        <a-select-option value="简单">简单</a-select-option>
        <a-select-option value="中等">中等</a-select-option>
        <a-select-option value="困难">困难</a-select-option>
      </a-select>
      <div style="flex: 1"></div>
      <a-button @click="$router.push('/sports/hiking/upload')">+ 导入活动</a-button>
      <a-button type="primary" @click="showManualModal">手动录入</a-button>
      <a-dropdown>
        <a-button>导出活动</a-button>
        <template #overlay>
          <a-menu @click="onExportMenu">
            <a-menu-item key="json">JSON 备份</a-menu-item>
            <a-menu-item key="csv">CSV 文件</a-menu-item>
          </a-menu>
        </template>
      </a-dropdown>
    </div>

    <!-- 活动列表 -->
    <a-table
      :data-source="filteredActivities"
      :columns="columns"
      :loading="loading"
      :pagination="pagination"
      row-key="id"
      @change="onTableChange"
      :row-class-name="() => 'clickable-row'"
    >
      <template #emptyText>
        <a-result v-if="loadError" status="error" title="加载失败" :sub-title="loadError">
          <template #extra>
            <a-button type="primary" @click="loadList">重试</a-button>
          </template>
        </a-result>
        <a-empty v-else description="暂无徒步记录" />
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <a @click="goDetail(record.id)">{{ record.title }}</a>
        </template>
        <template v-if="column.key === 'distance_km'">
          <span style="font-weight: bold; color: #2d9a4e">{{ record.distance_km }}</span> km
        </template>
        <template v-if="column.key === 'duration_sec'">
          {{ formatDuration(record.duration_sec) }}
        </template>
        <template v-if="column.key === 'pace_min_km'">
          {{ record.pace_min_km ? formatPace(record.pace_min_km) : '-' }}
        </template>
        <template v-if="column.key === 'elevation_gain'">
          ↑ {{ record.elevation_gain || 0 }} m
        </template>
        <template v-if="column.key === 'max_elevation'">
          {{ record.max_elevation ? record.max_elevation + ' m' : '-' }}
        </template>
        <template v-if="column.key === 'calories'">
          {{ record.calories ? record.calories + ' kcal' : '-' }}
        </template>
        <template v-if="column.key === 'avg_heart_rate'">
          {{ record.avg_heart_rate ? record.avg_heart_rate + ' bpm' : '-' }}
        </template>
        <template v-if="column.key === 'max_speed_kmh'">
          <span v-if="record.max_speed_kmh" style="color: #e11d48; font-weight: 600">{{ record.max_speed_kmh }} km/h</span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'avg_cadence'">
          {{ record.avg_cadence ? record.avg_cadence + ' spm' : '-' }}
        </template>
        <template v-if="column.key === 'difficulty'">
          <a-tag :color="difficultyColor(record.difficulty)">{{ record.difficulty || '-' }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click.stop="showEditModal(record)">编辑</a-button>
            <a-popconfirm title="确认删除？" @confirm="deleteActivity(record.id)">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 手动录入弹窗 -->
    <a-modal v-model:open="manualModalOpen" title="手动录入徒步活动" @ok="saveManual" width="600px">
      <a-form :model="manualForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="活动名称" required><a-input v-model:value="manualForm.title" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="日期" required><a-date-picker v-model:value="manualForm.date" valueFormat="YYYY-MM-DD" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="距离 (km)"><a-input-number v-model:value="manualForm.distance_km" :min="0" :precision="2" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="时长 (分钟)"><a-input-number v-model:value="manualForm.duration_min" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="热量 (kcal)"><a-input-number v-model:value="manualForm.calories" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="累计爬升 (m)"><a-input-number v-model:value="manualForm.elevation_gain" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="最高海拔 (m)"><a-input-number v-model:value="manualForm.max_elevation" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="均速 (km/h)"><a-input-number v-model:value="manualForm.avg_speed_kmh" :min="0" :precision="1" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="难度">
              <a-select v-model:value="manualForm.difficulty" allow-clear>
                <a-select-option value="简单">简单</a-select-option>
                <a-select-option value="中等">中等</a-select-option>
                <a-select-option value="困难">困难</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="步数"><a-input-number v-model:value="manualForm.steps" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="天气"><a-input v-model:value="manualForm.weather" placeholder="晴/多云/雨…" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="路线名称"><a-input v-model:value="manualForm.trail_name" placeholder="例如：武功山登山路线" /></a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="manualForm.notes" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>

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
          <a-col :span="8">
            <a-form-item label="难度">
              <a-select v-model:value="editForm.difficulty" allow-clear>
                <a-select-option value="简单">简单</a-select-option>
                <a-select-option value="中等">中等</a-select-option>
                <a-select-option value="困难">困难</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="天气"><a-input v-model:value="editForm.weather" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="路线名称"><a-input v-model:value="editForm.trail_name" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model:value="editForm.notes" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { hikingApi } from '@/api/index'

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const activities = ref([])
const stats = ref({ total_activities: 0, total_km: 0, total_hours: 0, total_elevation_gain: 0, total_calories: 0 })
const achievements = ref({})
const searchText = ref('')
const dateRange = ref(null)
const filterDifficulty = ref(null)
const pagination = ref({ current: 1, pageSize: 20, total: 0 })

// 手动录入弹窗
const manualModalOpen = ref(false)
const manualForm = ref({
  title: '', date: '', distance_km: null, duration_min: null, calories: null,
  elevation_gain: null, max_elevation: null, avg_speed_kmh: null, difficulty: null,
  steps: null, weather: '', trail_name: '', notes: '',
})

// 编辑弹窗
const editModalOpen = ref(false)
const editingId = ref(null)
const editForm = ref({ title: '', date: '', difficulty: '', weather: '', trail_name: '', notes: '' })

const achievementIcons = {
  longest_distance: '📏',
  longest_duration: '⏱️',
  fastest_10km: '🏃',
  highest_elevation: '⛰️',
}

const achievementLabels = {
  longest_distance: '单次最长距离',
  longest_duration: '单次最长时间',
  fastest_10km: '10km 最快配速',
  highest_elevation: '最高海拔',
}

const statCards = computed(() => [
  { label: '总次数', value: stats.value.total_activities, unit: '次', bg: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' },
  { label: '总距离', value: stats.value.total_km, unit: '公里', bg: 'linear-gradient(135deg, #2d9a4e 0%, #52c41a 100%)' },
  { label: '总时长', value: stats.value.total_hours, unit: '小时', bg: 'linear-gradient(135deg, #1890ff 0%, #36cfc9 100%)' },
  { label: '总爬升', value: stats.value.total_elevation_gain, unit: '米', bg: 'linear-gradient(135deg, #fa8c16 0%, #fadb14 100%)' },
  { label: '总热量', value: stats.value.total_calories, unit: 'kcal', bg: 'linear-gradient(135deg, #f5222d 0%, #ff7a45 100%)' },
  { label: '平均距离', value: stats.value.total_activities ? round(stats.value.total_km / stats.value.total_activities, 1) : 0, unit: '公里/次', bg: 'linear-gradient(135deg, #722ed1 0%, #eb2f96 100%)' },
])

const columns = [
  { title: '活动名称', key: 'title', dataIndex: 'title', width: 180 },
  { title: '日期', key: 'date', dataIndex: 'date', width: 110, sorter: (a, b) => a.date.localeCompare(b.date) },
  { title: '距离', key: 'distance_km', dataIndex: 'distance_km', width: 100, sorter: (a, b) => (a.distance_km || 0) - (b.distance_km || 0) },
  { title: '时长', key: 'duration_sec', dataIndex: 'duration_sec', width: 90 },
  { title: '配速', key: 'pace_min_km', dataIndex: 'pace_min_km', width: 90 },
  { title: '爬升', key: 'elevation_gain', dataIndex: 'elevation_gain', width: 80 },
  { title: '最高海拔', key: 'max_elevation', dataIndex: 'max_elevation', width: 100 },
  { title: '热量', key: 'calories', dataIndex: 'calories', width: 90 },
  { title: '均心率', key: 'avg_heart_rate', dataIndex: 'avg_heart_rate', width: 85 },
  { title: '最大速度', key: 'max_speed_kmh', dataIndex: 'max_speed_kmh', width: 95 },
  { title: '平均步频', key: 'avg_cadence', dataIndex: 'avg_cadence', width: 90 },
  { title: '难度', key: 'difficulty', dataIndex: 'difficulty', width: 75 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

const filteredActivities = computed(() => {
  if (!searchText.value) return activities.value
  const q = searchText.value.toLowerCase()
  return activities.value.filter(a =>
    (a.title || '').toLowerCase().includes(q) ||
    (a.date || '').includes(q) ||
    (a.trail_name || '').toLowerCase().includes(q)
  )
})

function round(v, d = 1) {
  return Number(v).toFixed(d)
}

// ─── 导出 ───

function _downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function onExportMenu({ key }) {
  try {
    if (key === 'json') {
      const { data: blob } = await hikingApi.exportBackup()
      _downloadBlob(blob, `hiking_backup_${new Date().toISOString().slice(0, 10)}.json`)
    } else if (key === 'csv') {
      const { data: blob } = await hikingApi.exportCsv()
      _downloadBlob(blob, `hiking_activities_${new Date().toISOString().slice(0, 10)}.csv`)
    }
  } catch { message.error('导出失败') }
}

onMounted(async () => {
  await Promise.all([loadList(), loadStats(), loadAchievements()])
})

async function loadList() {
  loading.value = true
  loadError.value = ''
  try {
    const params = {
      page: pagination.value.current,
      limit: pagination.value.pageSize,
      difficulty: filterDifficulty.value || undefined,
    }
    const { data } = await hikingApi.listActivities(params)
    activities.value = data.items
    pagination.value.total = data.total
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '网络异常，请检查服务是否正常'
    loadError.value = msg
    message.error('加载失败：' + msg)
  } finally {
    loading.value = false
  }
}

async function loadStats() {
  try {
    const { data } = await hikingApi.getStats()
    stats.value = data
  } catch (e) {}
}

async function loadAchievements() {
  try {
    const { data } = await hikingApi.getAchievements()
    achievements.value = data
  } catch (e) {}
}

async function deleteActivity(id) {
  await hikingApi.deleteActivity(id)
  message.success('已删除')
  loadList()
  loadStats()
  loadAchievements()
}

function goDetail(id) {
  router.push(`/sports/hiking/detail/${id}`)
}

function onTableChange(pag) {
  pagination.value.current = pag.current
  loadList()
}

function difficultyColor(d) {
  return { '简单': 'green', '中等': 'orange', '困难': 'red' }[d] || 'default'
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function formatPace(minPerKm) {
  const m = Math.floor(minPerKm)
  const s = Math.round((minPerKm - m) * 60)
  return `${m}'${s.toString().padStart(2, '0')}"`
}

function showManualModal() {
  manualForm.value = {
    title: '', date: '', distance_km: null, duration_min: null, calories: null,
    elevation_gain: null, max_elevation: null, avg_speed_kmh: null, difficulty: null,
    steps: null, weather: '', trail_name: '', notes: '',
  }
  manualModalOpen.value = true
}

async function saveManual() {
  if (!manualForm.value.title || !manualForm.value.date) {
    message.warning('请填写活动名称和日期')
    return
  }
  try {
    const payload = {
      ...manualForm.value,
      duration_sec: manualForm.value.duration_min ? manualForm.value.duration_min * 60 : null,
    }
    delete payload.duration_min
    await hikingApi.createManual(payload)
    message.success('录入成功')
    manualModalOpen.value = false
    loadList()
    loadStats()
    loadAchievements()
  } catch (e) {
    message.error('保存失败')
  }
}

function showEditModal(record) {
  editingId.value = record.id
  editForm.value = {
    title: record.title,
    date: record.date,
    difficulty: record.difficulty || '',
    weather: record.weather || '',
    trail_name: record.trail_name || '',
    notes: record.notes || '',
  }
  editModalOpen.value = true
}

async function saveEdit() {
  if (!editForm.value.title) { message.warning('请填写活动名称'); return }
  try {
    await hikingApi.updateActivity(editingId.value, editForm.value)
    message.success('保存成功')
    editModalOpen.value = false
    loadList()
  } catch (e) {
    message.error('保存失败')
  }
}
</script>

<style scoped>
.stat-card {
  border-radius: 10px;
  text-align: center;
  color: #fff;
  transition: transform 0.2s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15); }
.stat-value { font-size: 22px; font-weight: bold; color: #fff; margin-top: 4px; }
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #f0fff4 !important; }

.achievement-card {
  background: linear-gradient(135deg, #f6ffed 0%, #e6fffb 100%);
  border-radius: 10px;
  padding: 16px;
  text-align: center;
  cursor: pointer;
  transition: transform 0.2s;
  border: 1px solid #d9f7be;
}
.achievement-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(45, 154, 78, 0.15); }
.achievement-icon { font-size: 28px; margin-bottom: 4px; }
.achievement-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.achievement-value { font-size: 20px; font-weight: bold; color: #2d9a4e; }
.achievement-meta { font-size: 11px; color: #999; margin-top: 4px; }
.achievement-note { font-size: 10px; color: #bbb; margin-top: 2px; }
</style>
