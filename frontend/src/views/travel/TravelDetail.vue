<template>
  <div class="travel-detail">
    <!-- 加载中 -->
    <a-spin v-if="loading" tip="加载中…" />
    <a-result v-else-if="!trip" status="404" title="旅行不存在" sub-title="该旅行可能已被删除" />

    <template v-else>
      <!-- 顶部：旅行信息 + 操作 -->
      <div class="detail-header">
        <div class="header-left">
          <a-button type="text" @click="$router.push('/travel')" style="padding: 0; margin-bottom: 8px">
            ← 返回列表
          </a-button>
          <h2>{{ trip.name }}</h2>
          <div class="header-meta">
            <a-tag v-if="trip.destination">{{ trip.destination }}</a-tag>
            <span>{{ trip.start_date || '?' }} ~ {{ trip.end_date || '?' }}</span>
            <a-tag v-if="trip.budget > 0" :color="budgetTagColor">
              预算 {{ trip.currency }}{{ trip.budget }}
            </a-tag>
          </div>
        </div>
        <a-space>
          <a-button @click="showTripModal(trip)">✏️ 编辑</a-button>
          <a-upload :before-upload="handleImportCsv" :show-upload-list="false" accept=".csv" :disabled="!trip">
            <a-button>📤 导入 CSV</a-button>
          </a-upload>
          <a-button @click="handleExportCsv">📄 导出 CSV</a-button>
          <a-button @click="handleExportTripJson">📥 导出 JSON</a-button>
          <a-popconfirm title="确定删除此旅行？" @confirm="deleteTrip(trip.id)">
            <a-button danger>🗑️ 删除</a-button>
          </a-popconfirm>
        </a-space>
      </div>

      <!-- Tabs -->
      <a-tabs v-model:activeKey="activeTab">
        <!-- 支出记录 -->
        <a-tab-pane key="expenses">
          <template #tab><span>💰 支出记录</span></template>
          <div class="tab-content">
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
                <a-input-search v-model:value="expenseSearch" placeholder="搜索备注…" size="small" style="width: 200px" @search="loadExpenses" />
              </template>
              <a-table
                :dataSource="filteredExpenses"
                :columns="expenseColumns"
                size="small"
                :pagination="{ pageSize: 15, showSizeChanger: false, showTotal: t => `共 ${t} 条` }"
                row-key="id"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.dataIndex === 'date'">{{ (record.date || '').replace('T', ' ') }}</template>
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
          <template #tab><span>🛣️ 里程记录</span></template>
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

            <a-card v-if="stats.planned_km > 0" size="small" style="margin-bottom: 16px">
              <a-progress :percent="Math.min(stats.km_completed_percent || 0, 100)" :stroke-color="{ '0%': '#F4A261', '100%': '#f97316' }" />
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
              <a-table
                :dataSource="mileages"
                :columns="mileageColumns"
                size="small"
                :pagination="{ pageSize: 15, showSizeChanger: false, showTotal: t => `共 ${t} 条` }"
                row-key="id"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.dataIndex === 'date'">{{ (record.date || '').replace('T', ' ') }}</template>
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
          <template #tab><span>📊 统计分析</span></template>
          <div class="tab-content">
            <a-card v-if="stats.budget > 0" size="small" style="margin-bottom: 16px">
              <div style="display: flex; justify-content: space-between; margin-bottom: 8px">
                <span style="font-weight: 600">预算使用情况</span>
                <span style="color: #64748b">{{ stats.currency }}{{ stats.total_expense }} / {{ stats.currency }}{{ stats.budget }}</span>
              </div>
              <a-progress :percent="Math.min(stats.budget_used_percent || 0, 100)" :stroke-color="budgetColor" />
            </a-card>

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

            <a-card size="small" title="分类统计">
              <a-table
                :dataSource="stats.category_breakdown || []"
                :columns="categoryColumns"
                size="small"
                :pagination="false"
                row-key="category"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.dataIndex === 'category'"><span>{{ record.icon }} {{ record.category }}</span></template>
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

    <!-- 旅行编辑弹窗（从 Home 共享） -->
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
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { Doughnut, Bar } from 'vue-chartjs'
import { Chart as ChartJS, ArcElement, Tooltip, Legend, BarElement, CategoryScale, LinearScale } from 'chart.js'
import dayjs from 'dayjs'
import { travelApi } from '@/api'

