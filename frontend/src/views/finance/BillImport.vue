<template>
  <div class="bill-import">
    <!-- 上传区域 -->
    <a-card :bordered="false" size="small" class="section-card">
      <div class="section-title">
        <span class="section-title-icon">📤</span>
        <span>上传账单</span>
      </div>
      <a-upload-dragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        accept=".csv,.xlsx"
        :disabled="parsing"
        class="upload-dragger"
      >
        <p class="ant-upload-drag-icon">
          <CloudUploadOutlined style="font-size: 48px; color: #6366f1" />
        </p>
        <p class="ant-upload-text">拖拽支付宝 / 微信账单文件到此处</p>
        <p class="ant-upload-hint">
          支持支付宝（CSV）和微信支付（CSV/XLSX）官方导出账单
        </p>
      </a-upload-dragger>
    </a-card>

    <!-- 解析结果 -->
    <a-spin :spinning="parsing" tip="正在解析账单...">
      <!-- 统计概览 -->
      <a-card v-if="parseResult" :bordered="false" size="small" class="section-card" style="margin-top: 16px">
        <div class="section-title">
          <span class="section-title-icon">📊</span>
          <span>解析结果 — {{ parseResult.source_label }}</span>
        </div>
        <a-row :gutter="12" style="margin-bottom: 16px">
          <a-col :span="5">
            <a-statistic title="总记录" :value="parseResult.stats.total" />
          </a-col>
          <a-col :span="5">
            <a-statistic title="可导入" :value="parseResult.stats.new" value-style="color: #22c55e" />
          </a-col>
          <a-col :span="5">
            <a-statistic title="重复跳过" :value="parseResult.stats.duplicate" value-style="color: #f59e0b" />
          </a-col>
          <a-col :span="5">
            <a-statistic title="待分类" :value="parseResult.stats.unclassified" value-style="color: #8b5cf6" />
          </a-col>
          <a-col :span="4">
            <a-statistic title="转账类" :value="parseResult.stats.transfer" value-style="color: #94a3b8" />
          </a-col>
        </a-row>

        <!-- 预览表格 -->
        <div class="preview-table-wrap">
          <a-table
            :dataSource="parseResult.preview"
            :columns="previewColumns"
            size="small"
            row-key="trade_no"
            :pagination="false"
            :scroll="{ y: 400 }"
            class="preview-table"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'amount'">
                <span :style="{ color: record.type === 'income' ? '#ef4444' : '#22c55e', fontWeight: 600 }">
                  {{ record.type === 'income' ? '+' : '-' }}¥{{ record.amount.toFixed(2) }}
                </span>
              </template>
              <template v-if="column.key === 'type'">
                <a-tag v-if="record.is_transfer" color="default">转账</a-tag>
                <a-tag v-else :color="record.type === 'income' ? 'red' : 'green'">
                  {{ record.type === 'income' ? '收入' : '支出' }}
                </a-tag>
              </template>
              <template v-if="column.key === 'category'">
                <a-tag v-if="!record.category || record.category.includes('其他')" color="default">待分类</a-tag>
                <span v-else>{{ record.category }}</span>
              </template>
              <template v-if="column.key === 'status'">
                <a-tag v-if="record.is_duplicate" color="warning">重复</a-tag>
                <a-tag v-else color="success">新增</a-tag>
              </template>
            </template>
          </a-table>
          <div v-if="parseResult.stats.new > 50" class="preview-tip">
            仅预览前 50 条，共 {{ parseResult.stats.new }} 条可导入
          </div>
        </div>

        <!-- 操作按钮 -->
        <div style="display: flex; gap: 12px; margin-top: 16px; justify-content: flex-end">
          <a-button @click="resetAll">取消</a-button>
          <a-button
            type="primary"
            :disabled="parseResult.stats.new === 0"
            :loading="importing"
            @click="confirmImport"
            style="background: #6366f1; border-color: #6366f1"
          >
            {{ importing ? '导入中...' : `确认导入 ${parseResult.stats.new} 条` }}
          </a-button>
        </div>
      </a-card>
    </a-spin>

    <!-- 导入结果 -->
    <a-card v-if="importResult" :bordered="false" size="small" class="section-card" style="margin-top: 16px">
      <a-result
        status="success"
        :title="importResult.message"
        style="padding: 16px 0"
      />
    </a-card>

    <!-- 历史导入记录 -->
    <a-card :bordered="false" size="small" class="section-card" style="margin-top: 16px">
      <div class="section-title">
        <span class="section-title-icon">📋</span>
        <span>导入记录</span>
        <span class="table-count">{{ importHistory.length }} 条</span>
        <a-button type="text" size="small" @click="loadHistory" style="margin-left: 8px">刷新</a-button>
      </div>
      <a-table
        :dataSource="importHistory"
        :columns="historyColumns"
        size="small"
        row-key="id"
        :pagination="false"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'source'">
            <a-tag :color="record.source === 'alipay' ? '#1677ff' : '#22c55e'">
              {{ record.source_label }}
            </a-tag>
          </template>
          <template v-if="column.key === 'status'">
            <a-badge :status="record.status === 'completed' ? 'success' : record.status === 'failed' ? 'error' : 'default'"
              :text="record.status === 'completed' ? '完成' : record.status === 'failed' ? '失败' : '待处理'" />
          </template>
          <template v-if="column.key === 'actions'">
            <a-popconfirm title="确定删除此批次及其所有导入记录？" @confirm="deleteImport(record.id)">
              <a-button type="link" size="small" danger>删除</a-button>
            </a-popconfirm>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { CloudUploadOutlined } from '@ant-design/icons-vue'
