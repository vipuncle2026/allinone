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
      <div style="flex: 1"></div>
      <a-button @click="$router.push({ name: 'running-upload' })">+ 导入活动</a-button>
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
        <a-empty v-else description="暂无跑步记录" />
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <a @click="goDetail(record.id)">{{ record.title }}</a>
        </template>
        <template v-if="column.key === 'distance_km'">
          <span style="font-weight: bold; color: #f97316">{{ record.distance_km }}</span> km
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
        <template v-if="column.key === 'calories'">
          {{ record.calories ? record.calories + ' kcal' : '-' }}
        </template>
        <template v-if="column.key === 'avg_heart_rate'">
          {{ record.avg_heart_rate ? record.avg_heart_rate + ' bpm' : '-' }}
        </template>
        <template v-if="column.key === 'avg_cadence'">
          {{ record.avg_cadence ? record.avg_cadence + ' spm' : '-' }}
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
    <a-modal v-model:open="manualModalOpen" title="手动录入跑步活动" @ok="saveManual" width="600px">
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
            <a-form-item label="爬升 (m)"><a-input-number v-model:value="manualForm.elevation_gain" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="平均心率 (bpm)"><a-input-number v-model:value="manualForm.avg_heart_rate" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="平均步频 (spm)"><a-input-number v-model:value="manualForm.avg_cadence" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="步数"><a-input-number v-model:value="manualForm.steps" :min="0" :precision="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="天气"><a-input v-model:value="manualForm.weather" placeholder="晴/多云/雨…" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="跑步路线"><a-input v-model:value="manualForm.running_route" placeholder="例如：CBD 环线" /></a-form-item>
        <a-form-item label="备注"><a-textarea v-model:value="manualForm.notes" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 编辑弹窗 -->
    <a-modal v-model:open="editModalOpen" title="编辑跑步活动" @ok="saveEdit" width="600px">
      <a-form :model="editForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="活动名称" required><a-input v-model:value="editForm.title" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="日期"><a-date-picker v-model:value="editForm.date" valueFormat="YYYY-MM-DD" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="跑步路线"><a-input v-model:value="editForm.running_route" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="天气"><a-input v-model:value="editForm.weather" /></a-form-item>
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
import { runningApi } from '@/api/index'

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const activities = ref([])
const stats = ref({ total_activities: 0, total_km: 0, total_hours: 0, total_elevation_gain: 0, total_calories: 0 })
const achievements = ref({})
const searchText = ref('')
const dateRange = ref(null)
const pagination = ref({ current: 1, pageSize: 20, total: 0 })

// 手动录入弹窗
const manualModalOpen = ref(false)
const manualForm = ref({
  title: '', date: '', distance_km: null, duration_min: null, calories: null,
  elevation_gain: null, avg_heart_rate: null, avg_cadence: null, steps: null,
  running_route: '', weather: '', notes: '',
})

// 编辑弹窗
const editModalOpen = ref(false)
const editingId = ref(null)
const editForm = ref({ title: '', date: '', running_route: '', weather: '', notes: '' })

const achievementIcons = {
  longest_distance: '📏',
  longest_duration: '⏱️',
  fastest_5km: '🏃',
  fastest_10km: '⚡',
  fastest_halfmarathon: '🏅',
  fastest_marathon: '🏆',
}

const achievementLabels = {
  longest_distance: '单次最长距离',
  longest_duration: '单次最长时间',
  fastest_5km: '5K 最快',
  fastest_10km: '10K 最快',
  fastest_halfmarathon: '半马最快',
  fastest_marathon: '全马最快',
}

const statCards = computed(() => [
  { label: '总次数', value: stats.value.total_activities, unit: '次', bg: 'linear-gradient(135deg, #ea580c 0%, #f97316 100%)' },
  { label: '总距离', value: stats.value.total_km, unit: '公里', bg: 'linear-gradient(135deg, #c2410c 0%, #ea580c 100%)' },
  { label: '总时长', value: stats.value.total_hours, unit: '小时', bg: 'linear-gradient(135deg, #c2410c 0%, #ea580c 100%)' },
  { label: '总爬升', value: stats.value.total_elevation_gain, unit: '米', bg: 'linear-gradient(135deg, #b45309 0%, #d97706 100%)' },
  { label: '总热量', value: stats.value.total_calories, unit: 'kcal', bg: 'linear-gradient(135deg, #c2410c 0%, #dc2626 100%)' },
  { label: '平均距离', value: stats.value.total_activities ? round(stats.value.total_km / stats.value.total_activities, 1) : 0, unit: '公里/次', bg: 'linear-gradient(135deg, #9a3412 0%, #ea580c 100%)' },
])