ChartJS.register(ArcElement, Tooltip, Legend, BarElement, CategoryScale, LinearScale)

const route = useRoute()
const router = useRouter()
const tripId = computed(() => Number(route.params.id))

const loading = ref(true)
const trip = ref(null)
const activeTab = ref('expenses')
const saving = ref(false)
const expenseSearch = ref('')

const expenseCategories = ref({})
const transportTypes = ref({})

const stats = ref({
  total_expense: 0, expense_count: 0, avg_expense: 0,
  total_km: 0, budget: 0, currency: '¥',
  budget_used_percent: 0, planned_km: 0, km_completed_percent: 0,
  category_breakdown: [], daily_trend: [],
})

const tripModalVisible = ref(false)
const editingTrip = ref(null)
const tripForm = ref({ name: '', destination: '', dateRange: null, budget: 0, currency: '¥', planned_km: 0 })

const expenseModalVisible = ref(false)
const editingExpense = ref(null)
const expenseForm = ref({ date: null, category: '餐饮', amount: 0, note: '' })

const mileageModalVisible = ref(false)
const editingMileage = ref(null)
const mileageForm = ref({ date: null, transport: '飞机', km: 0, from_place: '', to_place: '', note: '' })

const expenses = ref([])
const mileages = ref([])

const budgetColor = computed(() => {
  const pct = stats.value.budget_used_percent || 0
  if (pct >= 100) return '#ef4444'
  if (pct >= 80) return '#f59e0b'
  return '#06b6d4'
})

const budgetTagColor = computed(() => {
  const pct = stats.value.budget_used_percent || 0
  if (pct >= 100) return 'red'
  if (pct >= 80) return 'orange'
  return 'blue'
})

const filteredExpenses = computed(() => {
  if (!expenseSearch.value) return expenses.value
  const keyword = expenseSearch.value.toLowerCase()
  return expenses.value.filter(e => (e.note || '').toLowerCase().includes(keyword))
})

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
    tooltip: { callbacks: { label: ctx => `${ctx.label}: ${stats.value.currency}${ctx.parsed.toFixed(2)}` } },
  },
}

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

async function loadTrip() {
  loading.value = true
  try {
    const [tripRes, configRes] = await Promise.all([
      travelApi.getTrip(tripId.value),
      travelApi.getConfig(),
    ])
    trip.value = tripRes.data
    expenseCategories.value = configRes.data.expense_categories
    transportTypes.value = configRes.data.transport_types
    loadAll()
  } catch {
    trip.value = null
  } finally {
    loading.value = false
  }
}

async function loadExpenses() {
  try {
    const res = await travelApi.listExpenses(tripId.value, { keyword: expenseSearch.value || undefined })
    expenses.value = res.data
  } catch {}
}

async function loadMileages() {
  try {
    const res = await travelApi.listMileages(tripId.value)
    mileages.value = res.data
  } catch {}
}

async function loadStats() {
  try {
    const res = await travelApi.getStats(tripId.value)
    stats.value = res.data
  } catch {}
}

function loadAll() {
  loadExpenses()
  loadMileages()
  loadStats()
}

// Trip CRUD
function showTripModal(tripData = null) {
  editingTrip.value = tripData
  if (tripData) {
    tripForm.value = {
      name: tripData.name,
      destination: tripData.destination || '',
      dateRange: (tripData.start_date && tripData.end_date) ? [dayjs(tripData.start_date), dayjs(tripData.end_date)] : null,
      budget: tripData.budget || 0,
      currency: tripData.currency || '¥',
      planned_km: tripData.planned_km || 0,
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
    }
    tripModalVisible.value = false
    loadTrip()
  } catch { message.error('操作失败') }
  finally { saving.value = false }
}

async function deleteTrip(id) {
  try {
    await travelApi.deleteTrip(id)
    message.success('已删除')
    router.push('/travel')
  } catch { message.error('删除失败') }
}