import { financeApi } from '@/api'
import dayjs from 'dayjs'

const parsing = ref(false)
const importing = ref(false)
const parseResult = ref(null)
const importResult = ref(null)
const importHistory = ref([])
const cacheKey = ref('')

const previewColumns = [
  { title: '状态', key: 'status', width: 70, align: 'center' },
  { title: '日期', dataIndex: 'date', width: 100 },
  { title: '类型', key: 'type', width: 70, align: 'center' },
  { title: '金额', key: 'amount', width: 120, align: 'right' },
  { title: '分类', key: 'category', width: 90 },
  { title: '交易对方', dataIndex: 'counterparty', ellipsis: true },
  { title: '描述', dataIndex: 'description', ellipsis: true },
]

const historyColumns = [
  { title: '来源', key: 'source', width: 90 },
  { title: '文件名', dataIndex: 'file_name', ellipsis: true },
  { title: '总数', dataIndex: 'total_count', width: 60, align: 'center' },
  { title: '导入', dataIndex: 'imported_count', width: 60, align: 'center' },
  { title: '跳过', dataIndex: 'skipped_count', width: 60, align: 'center' },
  { title: '失败', dataIndex: 'failed_count', width: 60, align: 'center' },
  { title: '状态', key: 'status', width: 80, align: 'center' },
  { title: '时间', dataIndex: 'created_at', width: 150 },
  { title: '操作', key: 'actions', width: 70, align: 'center' },
]

async function beforeUpload(file) {
  if (!file.name.endsWith('.csv') && !file.name.endsWith('.xlsx')) {
    message.error('仅支持 CSV 或 XLSX 文件')
    return false
  }
  parsing.value = true
  importResult.value = null
  try {
    const { data } = await financeApi.parseBill(file)
    parseResult.value = data
    cacheKey.value = data.cache_key
    if (data.stats.new === 0) {
      message.info('没有新的可导入记录')
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '解析失败，请确认文件格式')
    parseResult.value = null
  } finally {
    parsing.value = false
  }
  return false
}

async function confirmImport() {
  if (!cacheKey.value) return
  importing.value = true
  try {
    const { data } = await financeApi.confirmBillImport(cacheKey.value, [])
    importResult.value = data
    message.success(data.message)
    parseResult.value = null
    cacheKey.value = ''
    loadHistory()
  } catch (e) {
    message.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

function resetAll() {
  parseResult.value = null
  importResult.value = null
  cacheKey.value = ''
}

async function loadHistory() {
  try {
    const { data } = await financeApi.listBillImports()
    importHistory.value = data
  } catch { /* ignore */ }
}

async function deleteImport(id) {
  try {
    const { data } = await financeApi.deleteBillImport(id)
    message.success(data.message)
    loadHistory()
  } catch (e) {
    message.error('删除失败')
  }
}

onMounted(() => {
  loadHistory()
})
</script>

<style scoped>
.bill-import {
  max-width: 1400px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.section-card {
  border-radius: 14px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
  transition: box-shadow 0.2s;
}
.section-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title-icon { font-size: 16px; }
.table-count {
  margin-left: auto;
  font-size: 12px;
  color: #94a3b8;
  background: #f8fafc;
  padding: 2px 10px;
  border-radius: 10px;
}
.upload-dragger :deep(.ant-upload) {
  width: 100%;
}
.upload-dragger :deep(.ant-upload-drag) {
  border-radius: 14px;
  border: 2px dashed #e2e8f0;
  background: linear-gradient(135deg, #fafbff, #f8fafc);
  padding: 40px 0;
  transition: all 0.3s;
}
.upload-dragger :deep(.ant-upload-drag:hover) {
  border-color: #818cf8;
  background: linear-gradient(135deg, #eef2ff, #f8fafc);
}
.preview-table-wrap {
  max-height: 460px;
  overflow: hidden;
}
.preview-tip {
  text-align: center;
  padding: 8px;
  color: #94a3b8;
  font-size: 12px;
}
:deep(.preview-table .ant-table) {
  border-radius: 10px;
  overflow: hidden;
}
:deep(.preview-table .ant-table-thead > tr > th) {
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  color: #475569;
  font-weight: 600;
  font-size: 13px;
}
:deep(.preview-table .ant-table-tbody > tr:hover > td) {
  background: #fafbff;
}
</style>
