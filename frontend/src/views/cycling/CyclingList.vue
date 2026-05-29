<template>
  <div>
    <!-- 顶部筛选栏 -->
    <div class="filter-bar">
      <a-input-search
        v-model:value="searchText"
        placeholder="搜索活动名称或日期…"
        style="width: 220px"
        allow-clear
        @search="onSearch"
      />
      <a-range-picker
        v-model:value="dateRange"
        :placeholder="['开始日期', '结束日期']"
        format="YYYY-MM-DD"
        @change="loadList"
        style="width: 240px"
      />
      <a-select v-model:value="filterBike" placeholder="筛选车辆" allow-clear style="width: 160px" @change="loadList">
        <a-select-option v-for="b in bikes" :key="b.id" :value="b.id">{{ b.name }}</a-select-option>
      </a-select>
      <div style="flex: 1"></div>
      <a-dropdown>
        <template #overlay>
          <a-menu @click="onExportMenu">
            <a-menu-item key="json">📥 导出 JSON 备份</a-menu-item>
            <a-menu-item key="csv">📊 导出 CSV</a-menu-item>
          </a-menu>
        </template>
        <a-button>导出 ↓</a-button>
      </a-dropdown>
      <a-upload
        :before-upload="handleImport"
        :show-upload-list="false"
        accept=".json"
      >
        <a-button style="margin-left: 8px">📤 导入备份</a-button>
      </a-upload>
      <a-button type="primary" @click="$router.push('/sports/cycling/bikes?upload=1')">+ 上传活动</a-button>
    </div>

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
        <a-empty v-else description="暂无骑行记录" />
      </template>
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'title'">
          <a @click="goDetail(record.id)">{{ record.title }}</a>
        </template>
        <template v-if="column.key === 'distance_km'">
          <span style="font-weight: bold; color: #667eea">{{ record.distance_km }}</span> km
        </template>
        <template v-if="column.key === 'duration_sec'">
          {{ formatDuration(record.duration_sec) }}
        </template>
        <template v-if="column.key === 'avg_speed_kmh'">
          {{ record.avg_speed_kmh || '-' }} km/h
        </template>
        <template v-if="column.key === 'elevation_gain'">
          ↑ {{ record.elevation_gain || 0 }} m
        </template>
        <template v-if="column.key === 'avg_heart_rate'">
          {{ record.avg_heart_rate ? record.avg_heart_rate + ' bpm' : '—' }}
        </template>
        <template v-if="column.key === 'avg_cadence'">
          {{ record.avg_cadence ? record.avg_cadence + ' rpm' : '—' }}
        </template>
        <template v-if="column.key === 'calories'">
          {{ record.calories ? record.calories + ' kcal' : '—' }}
        </template>
        <template v-if="column.key === 'max_speed_kmh'">
          {{ record.max_speed_kmh ? record.max_speed_kmh + ' km/h' : '—' }}
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { cyclingApi } from '@/api/index'

const router = useRouter()
const loading = ref(false)
const loadError = ref('')
const activities = ref([])
const bikes = ref([])
const filterBike = ref(null)
const searchText = ref('')
const dateRange = ref(null)
const pagination = ref({ current: 1, pageSize: 25, total: 0, showSizeChanger: false, showTotal: total => `共 ${total} 条` })

// 编辑弹窗
const editModalOpen = ref(false)
const editingId = ref(null)
const editForm = ref({ title: '', date: '', route_type: '', weather: '', notes: '' })

