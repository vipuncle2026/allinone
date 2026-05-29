<template>
  <div class="travel-home">
    <!-- 左侧旅行列表 -->
    <div class="trip-sidebar">
      <div class="sidebar-header">
        <h3>✈️ 我的旅行</h3>
        <a-space>
          <a-upload
            :before-upload="handleImportTripJson"
            :show-upload-list="false"
            accept=".json"
          >
            <a-button size="small">📤 导入旅行</a-button>
          </a-upload>
          <a-button type="primary" size="small" @click="showTripModal()">+ 新建</a-button>
        </a-space>
      </div>
      <div class="trip-list">
        <div
          v-for="trip in trips"
          :key="trip.id"
          class="trip-card"
          :class="{ active: currentTripId === trip.id }"
          @click="selectTrip(trip.id)"
        >
          <div class="trip-card-header">
            <span class="trip-name">{{ trip.name }}</span>
            <span class="trip-actions">
              <a-button type="text" size="small" @click.stop="$router.push(`/travel/detail/${trip.id}`)">
                🔍
              </a-button>
              <a-button type="text" size="small" @click.stop="showTripModal(trip)">
                <EditOutlined />
              </a-button>
              <a-popconfirm title="确定删除此旅行？" @confirm="deleteTrip(trip.id)">
                <a-button type="text" size="small" danger @click.stop>
                  <DeleteOutlined />
                </a-button>
              </a-popconfirm>
            </span>
          </div>
          <div class="trip-dates">
            {{ trip.start_date || '未设置' }} ~ {{ trip.end_date || '未设置' }}
          </div>
          <div v-if="trip.budget > 0" class="trip-budget">
            <a-progress
              :percent="Math.min(trip.total_expense / trip.budget * 100, 100)"
              :size="4"
              :show-info="false"
              :stroke-color="trip.total_expense > trip.budget ? '#ef4444' : '#06b6d4'"
            />
            <span class="budget-text">{{ trip.currency }}{{ trip.total_expense }} / {{ trip.currency }}{{ trip.budget }}</span>
          </div>
        </div>
        <a-empty v-if="!trips.length" description="暂无旅行" :image-style="{ height: '60px' }" />
      </div>
      <div v-if="trips.length" class="sidebar-footer">
        <a-button size="small" block @click="handleExportAll">📥 导出全部旅行</a-button>
      </div>
    </div>

    <!-- 右侧主内容 -->
    <div class="trip-content">
      <!-- 空状态 -->
      <div v-if="!currentTripId" class="empty-state">
        <a-empty description="选择或创建一个旅行项目开始记录" />
      </div>

      <template v-else>
        <!-- 顶部：旅行名 + Tab + 操作 -->
        <div class="content-header">
          <h2>{{ currentTripName }}</h2>
          <a-space>
            <a-button size="small" @click="handleExportTripJson">📥 导出旅行</a-button>
            <a-upload
              :before-upload="handleImportCsv"
              :show-upload-list="false"
              accept=".csv"
            >
              <a-button size="small">📤 导入 CSV</a-button>
            </a-upload>
            <a-button size="small" @click="handleExportCsv">📄 导出 CSV</a-button>
          </a-space>
        </div>

        <a-tabs v-model:activeKey="activeTab" @change="onTabChange">
          <!-- 支出记录 -->
          <a-tab-pane key="expenses">
            <template #tab>
              <span>💰 支出记录</span>
            </template>
            <div class="tab-content">
              <!-- 统计卡片 -->
              <a-row :gutter="12" style="margin-bottom: 16px">
                <a-col :span="8">
                  <a-card size="small" class="travel-stat-card travel-stat-expense">
                    <a-statistic title="总支出" :value="stats.total_expense" :precision="2" :prefix="stats.currency" :value-style="{ color: '#fff' }" />
                  </a-card>
                </a-col>
                <a-col :span="8">
                  <a-card size="small" class="travel-stat-card travel-stat-count">
                    <a-statistic title="支出笔数" :value="stats.expense_count" suffix="笔" :value-style="{ color: '#fff' }" />
                  </a-card>
                </a-col>
                <a-col :span="8">
                  <a-card size="small" class="travel-stat-card travel-stat-avg">
                    <a-statistic title="平均支出" :value="stats.avg_expense" :precision="2" :prefix="stats.currency" :value-style="{ color: '#fff' }" />
                  </a-card>
                </a-col>
              </a-row>

              <a-card size="small">
                <template #title>
                  <a-space>
                    <span>支出明细</span>
                    <a-button type="primary" size="small" @click="showExpenseModal()">+ 添加支出</a-button>
                  </a-space>
                </template>
                <template #extra>
                  <a-input-search v-model:value="expenseSearch" placeholder="搜索备注..." size="small" style="width: 200px" @search="loadExpenses" />
                </template>
                <a-table :dataSource="filteredExpenses" :columns="expenseColumns" size="small" :pagination="{ pageSize: 15, showSizeChanger: false, showTotal: t => `共 ${t} 条` }" row-key="id">
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.dataIndex === 'date'">
                      {{ (record.date || '').replace('T', ' ') }}
                    </template>
                    <template v-if="column.dataIndex === 'category'">
                      <a-tag :color="record.category_color">{{ record.category_icon }} {{ record.category }}</a-tag>
                    </template>
                    <template v-if="column.dataIndex === 'amount'">
                      <span style="font-weight: 600">{{ stats.currency }}{{ record.amount.toFixed(2) }}</span>
                    </template>
                    <template v-if="column.dataIndex === 'actions'">
                      <a-space>
                        <a-button type="link" size="small" @click="showExpenseModal(record)">编辑</a-button>
                        <a-popconfirm title="确定删除？" @confirm="deleteExpense(record.id)">
                          <a-button type="link" size="small" danger>删除</a-button>
                        </a-popconfirm>
                      </a-space>
                    </template>
                  </template>
                </a-table>
              </a-card>
            </div>
          </a-tab-pane>

          <!-- 里程记录 -->
          <a-tab-pane key="mileages">
            <template #tab>
              <span>🛣️ 里程记录</span>
            </template>
            <div class="tab-content">
              <a-row :gutter="12" style="margin-bottom: 16px">
                <a-col :span="8">
                  <a-card size="small" class="travel-stat-card travel-stat-km">
                    <a-statistic title="实际总里程" :value="stats.total_km" suffix="km" :precision="1" />
                  </a-card>
                </a-col>
                <a-col :span="8">
                  <a-card size="small" class="travel-stat-card travel-stat-planned">
                    <a-statistic title="预计里程" :value="stats.planned_km || 0" suffix="km" />
                  </a-card>
                </a-col>
                <a-col :span="8">
                  <a-card size="small" class="travel-stat-card travel-stat-percent">
                    <a-statistic title="完成率" :value="stats.km_completed_percent || 0" suffix="%" />
                  </a-card>
                </a-col>
              </a-row>

              <!-- 里程进度条 -->
              <a-card v-if="stats.planned_km > 0" size="small" style="margin-bottom: 16px">
                <a-progress
                  :percent="Math.min(stats.km_completed_percent || 0, 100)"
                  :stroke-color="{ '0%': '#F4A261', '100%': '#f97316' }"
                />
                <div style="text-align: center; color: #64748b; font-size: 12px; margin-top: 4px">
                  {{ stats.total_km }} / {{ stats.planned_km }} km
                </div>
              </a-card>

              <a-card size="small">
                <template #title>
                  <a-space>
                    <span>里程明细</span>
                    <a-button type="primary" size="small" @click="showMileageModal()">+ 添加里程</a-button>
                  </a-space>
                </template>
                <a-table :dataSource="mileages" :columns="mileageColumns" size="small" :pagination="{ pageSize: 15, showSizeChanger: false, showTotal: t => `共 ${t} 条` }" row-key="id">
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.dataIndex === 'date'">
                      {{ (record.date || '').replace('T', ' ') }}
                    </template>
                    <template v-if="column.dataIndex === 'transport'">
                      <a-tag :color="record.transport_color">{{ record.transport_icon }} {{ record.transport }}</a-tag>
                    </template>
                    <template v-if="column.dataIndex === 'km'">
                      <span style="font-weight: 600">{{ record.km.toFixed(1) }} km</span>
                    </template>
                    <template v-if="column.dataIndex === 'actions'">
                      <a-space>
                        <a-button type="link" size="small" @click="showMileageModal(record)">编辑</a-button>
                        <a-popconfirm title="确定删除？" @confirm="deleteMileage(record.id)">
                          <a-button type="link" size="small" danger>删除</a-button>
                        </a-popconfirm>
                      </a-space>
                    </template>
                  </template>
                </a-table>
              </a-card>
            </div>
          </a-tab-pane>

          <!-- 统计分析 -->
          <a-tab-pane key="analytics">
            <template #tab>
              <span>📊 统计分析</span>
            </template>
            <div class="tab-content">
              <!-- 预算进度 -->
              <a-card v-if="stats.budget > 0" size="small" style="margin-bottom: 16px">
                <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
                  <span style="font-weight: 600">预算使用情况</span>
                  <span style="color: #64748b">{{ stats.currency }}{{ stats.total_expense }} / {{ stats.currency }}{{ stats.budget }}</span>
                </div>
                <a-progress
                  :percent="Math.min(stats.budget_used_percent || 0, 100)"
                  :stroke-color="budgetColor"
                />
              </a-card>

              <!-- 图表 -->
              <a-row :gutter="16" style="margin-bottom: 16px">
                <a-col :span="12">
                  <a-card size="small" title="支出分类占比">
                    <div v-if="stats.category_breakdown && stats.category_breakdown.length" style="height: 280px">
                      <Doughnut :data="pieConfig" :options="pieOptions" />
                    </div>
                    <a-empty v-else description="暂无数据" />
                  </a-card>
                </a-col>
                <a-col :span="12">
                  <a-card size="small" title="每日支出趋势">
                    <div v-if="stats.daily_trend && stats.daily_trend.length" style="height: 280px">
                      <Bar :data="barConfig" :options="barOptions" />
                    </div>
                    <a-empty v-else description="暂无数据" />
                  </a-card>
                </a-col>
              </a-row>

              <!-- 分类统计表 -->
              <a-card size="small" title="分类统计">
                <a-table
                  :dataSource="stats.category_breakdown || []"
                  :columns="categoryColumns"
                  size="small"
                  :pagination="false"
                  row-key="category"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.dataIndex === 'category'">
                      <span>{{ record.icon }} {{ record.category }}</span>
                    </template>
                    <template v-if="column.dataIndex === 'amount'">
                      <span style="font-weight: 600">{{ stats.currency }}{{ record.amount.toFixed(2) }}</span>
                    </template>
                    <template v-if="column.dataIndex === 'percent'">
                      <a-progress :percent="record.percent" :size="4" :show-info="true" :stroke-color="record.color" style="width: 120px" />
                    </template>
                  </template>
                </a-table>
              </a-card>
            </div>
          </a-tab-pane>
        </a-tabs>
      </template>
    </div>

    <!-- 旅行弹窗 -->
    <a-modal v-model:open="tripModalVisible" :title="editingTrip ? '编辑旅行' : '新建旅行'" @ok="saveTrip" :confirmLoading="saving" width="500px">
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }" style="margin-top: 16px">
        <a-form-item label="旅行名称" required>
          <a-input v-model:value="tripForm.name" placeholder="例如：东京之旅" />
        </a-form-item>
        <a-form-item label="目的地">
          <a-input v-model:value="tripForm.destination" placeholder="例如：日本东京" />
        </a-form-item>
        <a-form-item label="日期范围">
          <a-range-picker v-model:value="tripForm.dateRange" style="width: 100%" />
        </a-form-item>
        <a-form-item label="预算金额">
          <a-input-number v-model:value="tripForm.budget" :min="0" :precision="2" style="width: 100%" placeholder="0" />
        </a-form-item>
        <a-form-item label="币种">
          <a-select v-model:value="tripForm.currency">
            <a-select-option value="¥">人民币 (¥)</a-select-option>
            <a-select-option value="$">美元 ($)</a-select-option>
            <a-select-option value="€">欧元 (€)</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="预计里程">
          <a-input-number v-model:value="tripForm.planned_km" :min="0" style="width: 100%" placeholder="0" suffix="km" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 支出弹窗 -->
    <a-modal v-model:open="expenseModalVisible" :title="editingExpense ? '编辑支出' : '添加支出'" @ok="saveExpense" :confirmLoading="saving" width="460px">
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }" style="margin-top: 16px">
        <a-form-item label="日期" required>
          <a-date-picker v-model:value="expenseForm.date" show-time format="YYYY-MM-DD HH:mm" style="width: 100%" />
        </a-form-item>
        <a-form-item label="分类" required>
          <a-select v-model:value="expenseForm.category">
            <a-select-option v-for="(info, key) in expenseCategories" :key="key" :value="key">
              {{ info.icon }} {{ key }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="金额" required>
          <a-input-number v-model:value="expenseForm.amount" :min="0" :precision="2" style="width: 100%" placeholder="0.00" />
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="expenseForm.note" placeholder="可选备注" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 里程弹窗 -->
    <a-modal v-model:open="mileageModalVisible" :title="editingMileage ? '编辑里程' : '添加里程'" @ok="saveMileage" :confirmLoading="saving" width="500px">
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }" style="margin-top: 16px">
        <a-form-item label="日期" required>
          <a-date-picker v-model:value="mileageForm.date" show-time format="YYYY-MM-DD HH:mm" style="width: 100%" />
        </a-form-item>
        <a-form-item label="交通方式" required>
          <a-select v-model:value="mileageForm.transport">
            <a-select-option v-for="(info, key) in transportTypes" :key="key" :value="key">
              {{ info.icon }} {{ key }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="里程" required>
          <a-input-number v-model:value="mileageForm.km" :min="0" :precision="1" style="width: 100%" placeholder="0" suffix="km" />
        </a-form-item>
        <a-form-item label="出发地">
          <a-input v-model:value="mileageForm.from_place" placeholder="出发城市/地点" />
        </a-form-item>
        <a-form-item label="目的地">
          <a-input v-model:value="mileageForm.to_place" placeholder="到达城市/地点" />
        </a-form-item>
        <a-form-item label="备注">
          <a-input v-model:value="mileageForm.note" placeholder="可选备注" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { EditOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { Doughnut, Bar } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import dayjs from 'dayjs'
import { travelApi } from '@/api'

ChartJS.register(ArcElement, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

// 状态
const trips = ref([])
const currentTripId = ref(null)
const activeTab = ref('expenses')
const saving = ref(false)
const expenseSearch = ref('')

// 配置
const expenseCategories = ref({})
const transportTypes = ref({})

// 统计
const stats = ref({
  total_expense: 0, expense_count: 0, avg_expense: 0,
  total_km: 0, budget: 0, currency: '¥',
  budget_used_percent: 0, planned_km: 0, km_completed_percent: 0,
  category_breakdown: [], daily_trend: [],
})

// 弹窗状态
const tripModalVisible = ref(false)
const editingTrip = ref(null)
const tripForm = ref({ name: '', destination: '', dateRange: null, budget: 0, currency: '¥', planned_km: 0 })

const expenseModalVisible = ref(false)
const editingExpense = ref(null)
const expenseForm = ref({ date: null, category: '餐饮', amount: 0, note: '' })

const mileageModalVisible = ref(false)
const editingMileage = ref(null)
const mileageForm = ref({ date: null, transport: '飞机', km: 0, from_place: '', to_place: '', note: '' })

// 数据
const expenses = ref([])
const mileages = ref([])

// 当前旅行名称
const currentTripName = computed(() => {
  const trip = trips.value.find(t => t.id === currentTripId.value)
  return trip ? trip.name : ''
})

// 过滤支出
const filteredExpenses = computed(() => {
  if (!expenseSearch.value) return expenses.value
  const keyword = expenseSearch.value.toLowerCase()
  return expenses.value.filter(e => (e.note || '').toLowerCase().includes(keyword))
})

// 预算颜色
const budgetColor = computed(() => {
  const pct = stats.value.budget_used_percent || 0
  if (pct >= 100) return '#ef4444'
  if (pct >= 80) return '#f59e0b'
  return '#06b6d4'
})

// 表格列定义
const expenseColumns = [
  { title: '日期', dataIndex: 'date', width: 150, ellipsis: true },
  { title: '分类', dataIndex: 'category', width: 120 },
  { title: '金额', dataIndex: 'amount', width: 120, align: 'right' },
  { title: '备注', dataIndex: 'note', ellipsis: true },
  { title: '操作', dataIndex: 'actions', width: 120, align: 'center' },
]

const mileageColumns = [
  { title: '日期', dataIndex: 'date', width: 150, ellipsis: true },
  { title: '交通方式', dataIndex: 'transport', width: 120 },
  { title: '里程', dataIndex: 'km', width: 100, align: 'right' },
  { title: '出发地', dataIndex: 'from_place', ellipsis: true },
  { title: '目的地', dataIndex: 'to_place', ellipsis: true },
  { title: '备注', dataIndex: 'note', ellipsis: true },
  { title: '操作', dataIndex: 'actions', width: 120, align: 'center' },
]

const categoryColumns = [
  { title: '分类', dataIndex: 'category', width: 120 },
  { title: '金额', dataIndex: 'amount', width: 140, align: 'right' },
  { title: '占比', dataIndex: 'percent', width: 200 },
]

// 饼图配置
const pieConfig = computed(() => ({
  labels: (stats.value.category_breakdown || []).map(c => c.category),
  datasets: [{
    data: (stats.value.category_breakdown || []).map(c => c.amount),
    backgroundColor: (stats.value.category_breakdown || []).map(c => c.color),
    borderWidth: 0,
  }],
}))

const pieOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'right', labels: { padding: 12, font: { size: 12 } } },
    tooltip: {
      callbacks: { label: ctx => `${ctx.label}: ${stats.value.currency}${ctx.parsed.toFixed(2)}` }
    },
  },
}