const columns = [
  { title: '活动名称', key: 'title', dataIndex: 'title', width: 180 },
  { title: '日期', key: 'date', dataIndex: 'date', width: 110, sorter: (a, b) => a.date.localeCompare(b.date) },
  { title: '距离', key: 'distance_km', dataIndex: 'distance_km', width: 100, sorter: (a, b) => (a.distance_km || 0) - (b.distance_km || 0) },
  { title: '时长', key: 'duration_sec', dataIndex: 'duration_sec', width: 90 },
  { title: '配速', key: 'pace_min_km', dataIndex: 'pace_min_km', width: 100 },
  { title: '爬升', key: 'elevation_gain', dataIndex: 'elevation_gain', width: 80 },
  { title: '热量', key: 'calories', dataIndex: 'calories', width: 90 },
  { title: '均心率', key: 'avg_heart_rate', dataIndex: 'avg_heart_rate', width: 85 },
  { title: '平均步频', key: 'avg_cadence', dataIndex: 'avg_cadence', width: 90 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

const filteredActivities = computed(() => {
  if (!searchText.value) return activities.value
  const q = searchText.value.toLowerCase()
  return activities.value.filter(a =>
    (a.title || '').toLowerCase().includes(q) ||
    (a.date || '').includes(q) ||
    (a.running_route || '').toLowerCase().includes(q)
  )
})

function round(v, d = 1) { return Number(v).toFixed(d) }

// ─── 导出 ───
function _downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename
  document.body.appendChild(a); a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

async function onExportMenu({ key }) {
  try {
    if (key === 'json') {
      const { data: blob } = await runningApi.exportBackup()
      _downloadBlob(blob, `running_backup_${new Date().toISOString().slice(0, 10)}.json`)
    } else if (key === 'csv') {
      const { data: blob } = await runningApi.exportCsv()
      _downloadBlob(blob, `running_activities_${new Date().toISOString().slice(0, 10)}.csv`)
    }
  } catch { message.error('导出失败') }
}

onMounted(async () => { await Promise.all([loadList(), loadStats(), loadAchievements()]) })

async function loadList() {
  loading.value = true
  loadError.value = ''
  try {
    const { data } = await runningApi.listActivities({ page: pagination.value.current, limit: pagination.value.pageSize })
    activities.value = data.items
    pagination.value.total = data.total
  } catch (e) {
    const msg = e.response?.data?.detail || e.message || '网络异常，请检查服务是否正常'
    loadError.value = msg
    message.error('加载失败：' + msg)
  } finally { loading.value = false }
}

async function loadStats() {
  try {
    const { data } = await runningApi.getStats()
    stats.value = data
  } catch (e) {}
}

async function loadAchievements() {
  try {
    const { data } = await runningApi.getAchievements()
    achievements.value = data
  } catch (e) {}
}

async function deleteActivity(id) {
  await runningApi.deleteActivity(id)
  message.success('已删除')
  loadList(); loadStats(); loadAchievements()
}

function goDetail(id) { router.push(`/sports/running/${id}`) }

function onTableChange(pag) { pagination.value.current = pag.current; loadList() }

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
  return `${m}'${s.toString().padStart(2, '0')}"`
}

function showManualModal() {
  manualForm.value = {
    title: '', date: '', distance_km: null, duration_min: null, calories: null,
    elevation_gain: null, avg_heart_rate: null, avg_cadence: null, steps: null,
    running_route: '', weather: '', notes: '',
  }
  manualModalOpen.value = true
}

async function saveManual() {
  if (!manualForm.value.title || !manualForm.value.date) { message.warning('请填写活动名称和日期'); return }
  try {
    const payload = {
      ...manualForm.value,
      duration_sec: manualForm.value.duration_min ? manualForm.value.duration_min * 60 : null,
    }
    delete payload.duration_min
    await runningApi.createManual(payload)
    message.success('录入成功')
    manualModalOpen.value = false
    loadList(); loadStats(); loadAchievements()
  } catch (e) { message.error('保存失败') }
}

function showEditModal(record) {
  editingId.value = record.id
  editForm.value = {
    title: record.title,
    date: record.date,
    running_route: record.running_route || '',
    weather: record.weather || '',
    notes: record.notes || '',
  }
  editModalOpen.value = true
}

async function saveEdit() {
  if (!editForm.value.title) { message.warning('请填写活动名称'); return }
  try {
    await runningApi.updateActivity(editingId.value, editForm.value)
    message.success('保存成功')
    editModalOpen.value = false
    loadList()
  } catch (e) { message.error('保存失败') }
}
</script>

<style scoped>
.stat-card {
  border-radius: 10px; text-align: center; color: #fff;
  transition: transform 0.2s; box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0,0,0,0.15); }
.stat-value { font-size: 22px; font-weight: bold; color: #fff; margin-top: 4px; }
.filter-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #fff7f0 !important; }

.achievement-card {
  background: linear-gradient(135deg, #fff7f0 0%, #ffedd5 100%);
  border-radius: 10px; padding: 16px; text-align: center;
  cursor: pointer; transition: transform 0.2s; border: 1px solid #fed7aa;
}
.achievement-card:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(249,115,22,0.15); }
.achievement-icon { font-size: 28px; margin-bottom: 4px; }
.achievement-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.achievement-value { font-size: 20px; font-weight: bold; color: #f97316; }
.achievement-meta { font-size: 11px; color: #999; margin-top: 4px; }
.achievement-note { font-size: 10px; color: #bbb; margin-top: 2px; }
</style>
