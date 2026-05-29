<template>
  <div class="finance-accounts">
    <!-- 统计卡片 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-card size="small">
          <a-statistic
            title="总资产"
            :value="stats.total_assets"
            :precision="2"
            prefix="¥"
            :value-style="{ color: '#ef4444' }"
          />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic
            title="总负债"
            :value="stats.total_debt"
            :precision="2"
            prefix="¥"
            :value-style="{ color: '#22c55e' }"
          />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic
            title="净资产"
            :value="stats.net_assets"
            :precision="2"
            prefix="¥"
            :value-style="{ color: '#3b82f6' }"
          />
        </a-card>
      </a-col>
      <a-col :span="6">
        <a-card size="small">
          <a-statistic title="账户数量" :value="stats.account_count" suffix="个" />
        </a-card>
      </a-col>
    </a-row>

    <!-- 资产分布图 + 账户列表 -->
    <a-row :gutter="16">
      <!-- 左侧：饼图 -->
      <a-col :span="8">
        <a-card size="small" title="📊 资产分布">
          <div v-if="chartData.length" style="height: 300px">
            <Doughnut :data="chartConfig" :options="chartOptions" />
          </div>
          <a-empty v-else description="暂无数据" style="padding: 40px 0" />
        </a-card>
      </a-col>

      <!-- 右侧：账户列表 -->
      <a-col :span="16">
        <a-card size="small" title="📋 账户列表">
          <template #extra>
            <a-space>
              <a-button type="primary" size="small" @click="showModal()">+ 新增账户</a-button>
              <a-button size="small" @click="onMenuAction({ key: 'export' })">导出备份</a-button>
              <a-button size="small" @click="onMenuAction({ key: 'import' })">导入备份</a-button>
              <a-button size="small" @click="onMenuAction({ key: 'snapshot' })">记录今日快照</a-button>
            </a-space>
          </template>

          <a-table
            :dataSource="visibleAccounts"
            :columns="columns"
            :loading="loading"
            size="small"
            :pagination="false"
            row-key="id"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.dataIndex === 'type'">
                <a-tag :color="record.type_color">
                  {{ record.type_icon }} {{ record.type_label }}
                </a-tag>
              </template>
              <template v-if="column.dataIndex === 'amount'">
                <span :style="{ color: record.type === 'debt' ? '#22c55e' : '#ef4444', fontWeight: 600 }">
                  ¥{{ record.amount.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
                </span>
              </template>
              <template v-if="column.dataIndex === 'actions'">
                <a-space>
                  <a-button type="link" size="small" @click="showModal(record)">编辑</a-button>
                  <a-popconfirm title="确定删除此账户？" @confirm="deleteAccount(record.id)">
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>
    </a-row>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingAccount ? '编辑账户' : '新增账户'"
      @ok="saveAccount"
      :confirmLoading="saving"
      width="480px"
    >
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }" style="margin-top: 16px">
        <a-form-item label="账户名称" required>
          <a-input v-model:value="form.name" placeholder="如：招商银行储蓄卡" />
        </a-form-item>
        <a-form-item label="资产类型" required>
          <a-select v-model:value="form.type">
            <a-select-option v-for="(info, key) in assetTypes" :key="key" :value="key">
              {{ info.icon }} {{ info.label }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="当前金额" required>
          <a-input-number
            v-model:value="form.amount"
            :min="0"
            :precision="2"
            style="width: 100%"
            placeholder="0.00"
          />
        </a-form-item>
        <a-form-item label="机构/平台">
          <a-input v-model:value="form.institution" placeholder="如：招商银行" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="form.notes" :rows="2" placeholder="可选" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 导入弹窗 -->
    <a-modal v-model:open="importVisible" title="导入备份" @ok="doImport" :confirmLoading="importing" width="520px">
      <a-radio-group v-model:value="importMode" style="margin-bottom: 12px">
        <a-radio value="merge">合并（保留现有数据）</a-radio>
        <a-radio value="replace">覆盖（清空现有数据）</a-radio>
      </a-radio-group>
      <a-upload-dragger
        :before-upload="onFileSelected"
        :show-upload-list="selectedFile ? [selectedFile] : false"
        :max-count="1"
        accept=".json"
        style="margin-bottom: 8px"
      >
        <p class="ant-upload-drag-icon"><inbox-outlined /></p>
        <p class="ant-upload-text">点击或拖拽上传 JSON 备份文件</p>
        <p class="ant-upload-hint">支持 allinone 和 money 项目导出的备份文件</p>
      </a-upload-dragger>
      <div v-if="selectedFile" style="margin-bottom: 8px; color: #52c41a">✓ 已选择：{{ selectedFile.name }}</div>
      <a-collapse>
        <a-collapse-panel header="或手动粘贴 JSON">
          <a-textarea v-model:value="importJson" :rows="6" placeholder="粘贴备份 JSON 内容..." />
        </a-collapse-panel>
      </a-collapse>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { useRoute, useRouter } from 'vue-router'
import { InboxOutlined } from '@ant-design/icons-vue'
import { Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend,
} from 'chart.js'
import { financeApi } from '@/api'

ChartJS.register(ArcElement, Tooltip, Legend)

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const accounts = ref([])
const assetTypes = ref({})
const stats = ref({
  total_assets: 0, total_debt: 0, net_assets: 0, account_count: 0
})
const modalVisible = ref(false)
const editingAccount = ref(null)
const form = ref({ name: '', type: 'cash', amount: 0, institution: '', notes: '' })

const importVisible = ref(false)
const importJson = ref('')
const importMode = ref('merge')
const importing = ref(false)
const selectedFile = ref(null)

function onFileSelected(file) {
  selectedFile.value = file
  const reader = new FileReader()
  reader.onload = (e) => {
    importJson.value = e.target.result
  }
  reader.readAsText(file)
  return false // 阻止自动上传
}

const columns = [
  { title: '账户名称', dataIndex: 'name', ellipsis: true },
  { title: '类型', dataIndex: 'type', width: 120 },
  { title: '金额', dataIndex: 'amount', width: 150, align: 'right' },
  { title: '机构', dataIndex: 'institution', ellipsis: true },
  { title: '操作', dataIndex: 'actions', width: 120, align: 'center' },
]

const visibleAccounts = computed(() => accounts.value.filter(a => !a.is_hidden))

const chartData = computed(() => {
  const breakdown = stats.value.asset_breakdown || {}
  return Object.entries(breakdown)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({
      label: assetTypes.value[k]?.label || k,
      value: v,
      color: assetTypes.value[k]?.color || '#6b7280',
    }))
})

const chartConfig = computed(() => ({
  labels: chartData.value.map(d => d.label),
  datasets: [{
    data: chartData.value.map(d => d.value),
    backgroundColor: chartData.value.map(d => d.color),
    borderWidth: 2,
    borderColor: '#fff',
  }],
}))

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { padding: 12, font: { size: 12 } } },
    tooltip: {
      callbacks: {
        label: ctx => `${ctx.label}: ¥${ctx.parsed.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}`,
      },
    },
  },
}