// 柱状图配置
const barConfig = computed(() => ({
  labels: (stats.value.daily_trend || []).map(d => d.date),
  datasets: [{
    label: '支出',
    data: (stats.value.daily_trend || []).map(d => d.amount),
    backgroundColor: '#06b6d4',
    borderRadius: 4,
  }],
}))

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: { legend: { display: false } },
  scales: {
    y: { beginAtZero: true, grid: { color: '#F3F4F6' } },
    x: { grid: { display: false } },
  },
}

// 加载数据
async function loadTrips() {
  try {
    const res = await travelApi.listTrips()
    trips.value = res.data
  } catch { message.error('加载旅行列表失败') }
}

async function loadExpenses() {
  if (!currentTripId.value) return
  try {
    const res = await travelApi.listExpenses(currentTripId.value, { keyword: expenseSearch.value || undefined })
    expenses.value = res.data
  } catch { message.error('加载支出失败') }
}

async function loadMileages() {
  if (!currentTripId.value) return
  try {
    const res = await travelApi.listMileages(currentTripId.value)
    mileages.value = res.data
  } catch { message.error('加载里程失败') }
}

async function loadStats() {
  if (!currentTripId.value) return
  try {
    const res = await travelApi.getStats(currentTripId.value)
    stats.value = res.data
  } catch { /* 静默 */ }
}

