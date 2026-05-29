<template>
  <div class="backup-center">
    <a-page-header title="备份中心" sub-title="统一管理所有模块数据" />

    <!-- 数据概览 -->
    <a-card :bordered="false" size="small" class="section-card" :body-style="{ padding: '20px 24px' }">
      <div class="section-title">
        <span class="section-title-icon">📊</span>
        <span>当前数据概览</span>
        <span v-if="dbInfo" class="db-info">
          <a-tag color="blue" class="db-tag">🗄️ {{ dbInfo.name }}</a-tag>
          <a-tag color="cyan" class="db-tag">📁 {{ dbInfo.size_display }}</a-tag>
        </span>
      </div>
      <div class="module-stats-row">
        <div v-for="mod in moduleStats" :key="mod.name" :class="['module-stat', `module-stat-${mod.theme}`]">
          <div class="module-stat-icon">{{ mod.icon }}</div>
          <div class="module-stat-body">
            <div class="module-stat-name">{{ mod.name }}</div>
            <div class="module-stat-count">{{ mod.total }}</div>
          </div>
        </div>
      </div>
    </a-card>

    <!-- 操作区 -->
    <a-row :gutter="16" style="align-items: stretch">
      <!-- 导出备份 -->
      <a-col :xs="24" :sm="12">
        <a-card :bordered="false" size="small" class="section-card action-card" :body-style="{ padding: '24px' }">
          <div class="action-header">
            <div>
              <div class="action-title">
                <span class="action-icon export-icon">📤</span>
                导出备份
              </div>
              <div class="action-desc">将所有模块数据导出为备份文件</div>
            </div>
          </div>

          <a-divider style="margin: 16px 0" />

          <div class="export-info">
            <div class="info-row">
              <span class="info-label">备份格式</span>
              <span class="info-value">JSON / ZIP</span>
            </div>
            <div class="info-row">
              <span class="info-label">覆盖模块</span>
              <span class="info-value">8 个模块</span>
            </div>
            <div class="info-row">
              <span class="info-label">总记录数</span>
              <span class="info-value highlight">{{ totalRecords }} 条</span>
            </div>
            <div class="info-row">
              <span class="info-label">导入策略</span>
              <span class="info-value">合并（跳过已有）</span>
            </div>
          </div>

          <div style="display: flex; gap: 10px; margin-top: 18px">
            <a-button
              type="primary"
              size="large"
              :loading="exporting"
              @click="handleExport"
              class="action-btn export-btn"
              style="flex: 1"
            >
              {{ exporting ? '正在导出...' : '📦 仅数据备份' }}
            </a-button>
            <a-button
              size="large"
              :loading="exportingFull"
              @click="handleExportFull"
              class="action-btn full-export-btn"
              style="flex: 1"
            >
              {{ exportingFull ? '正在导出...' : '💾 完整备份（含文件）' }}
            </a-button>
          </div>
        </a-card>
      </a-col>

      <!-- 导入恢复 -->
      <a-col :xs="24" :sm="12">
        <a-card :bordered="false" size="small" class="section-card action-card" :body-style="{ padding: '24px' }">
          <div class="action-header">
            <div>
              <div class="action-title">
                <span class="action-icon import-icon">📥</span>
                导入恢复
              </div>
              <div class="action-desc">从备份文件恢复数据到系统</div>
            </div>
          </div>

          <a-divider style="margin: 16px 0" />

          <a-upload-dragger
            :before-upload="beforeImport"
            :show-upload-list="false"
            accept=".json,.zip"
            :disabled="importing"
            class="import-dragger"
          >
            <p class="ant-upload-drag-icon">
              <CloudUploadOutlined style="font-size: 40px; color: #6366f1" />
            </p>
            <p class="ant-upload-text">拖拽 JSON / ZIP 备份文件到此处</p>
            <p class="ant-upload-hint">支持 JSON 数据备份 和 ZIP 完整备份</p>
          </a-upload-dragger>

          <a-spin v-if="importing" :spinning="true" tip="正在导入数据..." style="width: 100%">
            <div style="height: 80px"></div>
          </a-spin>

          <!-- 导入结果 -->
          <div v-if="importResult" class="import-result" :class="importResult.success ? 'result-success' : 'result-error'">
            <div class="result-icon">{{ importResult.success ? '✅' : '❌' }}</div>
            <div class="result-msg">{{ importResult.message }}</div>
            <div v-if="importResult.stats" class="result-stats">
              <a-row :gutter="16">
                <a-col :span="8">
                  <div class="stat-item stat-green">
                    <div class="stat-num">{{ importResult.stats.imported }}</div>
                    <div class="stat-lbl">新增</div>
                  </div>
                </a-col>
                <a-col :span="8">
                  <div class="stat-item stat-gray">
                    <div class="stat-num">{{ importResult.stats.skipped }}</div>
                    <div class="stat-lbl">跳过</div>
                  </div>
                </a-col>
                <a-col :span="8">
                  <div class="stat-item stat-red">
                    <div class="stat-num">{{ importResult.stats.errors }}</div>
                    <div class="stat-lbl">失败</div>
                  </div>
                </a-col>
              </a-row>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 数据明细 + 操作记录 -->
    <a-row :gutter="16" style="align-items: stretch">
      <a-col :xs="24" :sm="12">
        <a-card :bordered="false" size="small" class="section-card equal-card" :body-style="{ padding: '20px 24px' }">
          <div class="section-title">
            <span class="section-title-icon">📋</span>
            <span>数据明细</span>
            <span class="table-count">{{ tableDetails.length }} 张表</span>
          </div>
          <div class="detail-scroll">
            <a-table
              :columns="detailColumns"
              :data-source="tableDetails"
              :pagination="false"
              size="small"
              class="detail-table"
              row-key="table"
            >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'module'">
                <span class="module-tag" :style="{ background: record.color + '15', color: record.color }">{{ record.module }}</span>
              </template>
              <template v-if="column.key === 'count'">
                <span class="count-text">{{ record.count }}</span>
              </template>
            </template>
          </a-table>
          </div>
        </a-card>
      </a-col>
      <a-col :xs="24" :sm="12">
        <a-card :bordered="false" size="small" class="section-card equal-card" :body-style="{ padding: '20px 24px' }">
          <div class="section-title">
            <span class="section-title-icon">📝</span>
            <span>操作记录</span>
            <span class="table-count">{{ logs.length }} 条</span>
            <a-button
              v-if="logs.length > 0"
              type="text"
              size="small"
              danger
              class="log-clear-all-btn"
              :loading="clearingLogs"
              @click="handleClearAllLogs"
            >
              <template #icon><DeleteOutlined /></template>
              清除全部
            </a-button>
          </div>
          <div v-if="logs.length === 0" class="log-empty">
            <span style="font-size: 36px">📭</span>
            <div style="color: #94a3b8; font-size: 13px; margin-top: 8px">暂无操作记录</div>
          </div>
          <div v-else class="log-list" ref="logListRef">
            <div v-for="log in logs" :key="log.id" class="log-item">
              <div class="log-item-header">
                <span :class="['log-op-tag', logOpClass(log.operation)]">
                  {{ logOpLabel(log.operation) }}
                </span>
                <div class="log-item-actions">
                  <span class="log-time">{{ formatTime(log.created_at) }}</span>
                  <a-button type="text" size="small" danger class="log-del-btn" @click.stop="handleDeleteLog(log)">
                    <template #icon><DeleteOutlined /></template>
                  </a-button>
                </div>
              </div>
              <div class="log-item-body">
                <div class="log-detail">
                  <div v-if="log.file_name" class="log-file">
                    📄 {{ log.file_name }}
                    <span v-if="log.file_size_display" class="log-file-size">{{ log.file_size_display }}</span>
                  </div>
                  <span v-if="log.operation === 'export'">导出 <b>{{ log.record_count }}</b> 条记录</span>
                  <span v-else>{{ log.detail }}</span>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 清理孤儿文件 -->
    <a-card :bordered="false" size="small" class="section-card" :body-style="{ padding: '24px' }">
      <div class="section-title">
        <span class="section-title-icon">🧹</span>
        <span>清理孤儿文件</span>
        <span class="table-count">存储维护</span>
      </div>
      <div class="cleanup-area">
        <div class="cleanup-info">
          <div class="cleanup-desc">
            扫描 uploads/ 目录，删除骑行、徒步、跑步中已被删除但原始 GPX/FIT 文件仍残留在磁盘上的孤儿文件，释放磁盘空间。
          </div>
          <a-button
            type="primary"
            size="middle"
            :loading="cleaningFiles"
            @click="handleCleanupFiles"
            class="cleanup-btn"
          >
            {{ cleaningFiles ? '扫描中...' : '🧹 立即清理' }}
          </a-button>
        </div>
        <div v-if="cleanupResult" class="cleanup-result">
          <a-alert
            :type="cleanupResult.deleted_count > 0 ? 'success' : 'info'"
            :message="cleanupResult.deleted_count > 0
              ? `清理完成：删除 ${cleanupResult.deleted_count} 个文件，释放 ${cleanupResult.freed_mb} MB`
              : '没有发现孤儿文件，uploads 目录干净'"
            show-icon
          />
        </div>
      </div>
    </a-card>

    <!-- 数据初始化 -->

    <a-card :bordered="false" size="small" class="section-card" :body-style="{ padding: '24px' }">
      <div class="section-title">
        <span class="section-title-icon">⚠️</span>
        <span>数据初始化</span>
        <span class="table-count">危险操作</span>
      </div>
      <div class="reset-area">
        <div class="reset-warning">
          <div class="reset-warning-text">
            <div class="reset-warning-title">清空所有业务数据</div>
            <div class="reset-warning-desc">
              将删除财务、骑行、徒步、跑步、旅行、基金、车辆、物品共 8 个模块的全部数据记录。
              此操作<strong>不可撤销</strong>，请务必先导出备份！
            </div>
          </div>
          <a-button
            type="primary"
            danger
            size="large"
            :loading="resetting"
            @click="handleReset"
            class="reset-btn"
          >
            {{ resetting ? '正在初始化...' : '🗑️ 清空数据' }}
          </a-button>
        </div>
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { CloudUploadOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { backupApi } from '@/api'
import dayjs from 'dayjs'

const exporting = ref(false)
const exportingFull = ref(false)
const importing = ref(false)
const importResult = ref(null)
const resetting = ref(false)
const clearingLogs = ref(false)
const cleaningFiles = ref(false)
const cleanupResult = ref(null)
const tableDetails = ref([])
const dbInfo = ref(null)
const logs = ref([])

const MODULES = [
  { name: '财务管理', icon: '💰', theme: 'blue', color: '#3b82f6', tables: ['finance_accounts', 'finance_transactions', 'finance_bill_imports', 'finance_category_rules', 'asset_snapshots'] },
  { name: '骑行管理', icon: '🚴', theme: 'green', color: '#10b981', tables: ['cycling_activities', 'bikes', 'bike_maintenance'] },
  { name: '徒步管理', icon: '🥾', theme: 'teal', color: '#14b8a6', tables: ['hiking_activities'] },
  { name: '跑步管理', icon: '🏃', theme: 'orange', color: '#f97316', tables: ['running_activities'] },
  { name: '旅行管理', icon: '✈️', theme: 'violet', color: '#8b5cf6', tables: ['travel_trips', 'travel_expenses', 'travel_mileages'] },
  { name: '基金管理', icon: '📊', theme: 'amber', color: '#f59e0b', tables: ['fund_library', 'fund_favorites', 'fund_groups', 'fund_snapshots', 'fund_snapshot_items'] },
  { name: '车辆管理', icon: '🚗', theme: 'rose', color: '#f43f5e', tables: ['vehicles', 'fuel_records', 'vehicle_expenses'] },
  { name: '物品管理', icon: '📦', theme: 'slate', color: '#64748b', tables: ['important_items'] },
]

const TABLE_LABELS = {
  finance_accounts: '财务账户',
  finance_transactions: '收支记录',
  finance_bill_imports: '账单导入批次',
  finance_category_rules: '分类规则',
  asset_snapshots: '资产快照',
  cycling_activities: '骑行活动',
  bikes: '骑行车辆',
  bike_maintenance: '车辆维护',
  hiking_activities: '徒步活动',
  running_activities: '跑步活动',
  travel_trips: '旅行计划',
  travel_expenses: '旅行支出',
  travel_mileages: '旅行里程',
  fund_library: '基金库',
  fund_favorites: '自选基金',
  fund_groups: '基金分组',
  fund_snapshots: '持仓快照',
  fund_snapshot_items: '持仓快照明细',
  vehicles: '机动车',
  fuel_records: '加油/充电记录',
  vehicle_expenses: '车辆费用',
  important_items: '重要物品',
}

const detailColumns = [
  { title: '模块', key: 'module', width: 110 },
  { title: '数据表', dataIndex: 'label', ellipsis: true },
  { title: '表名', dataIndex: 'table', ellipsis: true },
  { title: '记录数', key: 'count', width: 90, align: 'right' },
]


const moduleStats = computed(() => {
  return MODULES.map(mod => {
    const total = tableDetails.value
      .filter(t => mod.tables.includes(t.table))
      .reduce((s, t) => s + t.count, 0)
    return { ...mod, total }
  })
})

const totalRecords = computed(() => {
  return tableDetails.value.reduce((s, t) => s + t.count, 0)
})

async function loadInfo() {
  try {
    const { data } = await backupApi.getInfo()
    const modules = MODULES
    tableDetails.value = (data.tables || []).map(t => {
      const mod = modules.find(m => m.tables.includes(t.table))
      return {
        ...t,
        module: mod?.name || '-',
        label: TABLE_LABELS[t.table] || t.table,
        color: mod?.color || '#6b7280',
      }
    })
    dbInfo.value = data.db || null
  } catch (e) {
    console.error('加载数据信息失败', e)
  }
}

async function loadLogs() {
  try {
    const { data } = await backupApi.getLogs()
    logs.value = data || []
  } catch (e) {
    console.error('加载操作记录失败', e)
  }
}

function formatTime(iso) {
  if (!iso) return ''
  return dayjs(iso).format('YYYY-MM-DD HH:mm')
}

function logOpLabel(op) {
  if (op === 'export') return '📤 数据备份'
  if (op === 'export_full') return '💾 完整备份'
  if (op === 'import_full') return '📥 完整恢复'
  if (op === 'reset') return '🗑️ 数据清空'
  return '📥 数据恢复'
}

function logOpClass(op) {
  if (op === 'export' || op === 'export_full') return 'log-op-export'
  return 'log-op-import'
}

async function handleDeleteLog(log) {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除这条${log.operation === 'export' ? '导出' : '导入'}记录吗？`,
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      try {
        await backupApi.deleteLog(log.id)
        logs.value = logs.value.filter(l => l.id !== log.id)
        message.success('已删除')
      } catch (e) {
        message.error('删除失败')
      }
    },
  })
}

async function handleClearAllLogs() {
  Modal.confirm({
    title: '⚠️ 确认清除全部',
    content: '此操作将删除所有操作记录，且不可撤销。确定要清除全部操作记录吗？',
    okText: '清除全部',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      clearingLogs.value = true
      try {
        const { data } = await backupApi.clearLogs()
        logs.value = []
        message.success(data.message)
      } catch (e) {
        message.error('清除失败：' + (e.response?.data?.detail || e.message))
      } finally {
        clearingLogs.value = false
      }
    },
  })
}

onMounted(() => {
  loadInfo()
  loadLogs()
})

async function handleExport() {
  exporting.value = true
  try {
    const { data } = await backupApi.exportAll()
    const json = JSON.stringify(data, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    // 优先使用后端返回的文件名
    const fileName = data.filename || `allinone_backup_${dayjs().format('YYYY-MM-DD_HHmmss')}.json`

    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = fileName
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 3000)

    loadInfo()
    loadLogs()
  } catch (e) {
    message.error('导出失败：' + (e.response?.data?.detail || e.message))
  } finally {
    exporting.value = false
  }
}

async function handleExportFull() {
  exportingFull.value = true
  try {
    const res = await backupApi.exportFull()
    const blob = res.data
    // 优先读取后端返回的文件名，其次使用本地生成
    const filename = res.headers['x-filename'] || `allinone_full_backup_${dayjs().format('YYYY-MM-DD_HHmmss')}.zip`
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 3000)

    loadInfo()
    loadLogs()
  } catch {
    // 401 由 axios 拦截器处理
  } finally {
    exportingFull.value = false
  }
}

async function beforeImport(file) {
  const isFull = file.name.endsWith('.zip')
  if (!file.name.endsWith('.json') && !isFull) {
    message.error('仅支持 .json 或 .zip 文件')
    return false
  }
  importResult.value = null
  importing.value = true
  try {
    const { data } = isFull ? await backupApi.importFull(file) : await backupApi.importAll(file)
    importResult.value = data
    if (data.success) {
      message.success(data.message)
      // 延迟跳转首页，让用户看到成功提示，强制刷新SPA清除各模块缓存数据
      setTimeout(() => {
        window.location.href = '/'
      }, 800)
    } else {
      message.error(data.message)
    }
  } catch (e) {
    importResult.value = {
      success: false,
      message: e.response?.data?.detail || '导入失败',
    }
  } finally {
    importing.value = false
  }
  return false
}

async function handleReset() {
  Modal.confirm({
    title: '⚠️ 确认初始化',
    content: '此操作将清空所有模块的业务数据，包括财务、骑行、徒步、跑步、旅行、基金、车辆、物品的全部记录。此操作不可撤销！',
    okText: '确认清空',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      resetting.value = true
      try {
        const { data } = await backupApi.resetData()
        message.success(data.message)
        importResult.value = null
        loadInfo()
        loadLogs()
        // 延迟跳转首页，让用户看到成功提示
        setTimeout(() => {
          window.location.href = '/'
        }, 800)
      } catch (e) {
        message.error('初始化失败：' + (e.response?.data?.detail || e.message))
      } finally {
        resetting.value = false
      }
    },
  })
}

async function handleCleanupFiles() {
  cleaningFiles.value = true
  cleanupResult.value = null
  try {
    const { data } = await backupApi.cleanupOrphanFiles()
    cleanupResult.value = data
    if (data.deleted_count > 0) {
      message.success(`清理完成：删除 ${data.deleted_count} 个孤儿文件，释放 ${data.freed_mb} MB`)
    } else {
      message.info('没有发现孤儿文件')
    }
  } catch (e) {
    message.error('清理失败：' + (e.response?.data?.detail || e.message))
  } finally {
    cleaningFiles.value = false
  }
}
</script>

<style scoped>
:deep(.ant-page-header) {
  padding: 0 0 8px;
  margin-bottom: 0 !important;
}

.backup-center {
  padding: 0 8px;
  max-width: 1400px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ===== 通用卡片 ===== */
.section-card {
  border-radius: 14px !important;
  border: 1px solid #f1f5f9 !important;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04) !important;
  transition: box-shadow 0.2s;
  height: 100%;
  display: flex;
  flex-direction: column;
  margin-bottom: 0 !important;
  overflow: hidden;
}
.section-card :deep(.ant-card-body) {
  flex: 1;
  overflow: hidden;
}
.section-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06) !important;
}

/* ===== 标题栏 ===== */
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
  font-weight: 500;
  background: #f8fafc;
  padding: 2px 10px;
  border-radius: 10px;
}

/* ===== 数据库标签 ===== */
.db-info {
  margin-left: auto;
  display: flex;
  gap: 8px;
}
.db-tag {
  border-radius: 8px !important;
  font-size: 12px !important;
  font-weight: 500 !important;
  padding: 1px 10px !important;
  border: none !important;
}

/* ===== 模块统计卡片 ===== */
.module-stats-row {
  display: flex;
  gap: 12px;
  flex-wrap: nowrap;
}
.module-stat {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 12px;
  border: 1px solid transparent;
  transition: all 0.25s;
  cursor: default;
  min-width: 0;
}
.module-stat:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}
.module-stat-icon { font-size: 24px; flex-shrink: 0; }
.module-stat-body { min-width: 0; }
.module-stat-name {
  font-size: 12px;
  color: #94a3b8;
  font-weight: 500;
  margin-bottom: 2px;
  white-space: nowrap;
}
.module-stat-count {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

/* 素雅淡色背景 - 每个模块一个柔和色调 */
.module-stat-blue {
  background: #eff6ff;
  border-color: #dbeafe;
}
.module-stat-blue .module-stat-count { color: #2563eb; }

.module-stat-green {
  background: #ecfdf5;
  border-color: #d1fae5;
}
.module-stat-green .module-stat-count { color: #059669; }

.module-stat-teal {
  background: #f0fdfa;
  border-color: #ccfbf1;
}
.module-stat-teal .module-stat-count { color: #0d9488; }

.module-stat-violet {
  background: #f5f3ff;
  border-color: #ede9fe;
}
.module-stat-violet .module-stat-count { color: #7c3aed; }

.module-stat-amber {
  background: #fffbeb;
  border-color: #fef3c7;
}
.module-stat-amber .module-stat-count { color: #d97706; }

.module-stat-rose {
  background: #fff1f2;
  border-color: #ffe4e6;
}
.module-stat-rose .module-stat-count { color: #e11d48; }

.module-stat-orange {
  background: #fff7ed;
  border-color: #fed7aa;
}
.module-stat-orange .module-stat-count { color: #ea580c; }

.module-stat-slate {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.module-stat-slate .module-stat-count { color: #475569; }

/* ===== 操作卡片 ===== */
.action-card {
  height: 100%;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.action-title {
  font-size: 16px;
  font-weight: 700;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.action-icon { font-size: 20px; }
.action-desc {
  font-size: 13px;
  color: #94a3b8;
  margin-top: 4px;
}
.action-btn {
  border-radius: 10px;
  padding: 0 28px;
  height: 42px;
  font-weight: 600;
  font-size: 14px;
}
.export-btn {
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  border: none;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}
.export-btn:hover {
  background: linear-gradient(135deg, #818cf8 0%, #6366f1 100%) !important;
  box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4) !important;
}
.full-export-btn {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  border: none;
  color: #fff;
  box-shadow: 0 2px 8px rgba(5, 150, 105, 0.3);
}
.full-export-btn:hover {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
  box-shadow: 0 4px 14px rgba(5, 150, 105, 0.4) !important;
}

/* ===== 导出信息 ===== */
.export-info {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
}
.info-label {
  font-size: 13px;
  color: #94a3b8;
}
.info-value {
  font-size: 13px;
  color: #334155;
  font-weight: 600;
}
.info-value.highlight {
  color: #6366f1;
}

/* ===== 导入区域 ===== */
.import-dragger {
  border-radius: 12px !important;
  box-sizing: border-box;
  max-width: 100%;
}
.import-dragger :deep(.ant-upload) {
  width: 100%;
  box-sizing: border-box;
}
.import-dragger :deep(.ant-upload-btn) {
  width: 100%;
  padding: 8px;
  box-sizing: border-box;
}
.import-dragger :deep(.ant-upload-drag) {
  border-radius: 12px;
  border: 2px dashed #e2e8f0;
  background: linear-gradient(135deg, #fafbff 0%, #f8fafc 100%);
  transition: all 0.3s;
  box-sizing: border-box;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.import-dragger :deep(.ant-upload-drag:hover) {
  border-color: #818cf8;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
}
.import-dragger :deep(.ant-upload-text) {
  color: #475569;
  font-weight: 600;
  font-size: 14px;
}
.import-dragger :deep(.ant-upload-hint) {
  color: #94a3b8;
  font-size: 12px;
}

/* ===== 导入结果 ===== */
.import-result {
  margin-top: 16px;
  padding: 16px;
  border-radius: 12px;
}
.result-success { background: #ecfdf5; border: 1px solid #a7f3d0; }
.result-error { background: #fef2f2; border: 1px solid #fecaca; }
.result-icon { font-size: 20px; margin-bottom: 6px; }
.result-msg { font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 12px; }
.result-stats {
  background: rgba(255, 255, 255, 0.6);
  border-radius: 10px;
  padding: 12px;
}
.stat-item { text-align: center; }
.stat-num { font-size: 20px; font-weight: 700; }
.stat-lbl { font-size: 12px; color: #64748b; margin-top: 2px; }
.stat-green .stat-num { color: #059669; }
.stat-gray .stat-num { color: #94a3b8; }
.stat-red .stat-num { color: #ef4444; }

/* ===== 数据明细 & 操作记录（等高两列，高度减半，内容滚动） ===== */
.equal-card {
  max-height: 400px;
  display: flex;
  flex-direction: column;
}
.equal-card :deep(.ant-card-body) {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
/* 数据明细表格内容区滚动 */
.detail-scroll {
  overflow-y: auto;
  max-height: 280px;
  border-radius: 8px;
}
.detail-scroll::-webkit-scrollbar {
  width: 4px;
}
.detail-scroll::-webkit-scrollbar-track {
  background: transparent;
}
.detail-scroll::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}
/* 操作记录列表滚动 */
.log-list {
  overflow-y: auto;
  max-height: 280px;
  padding-right: 4px;
}

/* ===== 数据明细表格 ===== */
.module-tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}
.count-text {
  font-weight: 700;
  color: #6366f1;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
:deep(.detail-table .ant-table) {
  border-radius: 10px;
  overflow: hidden;
}
:deep(.detail-table .ant-table-thead > tr > th) {
  background: linear-gradient(135deg, #f8fafc, #f1f5f9);
  color: #475569;
  font-weight: 600;
  font-size: 13px;
  border-bottom: 1px solid #e2e8f0;
  padding: 10px 14px;
}
:deep(.detail-table .ant-table-tbody > tr > td) {
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
  padding: 10px 14px;
  font-size: 13px;
}
:deep(.detail-table .ant-table-tbody > tr:hover > td) {
  background: #fafbff;
}

/* ===== 操作记录 ===== */
.log-empty {
  text-align: center;
  padding: 60px 0;
}
.log-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.log-list::-webkit-scrollbar {
  width: 4px;
}
.log-list::-webkit-scrollbar-track {
  background: transparent;
}
.log-list::-webkit-scrollbar-thumb {
  background: #e2e8f0;
  border-radius: 2px;
}
.log-item {
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #f1f5f9;
  transition: all 0.2s;
}
.log-item:hover {
  border-color: #e2e8f0;
  background: #f1f5f9;
}
.log-item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}
.log-item-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}
.log-op-tag {
  font-size: 12px;
  font-weight: 600;
  padding: 2px 10px;
  border-radius: 8px;
}
.log-op-export {
  background: linear-gradient(135deg, #ecfdf5, #d1fae5);
  color: #059669;
}
.log-op-import {
  background: linear-gradient(135deg, #eff6ff, #dbeafe);
  color: #2563eb;
}
.log-time {
  font-size: 12px;
  color: #94a3b8;
}
.log-del-btn {
  opacity: 0;
  transition: opacity 0.2s;
}
.log-item:hover .log-del-btn {
  opacity: 1;
}
.log-clear-all-btn {
  font-size: 12px;
  margin-left: 8px;
  padding: 0 8px;
  height: 24px;
  border-radius: 6px;
  color: #f43f5e;
}
.log-clear-all-btn:hover {
  background: #fff1f2;
}
.log-item-body {
  font-size: 13px;
  color: #475569;
  line-height: 1.6;
}
.log-detail b {
  color: #0f172a;
  font-weight: 700;
}
.log-file {
  word-break: break-all;
  margin-bottom: 2px;
}
.log-file-size {
  color: #94a3b8;
  font-size: 12px;
  margin-left: 6px;
}

/* ===== 清理孤儿文件 ===== */
.cleanup-area {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 20px 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.cleanup-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.cleanup-desc {
  flex: 1;
  font-size: 13px;
  color: #166534;
  line-height: 1.6;
}
.cleanup-btn {
  border-radius: 10px;
  padding: 0 24px;
  flex-shrink: 0;
}
.cleanup-result { margin-top: 4px; }

/* ===== 数据初始化 ===== */
.reset-area {
  background: #fff5f5;
  border: 1px solid #fecaca;
  border-radius: 12px;
  padding: 20px 24px;
}
.reset-warning {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.reset-warning-text { flex: 1; }
.reset-warning-title {
  font-size: 15px;
  font-weight: 700;
  color: #991b1b;
  margin-bottom: 4px;
}
.reset-warning-desc {
  font-size: 13px;
  color: #b91c1c;
  line-height: 1.6;
}
.reset-warning-desc strong {
  color: #dc2626;
}
.reset-btn {
  border-radius: 10px;
  padding: 0 28px;
  height: 42px;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}
</style>