async function loadData() {
  loading.value = true
  try {
    const [accountsRes, statsRes, configRes] = await Promise.all([
      financeApi.listAccounts(),
      financeApi.getStats(),
      financeApi.getConfig(),
    ])
    accounts.value = accountsRes.data
    stats.value = statsRes.data
    assetTypes.value = configRes.data.asset_types
  } catch (e) {
    message.error('加载数据失败')
  } finally {
    loading.value = false
  }
}

function showModal(account = null) {
  editingAccount.value = account
  if (account) {
    form.value = { name: account.name, type: account.type, amount: account.amount, institution: account.institution, notes: account.notes }
  } else {
    form.value = { name: '', type: 'cash', amount: 0, institution: '', notes: '' }
  }
  modalVisible.value = true
}

async function saveAccount() {
  if (!form.value.name || !form.value.type) {
    return message.warning('请填写账户名称和类型')
  }
  saving.value = true
  try {
    if (editingAccount.value) {
      await financeApi.updateAccount(editingAccount.value.id, form.value)
      message.success('更新成功')
    } else {
      await financeApi.createAccount(form.value)
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

async function deleteAccount(id) {
  try {
    await financeApi.deleteAccount(id)
    message.success('删除成功')
    loadData()
  } catch (e) {
    message.error('删除失败')
  }
}

async function onMenuAction({ key }) {
  if (key === 'export') {
    try {
      const res = await financeApi.exportBackup()
      const blob = new Blob([JSON.stringify(res.data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `finance_backup_${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch { message.error('导出失败') }
  } else if (key === 'import') {
    importJson.value = ''
    importMode.value = 'merge'
    importVisible.value = true
  } else if (key === 'snapshot') {
    try {
      const res = await financeApi.createSnapshot()
      message.success(res.data.message)
      loadData()
      // 跳转到快照记录页面
      router.push('/finance/snapshots')
    } catch (e) { message.error(e.response?.data?.message || '操作失败') }
  }
}

async function doImport() {
  if (!importJson.value.trim()) return message.warning('请上传文件或粘贴备份内容')
  importing.value = true
  try {
    const backupData = JSON.parse(importJson.value)
    const res = await financeApi.importBackup({ backup: backupData, mode: importMode.value })
    message.success(res.data.message)
    importVisible.value = false
    selectedFile.value = null
    loadData()
  } catch (e) {
    message.error('导入失败，请检查 JSON 格式')
  } finally {
    importing.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.finance-accounts { max-width: 1400px; }
</style>