function selectTrip(id) {
  currentTripId.value = id
  activeTab.value = 'expenses'
  loadAllTripData()
}

function loadAllTripData() {
  loadExpenses()
  loadMileages()
  loadStats()
}

function onTabChange(key) {
  if (key === 'analytics') loadStats()
}

// ─── Trip CRUD ───

function showTripModal(trip = null) {
  editingTrip.value = trip
  if (trip) {
    tripForm.value = {
      name: trip.name,
      destination: trip.destination || '',
      dateRange: (trip.start_date && trip.end_date) ? [dayjs(trip.start_date), dayjs(trip.end_date)] : null,
      budget: trip.budget || 0,
      currency: trip.currency || '¥',
      planned_km: trip.planned_km || 0,
    }
  } else {
    tripForm.value = { name: '', destination: '', dateRange: null, budget: 0, currency: '¥', planned_km: 0 }
  }
  tripModalVisible.value = true
}

async function saveTrip() {
  if (!tripForm.value.name) return message.warning('请输入旅行名称')
  saving.value = true
  try {
    const payload = {
      name: tripForm.value.name,
      destination: tripForm.value.destination,
      start_date: tripForm.value.dateRange ? dayjs(tripForm.value.dateRange[0]).format('YYYY-MM-DD') : null,
      end_date: tripForm.value.dateRange ? dayjs(tripForm.value.dateRange[1]).format('YYYY-MM-DD') : null,
      budget: tripForm.value.budget,
      currency: tripForm.value.currency,
      planned_km: tripForm.value.planned_km,
    }
    if (editingTrip.value) {
      await travelApi.updateTrip(editingTrip.value.id, payload)
      message.success('更新成功')
    } else {
      await travelApi.createTrip(payload)
      message.success('创建成功')
    }
    tripModalVisible.value = false
    await loadTrips()
    // 如果是新建，自动选中新创建的
    if (!editingTrip.value) {
      const res = await travelApi.listTrips()
      if (res.data.length) {
        currentTripId.value = res.data[0].id
        loadAllTripData()
      }
    }
  } catch { message.error('操作失败') }
  finally { saving.value = false }
}