// Expense CRUD
function showExpenseModal(expense = null) {
  editingExpense.value = expense
  if (expense) {
    expenseForm.value = { date: dayjs(expense.date), category: expense.category, amount: expense.amount, note: expense.note || '' }
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
      trip_id: tripId.value,
      date: dayjs(expenseForm.value.date).format('YYYY-MM-DDTHH:mm'),
      category: expenseForm.value.category,
      amount: expenseForm.value.amount,
      note: expenseForm.value.note,
    }
    if (editingExpense.value) {
      await travelApi.updateExpense(editingExpense.value.id, payload)
    } else {
      await travelApi.createExpense(payload)
    }
    message.success('保存成功')
    expenseModalVisible.value = false
    loadExpenses()
    loadStats()
  } catch { message.error('操作失败') }
  finally { saving.value = false }
}

async function deleteExpense(id) {
  await travelApi.deleteExpense(id)
  message.success('已删除')
  loadExpenses()
  loadStats()
}

// Mileage CRUD
function showMileageModal(mileage = null) {
  editingMileage.value = mileage
  if (mileage) {
    mileageForm.value = {
      date: dayjs(mileage.date), transport: mileage.transport, km: mileage.km,
      from_place: mileage.from_place || '', to_place: mileage.to_place || '', note: mileage.note || '',
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
      trip_id: tripId.value,
      date: dayjs(mileageForm.value.date).format('YYYY-MM-DDTHH:mm'),
      transport: mileageForm.value.transport,
      km: mileageForm.value.km,
      from_place: mileageForm.value.from_place,
      to_place: mileageForm.value.to_place,
      note: mileageForm.value.note,
    }
    if (editingMileage.value) {
      await travelApi.updateMileage(editingMileage.value.id, payload)
    } else {
      await travelApi.createMileage(payload)
    }
    message.success('保存成功')
    mileageModalVisible.value = false
    loadMileages()
    loadStats()
  } catch { message.error('操作失败') }
  finally { saving.value = false }
}

async function deleteMileage(id) {
  await travelApi.deleteMileage(id)
  message.success('已删除')
  loadMileages()
  loadStats()
}

// Export/Import
async function handleExportTripJson() {
  try {
    const res = await travelApi.exportTripJson(tripId.value)
    const blob = new Blob([res.data], { type: 'application/json;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${trip.value.name}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { message.error('导出失败') }
}

async function handleExportCsv() {
  try {
    const res = await travelApi.exportCsv(tripId.value)
    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${trip.value.name}_记录.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { message.error('导出失败') }
}

async function handleImportCsv(file) {
  const text = await file.text()
  try {
    const res = await travelApi.importCsv(tripId.value, { csv: text })
    message.success(res.data.message)
    loadAll()
  } catch { message.error('导入失败，请检查文件格式') }
  return false
}

onMounted(loadTrip)
watch(tripId, loadTrip)
</script>

<style scoped>
.travel-detail { max-width: 1200px; }
.detail-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 20px;
}
.header-left h2 { margin: 0 0 8px; font-size: 22px; }
.header-meta { display: flex; gap: 8px; align-items: center; font-size: 13px; color: #64748b; flex-wrap: wrap; }
.tab-content { padding-top: 4px; }
.travel-stat-card {
  border-radius: 10px; color: #fff;
  box-shadow: 0 2px 8px rgba(0,0,0,.1);
  transition: transform 0.2s;
}
.travel-stat-card:hover { transform: translateY(-2px); }
.travel-stat-card :deep(.ant-statistic-title) { color: rgba(255,255,255,.85) !important; }
.travel-stat-card :deep(.ant-statistic-content) { color: #fff !important; }
.travel-stat-card :deep(.ant-statistic-content-value) { color: #fff !important; }
.travel-stat-card :deep(.ant-card-body) { padding: 16px 20px !important; }
.travel-stat-expense { background: linear-gradient(135deg, #f5222d 0%, #ff7a45 100%) !important; }
.travel-stat-count { background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%) !important; }
.travel-stat-avg { background: linear-gradient(135deg, #722ed1 0%, #eb2f96 100%) !important; }
.travel-stat-km { background: linear-gradient(135deg, #2d9a4e 0%, #52c41a 100%) !important; }
.travel-stat-planned { background: linear-gradient(135deg, #1890ff 0%, #36cfc9 100%) !important; }
.travel-stat-percent { background: linear-gradient(135deg, #fa8c16 0%, #fadb14 100%) !important; }
</style>
