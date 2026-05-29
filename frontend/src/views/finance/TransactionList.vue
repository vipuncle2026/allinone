<template>
  <div class="finance-records">
    <!-- 筛选栏 -->
    <a-card size="small" style="margin-bottom: 16px">
      <a-space wrap>
        <a-select
          v-model:value="filters.source"
          placeholder="来源"
          allow-clear
          style="width: 100px"
          size="small"
          @change="loadData"
        >
          <a-select-option value="manual">手动</a-select-option>
          <a-select-option value="alipay">支付宝</a-select-option>
          <a-select-option value="wechat">微信</a-select-option>
        </a-select>
        <a-select
          v-model:value="filters.type"
          placeholder="收支类型"
          allow-clear
          style="width: 100px"
          size="small"
          @change="loadData"
        >
          <a-select-option value="income">收入</a-select-option>
          <a-select-option value="expense">支出</a-select-option>
        </a-select>
        <a-select
          v-model:value="filters.category"
          placeholder="分类"
          allow-clear
          style="width: 120px"
          size="small"
          @change="loadData"
        >
          <a-select-option v-for="c in currentCategories" :key="c" :value="c">{{ c }}</a-select-option>
        </a-select>
        <a-button size="small" @click="showCategoryModal" title="管理分类">
          <template #icon><SettingOutlined /></template>
        </a-button>
        <a-range-picker
          v-model:value="dateRange"
          size="small"
          style="width: 220px"
          @change="onDateChange"
        />
        <a-input-search
          v-model:value="filters.keyword"
          placeholder="搜索描述"
          size="small"
          style="width: 150px"
          @search="loadData"
          allow-clear
        />
        <a-button size="small" @click="resetFilters">重置</a-button>
      </a-space>
    </a-card>

    <!-- 月度收支汇总 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="本月收入" :value="stats.month_income" :precision="2" prefix="¥"
            :value-style="{ color: '#ef4444' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="本月支出" :value="stats.month_expense" :precision="2" prefix="¥"
            :value-style="{ color: '#22c55e' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="本月结余" :value="stats.month_income - stats.month_expense" :precision="2" prefix="¥"
            :value-style="{ color: (stats.month_income - stats.month_expense) >= 0 ? '#3b82f6' : '#ef4444' }" />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <div style="display: flex; justify-content: space-between; align-items: center; height: 100%">
            <a-statistic title="筛选结果" :value="pagination.total" suffix="条" />
            <a-button type="primary" size="small" @click="showModal()">+ 新增记录</a-button>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 记录列表 -->
    <a-card size="small">
      <a-table
        :dataSource="records"
        :columns="columns"
        :loading="loading"
        size="small"
        row-key="id"
        :pagination="{
          current: pagination.page,
          pageSize: pagination.limit,
          total: pagination.total,
          showSizeChanger: false,
          showTotal: t => `共 ${t} 条`,
          onChange: onPageChange,
        }"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'type'">
            <a-tag v-if="record.is_transfer" color="default" size="small">转账</a-tag>
            <a-tag v-else :color="record.type === 'income' ? 'red' : 'green'">
              {{ record.type === 'income' ? '收入' : '支出' }}
            </a-tag>
          </template>
          <template v-if="column.key === 'source'">
            <a-tag v-if="record.source === 'alipay'" color="#1677ff" size="small">支</a-tag>
            <a-tag v-else-if="record.source === 'wechat'" color="#22c55e" size="small">微</a-tag>
            <a-tag v-else color="default" size="small">手</a-tag>
          </template>
          <template v-if="column.dataIndex === 'amount'">
            <span :style="{
              color: record.type === 'income' ? '#ef4444' : '#22c55e',
              fontWeight: 600,
              fontSize: '14px',
            }">
              {{ record.type === 'income' ? '+' : '-' }}¥{{
                record.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
              }}
            </span>
          </template>
          <template v-if="column.dataIndex === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="showModal(record)">编辑</a-button>
              <a-popconfirm title="确定删除此记录？" @confirm="deleteRecord(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingRecord ? '编辑记录' : '新增记录'"
      @ok="saveRecord"
      :confirmLoading="saving"
      width="480px"
    >
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }" style="margin-top: 16px">
        <a-form-item label="收支类型" required>
          <a-radio-group v-model:value="form.type" button-style="solid" @change="form.category = ''">
            <a-radio-button value="expense">支出</a-radio-button>
            <a-radio-button value="income">收入</a-radio-button>
          </a-radio-group>
        </a-form-item>
        <a-form-item label="分类" required>
          <a-select v-model:value="form.category" placeholder="选择分类">
            <a-select-option v-for="c in currentCategories" :key="c" :value="c">{{ c }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="金额" required>
          <a-input-number v-model:value="form.amount" :min="0.01" :precision="2" style="width: 100%" placeholder="0.00" />
        </a-form-item>
        <a-form-item label="日期" required>
          <a-date-picker v-model:value="form.dateObj" style="width: 100%" valueFormat="YYYY-MM-DD" />
        </a-form-item>
        <a-form-item label="关联账户">
          <a-select v-model:value="form.account_id" allow-clear placeholder="可选">
            <a-select-option v-for="a in accountList" :key="a.id" :value="a.id">
              {{ a.type_icon }} {{ a.name }} (¥{{ a.amount.toLocaleString() }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="form.description" :rows="2" placeholder="备注说明" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 分类管理弹窗 -->
    <a-modal
      v-model:open="categoryModalVisible"
      title="分类管理"
      :footer="null"
      width="460px"
    >
      <a-tabs v-model:activeKey="categoryTab">
        <a-tab-pane key="expense" tab="支出分类">
          <div class="cat-list">
            <div v-for="c in categories.expense" :key="c" class="cat-item">
              <span class="cat-name">{{ c }}</span>
              <a-space size="small">
                <a-button type="link" size="small" @click="startRename('expense', c)">重命名</a-button>
                <a-popconfirm :title="`删除「${c}」分类？已有记录将归为「其他支出」`" @confirm="handleDeleteCategory('expense', c)">
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </div>
          </div>
          <div class="cat-add">
            <a-input v-model:value="newCategoryName" placeholder="输入新分类名" size="small" @pressEnter="handleAddCategory('expense')">
              <template #append>
                <a-button type="primary" size="small" @click="handleAddCategory('expense')">添加</a-button>
              </template>
            </a-input>
          </div>
        </a-tab-pane>
        <a-tab-pane key="income" tab="收入分类">
          <div class="cat-list">
            <div v-for="c in categories.income" :key="c" class="cat-item">
              <span class="cat-name">{{ c }}</span>
              <a-space size="small">
                <a-button type="link" size="small" @click="startRename('income', c)">重命名</a-button>
                <a-popconfirm :title="`删除「${c}」分类？已有记录将归为「其他收入」`" @confirm="handleDeleteCategory('income', c)">
                  <a-button type="link" size="small" danger>删除</a-button>
                </a-popconfirm>
              </a-space>
            </div>
          </div>
          <div class="cat-add">
            <a-input v-model:value="newCategoryName" placeholder="输入新分类名" size="small" @pressEnter="handleAddCategory('income')">
              <template #append>
                <a-button type="primary" size="small" @click="handleAddCategory('income')">添加</a-button>
              </template>
            </a-input>
          </div>
        </a-tab-pane>
      </a-tabs>
    </a-modal>

    <!-- 重命名弹窗 -->
    <a-modal
      v-model:open="renameModalVisible"
      title="重命名分类"
      @ok="handleRename"
      :confirmLoading="renaming"
      width="360px"
    >
      <div style="margin-top: 16px">
        <div style="margin-bottom: 8px; color: #94a3b8">原名称：{{ renameOldName }}</div>
        <a-input v-model:value="renameNewName" placeholder="输入新名称" @pressEnter="handleRename" />
      </div>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { SettingOutlined } from '@ant-design/icons-vue'
import { financeApi } from '@/api'

const loading = ref(false)
const saving = ref(false)
const records = ref([])
const accountList = ref([])
const categories = ref({ income: [], expense: [] })
const stats = ref({ month_income: 0, month_expense: 0 })

const pagination = ref({ page: 1, limit: 20, total: 0 })
const filters = ref({ type: undefined, category: undefined, keyword: '', source: undefined })
const dateRange = ref(null)

const modalVisible = ref(false)
const editingRecord = ref(null)
const form = ref({
  type: 'expense', category: '', amount: null, date: '', dateObj: '',
  account_id: undefined, description: '',
})

// 分类管理相关
const categoryModalVisible = ref(false)
const categoryTab = ref('expense')
const newCategoryName = ref('')
const renameModalVisible = ref(false)
const renameType = ref('expense')
const renameOldName = ref('')
const renameNewName = ref('')
const renaming = ref(false)

const currentCategories = computed(() => {
  return categories.value[form.value.type] || []
})

const columns = [
  { title: '日期', dataIndex: 'date', width: 100 },
  { title: '类型', key: 'type', width: 80 },
  { title: '分类', dataIndex: 'category', width: 100 },
  { title: '金额', dataIndex: 'amount', width: 120, align: 'right' },
  { title: '来源', key: 'source', width: 70, align: 'center' },
  { title: '交易对方', dataIndex: 'counterparty', width: 120, ellipsis: true },
  { title: '描述', dataIndex: 'description', ellipsis: true },
  { title: '操作', dataIndex: 'actions', width: 120, align: 'center' },
]

async function loadData() {
  loading.value = true
  try {
    const params = {
      page: pagination.value.page,
      limit: pagination.value.limit,
    }
    if (filters.value.type) params.type = filters.value.type
    if (filters.value.category) params.category = filters.value.category
    if (filters.value.keyword) params.keyword = filters.value.keyword
    if (filters.value.source) params.source = filters.value.source
    if (dateRange.value && dateRange.value[0]) {
      params.start_date = dateRange.value[0].format('YYYY-MM-DD')
      params.end_date = dateRange.value[1].format('YYYY-MM-DD')
    }

    const [txRes, statsRes] = await Promise.all([
      financeApi.listTransactions(params),
      financeApi.getStats(),
    ])

    records.value = txRes.data.items
    pagination.value.total = txRes.data.total
    stats.value = statsRes.data
  } catch (e) {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

async function loadAccounts() {
  try {
    const res = await financeApi.listAccounts()
    accountList.value = res.data
  } catch { /* ignore */ }
}

async function loadConfig() {
  try {
    const res = await financeApi.getConfig()
    categories.value = {
      income: res.data.income_categories,
      expense: res.data.expense_categories,
    }
  } catch { /* ignore */ }
}

function onPageChange(page) {
  pagination.value.page = page
  loadData()
}

function onDateChange() {
  pagination.value.page = 1
  loadData()
}

function resetFilters() {
  filters.value = { type: undefined, category: undefined, keyword: '', source: undefined }
  dateRange.value = null
  pagination.value.page = 1
  loadData()
}

function showModal(record = null) {
  editingRecord.value = record
  if (record) {
    form.value = {
      type: record.type,
      category: record.category,
      amount: record.amount,
      date: record.date,
      dateObj: record.date,
      account_id: record.account_id,
      description: record.description,
    }
  } else {
    form.value = {
      type: 'expense', category: '', amount: null, date: '', dateObj: '',
      account_id: undefined, description: '',
    }
  }
  modalVisible.value = true
}

async function saveRecord() {
  if (!form.value.type || !form.value.category || !form.value.amount || !form.value.dateObj) {
    return message.warning('请填写必要字段')
  }
  saving.value = true
  try {
    const data = {
      type: form.value.type,
      category: form.value.category,
      amount: form.value.amount,
      date: form.value.dateObj,
      description: form.value.description,
      account_id: form.value.account_id || null,
    }
    if (editingRecord.value) {
      await financeApi.updateTransaction(editingRecord.value.id, data)
      message.success('更新成功')
    } else {
      await financeApi.createTransaction(data)
      message.success('创建成功')
    }
    modalVisible.value = false
    loadData()
  } catch (e) {
    message.error('操作失败')
  } finally {
    saving.value = false
  }
}

async function deleteRecord(id) {
  try {
    await financeApi.deleteTransaction(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

// ─── 分类管理 ───────────────────────────────────────

function showCategoryModal() {
  categoryModalVisible.value = true
  newCategoryName.value = ''
}

async function handleAddCategory(type) {
  const name = newCategoryName.value.trim()
  if (!name) return
  const key = type === 'expense' ? 'expense_categories' : 'income_categories'
  const cats = [...categories.value[type]]
  if (cats.includes(name)) {
    return message.warning('分类已存在')
  }
  cats.push(name)
  try {
    await financeApi.updateCategories({
      income_categories: type === 'income' ? cats : categories.value.income,
      expense_categories: type === 'expense' ? cats : categories.value.expense,
    })
    categories.value[type] = cats
    newCategoryName.value = ''
    message.success('分类已添加')
  } catch (e) {
    message.error('添加失败')
  }
}

function startRename(type, name) {
  renameType.value = type
  renameOldName.value = name
  renameNewName.value = name
  renameModalVisible.value = true
}

async function handleRename() {
  const newName = renameNewName.value.trim()
  if (!newName || newName === renameOldName.value) {
    renameModalVisible.value = false
    return
  }
  renaming.value = true
  try {
    const res = await financeApi.renameCategory({
      old_name: renameOldName.value,
      new_name: newName,
      txn_type: renameType.value,
    })
    message.success(res.data.message || '重命名成功')
    renameModalVisible.value = false
    // 刷新分类列表和数据
    await loadConfig()
    loadData()
  } catch (e) {
    message.error('重命名失败')
  } finally {
    renaming.value = false
  }
}

async function handleDeleteCategory(type, name) {
  try {
    const res = await financeApi.deleteCategory({
      category: name,
      txn_type: type,
    })
    message.success(res.data.message || '分类已删除')
    await loadConfig()
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadConfig()
  loadAccounts()
  loadData()
})
</script>

<style scoped>
.finance-records { max-width: 1400px; }
.cat-list {
  max-height: 320px;
  overflow-y: auto;
  margin-bottom: 12px;
}
.cat-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  border-radius: 8px;
  transition: background 0.2s;
}
.cat-item:hover {
  background: #f8fafc;
}
.cat-name {
  font-size: 14px;
  color: #334155;
}
.cat-add {
  padding-top: 8px;
  border-top: 1px solid #f1f5f9;
}
</style>