async function deleteTrip(id) {
  try {
    await travelApi.deleteTrip(id)
    message.success('删除成功')
    if (currentTripId.value === id) currentTripId.value = null
    await loadTrips()
  } catch { message.error('删除失败') }
}

// ─── Expense CRUD ───

function showExpenseModal(expense = null) {
  editingExpense.value = expense
  if (expense) {
    expenseForm.value = {
      date: dayjs(expense.date),
      category: expense.category,
      amount: expense.amount,
      note: expense.note || '',
    }
  } else {
    expenseForm.value = { date: dayjs(), category: '餐饮', amount: 0, note: '' }
  }
  expenseModalVisible.value = true
}

async function saveExpense() {
  if (!expenseForm.value.date || !expenseForm.value.amount) return message.warning('请填写必填信息')
  saving.value = true
  try {
    const payload = {
      trip_id: currentTripId.value,
      date: dayjs(expenseForm.value.date).format('YYYY-MM-DDTHH:mm'),
      category: expenseForm.value.category,
      amount: expenseForm.value.amount,
      note: expenseForm.value.note,
    }
    if (editingExpense.value) {
      await travelApi.updateExpense(editingExpense.value.id, payload)
      message.success('更新成功')
    } else {
      await travelApi.createExpense(payload)
      message.success('创建成功')
    }
    expenseModalVisible.value = false
    loadExpenses()
    loadStats()
  } catch { message.error('操作失败') }
  finally { saving.value = false }
}