const columns = [
  { title: '活动名称', key: 'title', dataIndex: 'title', width: 200 },
  { title: '日期', key: 'date', dataIndex: 'date', width: 110, sorter: (a, b) => a.date.localeCompare(b.date) },
  { title: '距离', key: 'distance_km', dataIndex: 'distance_km', width: 100, sorter: (a, b) => (a.distance_km || 0) - (b.distance_km || 0) },
  { title: '时长', key: 'duration_sec', dataIndex: 'duration_sec', width: 90 },
  { title: '均速', key: 'avg_speed_kmh', dataIndex: 'avg_speed_kmh', width: 110 },
  { title: '爬升', key: 'elevation_gain', dataIndex: 'elevation_gain', width: 90 },
  { title: '平均心率', key: 'avg_heart_rate', dataIndex: 'avg_heart_rate', width: 90 },
  { title: '平均踏频', key: 'avg_cadence', dataIndex: 'avg_cadence', width: 90 },
  { title: '卡路里', key: 'calories', dataIndex: 'calories', width: 90 },
  { title: '最大速度', key: 'max_speed_kmh', dataIndex: 'max_speed_kmh', width: 100 },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

// 前端搜索 + 日期过滤
const filteredActivities = computed(() => {
  let list = activities.value
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(a =>
      (a.title || '').toLowerCase().includes(q) ||
      (a.date || '').includes(q)
    )
  }
  return list
})

onMounted(async () => {
  await Promise.all([loadList(), loadBikes()])
})

async function loadList() {
  loading.value = true
  loadError.value = ''
  try {
    const params = {
      page: pagination.value.current,
      limit: pagination.value.pageSize,
      bike_id: filterBike.value || undefined,
    }
    // 日期范围
    if (dateRange.value && dateRange.value[0] && dateRange.value[1]) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const { data } = await cyclingApi.listActivities(params)
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

async function loadBikes() {
  try {
    const { data } = await cyclingApi.listBikes()
    bikes.value = data
  } catch (e) {}
}

function onSearch() {
  loadList()
}

async function deleteActivity(id) {
  await cyclingApi.deleteActivity(id)
  message.success('已删除')
  loadList()
}

function goDetail(id) {
  router.push(`/sports/cycling/${id}`)
}

function onTableChange(pag) {
  pagination.value.current = pag.current
  loadList()
}

function showEditModal(record) {
  editingId.value = record.id
  editForm.value = {
    title: record.title,
    date: record.date,
    route_type: record.route_type || '',
    weather: record.weather || '',
    notes: record.notes || '',
  }
  editModalOpen.value = true
}

async function saveEdit() {
  if (!editForm.value.title) { message.warning('请填写活动名称'); return }
  try {
    await cyclingApi.updateActivity(editingId.value, editForm.value)
    message.success('保存成功')
    editModalOpen.value = false
    loadList()
  } catch (e) {
    message.error('保存失败')
  }
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

// ─── 导出导入 ────────────────────────────────────────────
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
      const { data: blob, headers } = await cyclingApi.exportBackup()
      const name = (headers['content-disposition'] || '').split('filename=')[1] || 'cycling_backup.json'
      _downloadBlob(blob, name)
    } else if (key === 'csv') {
      const { data: blob, headers } = await cyclingApi.exportCsv()
      const name = (headers['content-disposition'] || '').split('filename=')[1] || 'cycling_activities.csv'
      _downloadBlob(blob, name)
    }
  } catch (e) {
    message.error('导出失败')
  }
}

async function handleImport(file) {
  try {
    const { data } = await cyclingApi.importBackup(file)
    const imported = data.imported
    const total = (imported.bikes || 0) + (imported.activities || 0) + (imported.maintenance || 0)
    if (total > 0) {
      message.success(`导入成功：${imported.activities || 0} 条活动，${imported.bikes || 0} 辆车，${imported.maintenance || 0} 条维护记录`)
    } else {
      message.info('没有新数据需要导入（全部已存在）')
    }
    loadList()
    loadBikes()
  } catch (e) {
    const msg = e.response?.data?.detail || '导入失败'
    message.error(msg)
  }
  return false // 阻止默认上传
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.clickable-row { cursor: pointer; }
.clickable-row:hover td { background: #f0f4ff !important; }

@media (max-width: 767px) {
  .filter-bar > * { flex: 1 1 calc(50% - 6px); min-width: 0; }
  .filter-bar .ant-btn { flex: 0 0 auto; }
}
</style>