async function deleteExpense(id) {
  try {
    await travelApi.deleteExpense(id)
    message.success('删除成功')
    loadExpenses()
    loadStats()
  } catch { message.error('删除失败') }
}

// ─── Mileage CRUD ───

function showMileageModal(mileage = null) {
  editingMileage.value = mileage
  if (mileage) {
    mileageForm.value = {
      date: dayjs(mileage.date),
      transport: mileage.transport,
      km: mileage.km,
      from_place: mileage.from_place || '',
      to_place: mileage.to_place || '',
      note: mileage.note || '',
    }
  } else {
    mileageForm.value = { date: dayjs(), transport: '飞机', km: 0, from_place: '', to_place: '', note: '' }
  }
  mileageModalVisible.value = true
}

async function saveMileage() {
  if (!mileageForm.value.date || !mileageForm.value.km) return message.warning('请填写必填信息')
  saving.value = true
  try {
    const payload = {
      trip_id: currentTripId.value,
      date: dayjs(mileageForm.value.date).format('YYYY-MM-DDTHH:mm'),
      transport: mileageForm.value.transport,
      km: mileageForm.value.km,
      from_place: mileageForm.value.from_place,
      to_place: mileageForm.value.to_place,
      note: mileageForm.value.note,
    }
    if (editingMileage.value) {
      await travelApi.updateMileage(editingMileage.value.id, payload)
      message.success('更新成功')
    } else {
      await travelApi.createMileage(payload)
      message.success('创建成功')
    }
    mileageModalVisible.value = false
    loadMileages()
    loadStats()
  } catch { message.error('操作失败') }
  finally { saving.value = false }
}

async function deleteMileage(id) {
  try {
    await travelApi.deleteMileage(id)
    message.success('删除成功')
    loadMileages()
    loadStats()
  } catch { message.error('删除失败') }
}

// ─── JSON 导入导出（旅行级别） ───

async function handleExportTripJson() {
  if (!currentTripId.value) return
  try {
    const res = await travelApi.exportTripJson(currentTripId.value)
    const blob = new Blob([res.data], { type: 'application/json;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentTripName.value}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { message.error('导出失败') }
}

async function handleExportAll() {
  try {
    const res = await travelApi.exportAllJson()
    const blob = new Blob([res.data], { type: 'application/json;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '全部旅行.json'
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { message.error('导出失败') }
}

async function handleImportTripJson(file) {
  try {
    const text = await file.text()
    const data = JSON.parse(text)
    const res = await travelApi.importTripJson(data)
    message.success(res.data.message)
    await loadTrips()
    // 自动选中新导入的第一个旅行
    if (res.data.imported && res.data.imported.length) {
      const tripsRes = await travelApi.listTrips()
      const newestName = res.data.imported[0].name
      const match = tripsRes.data.find(t => t.name === newestName)
      if (match) {
        currentTripId.value = match.id
        loadAllTripData()
      }
    }
  } catch (e) {
    message.error('导入失败，请检查 JSON 文件格式')
  }
  return false
}

// ─── CSV 导入导出 ───

async function handleExportCsv() {
  if (!currentTripId.value) return
  try {
    const res = await travelApi.exportCsv(currentTripId.value)
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${currentTripName.value}_记录.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { message.error('导出失败') }
}

async function handleImportCsv(file) {
  if (!currentTripId.value) return message.warning('请先选择旅行')
  const text = await file.text()
  try {
    const res = await travelApi.importCsv(currentTripId.value, { csv: text })
    message.success(res.data.message)
    loadAllTripData()
    loadTrips()
  } catch { message.error('导入失败，请检查文件格式') }
  return false
}

// 初始化
onMounted(async () => {
  const [tripsRes, configRes] = await Promise.all([
    travelApi.listTrips(),
    travelApi.getConfig(),
  ])
  trips.value = tripsRes.data
  expenseCategories.value = configRes.data.expense_categories
  transportTypes.value = configRes.data.transport_types
  // 自动选中第一个
  if (trips.value.length) {
    currentTripId.value = trips.value[0].id
    loadAllTripData()
  }
})
</script>

<style scoped>
.travel-stat-card {
  border-radius: 10px;
  color: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  transition: transform 0.2s;
}
.travel-stat-card:hover { transform: translateY(-2px); box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15); }
.travel-stat-card :deep(.ant-statistic-title) { color: rgba(255, 255, 255, 0.85) !important; }
.travel-stat-card :deep(.ant-statistic-content) { color: #fff !important; }
.travel-stat-card :deep(.ant-statistic-content-value) { color: #fff !important; }
.travel-stat-card :deep(.ant-statistic-content-suffix) { color: rgba(255, 255, 255, 0.8) !important; }
.travel-stat-card :deep(.ant-statistic-content-prefix) { color: rgba(255, 255, 255, 0.9) !important; }
.travel-stat-card :deep(.ant-card-body) { padding: 16px 20px !important; }
.travel-stat-expense { background: linear-gradient(135deg, #f5222d 0%, #ff7a45 100%) !important; }
.travel-stat-count { background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%) !important; }
.travel-stat-avg { background: linear-gradient(135deg, #722ed1 0%, #eb2f96 100%) !important; }
.travel-stat-km { background: linear-gradient(135deg, #2d9a4e 0%, #52c41a 100%) !important; }
.travel-stat-planned { background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%) !important; }
.travel-stat-percent { background: linear-gradient(135deg, #fa8c16 0%, #fadb14 100%) !important; }

.travel-home {
  display: flex;
  gap: 16px;
  max-width: 1400px;
}

.trip-sidebar {
  width: 280px;
  flex-shrink: 0;
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding: 0 4px;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
}

.trip-list {
  max-height: calc(100vh - 180px);
  overflow-y: auto;
}

.trip-card {
  padding: 12px;
  border-radius: 8px;
  border: 2px solid #f0f0f0;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
  background: #fff;
}

.trip-card:hover {
  border-color: #d9d9d9;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}

.trip-card.active {
  border-color: #06b6d4;
  background: rgba(6, 182, 212, 0.05);
}

.trip-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.trip-name {
  font-weight: 600;
  font-size: 14px;
}

.trip-actions {
  display: none;
}

.trip-card:hover .trip-actions {
  display: flex;
}

.trip-dates {
  font-size: 12px;
  color: #8c8c8c;
  margin: 4px 0;
}

.trip-budget {
  display: flex;
  align-items: center;
  gap: 8px;
}

.budget-text {
  font-size: 11px;
  color: #8c8c8c;
  white-space: nowrap;
}

.trip-content {
  flex: 1;
  min-width: 0;
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 400px;
}

.content-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.content-header h2 {
  margin: 0;
  font-size: 18px;
}

.tab-content {
  padding-top: 4px;
}

.sidebar-footer {
  padding: 8px 4px 0;
  border-top: 1px solid #f0f0f0;
  margin-top: 8px;
  padding-top: 12px;
}
</style>
