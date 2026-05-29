<template>
  <div class="item-page">
    <!-- 统计卡片 -->
    <a-row :gutter="16" style="margin-bottom: 20px">
      <a-col :span="6">
        <div class="st-card" style="background: linear-gradient(135deg, #818cf8, #6366f1)">
          <div class="st-icon">📦</div>
          <div class="st-info">
            <div class="st-label">物品总数</div>
            <div class="st-val">{{ stats.total }}</div>
          </div>
        </div>
      </a-col>
      <a-col :span="6">
        <div class="st-card" style="background: linear-gradient(135deg, #fbbf24, #f59e0b)">
          <div class="st-icon">⭐</div>
          <div class="st-info">
            <div class="st-label">重要物品</div>
            <div class="st-val">{{ stats.important_count }}</div>
          </div>
        </div>
      </a-col>
      <a-col :span="6">
        <div class="st-card" style="background: linear-gradient(135deg, #f87171, #ef4444)">
          <div class="st-icon">💰</div>
          <div class="st-info">
            <div class="st-label">总估值</div>
            <div class="st-val">¥{{ formatMoney(stats.total_value) }}</div>
          </div>
        </div>
      </a-col>
      <a-col :span="6">
        <div class="st-card" style="background: linear-gradient(135deg, #34d399, #10b981)">
          <div class="st-icon">🛒</div>
          <div class="st-info">
            <div class="st-label">总购入</div>
            <div class="st-val">¥{{ formatMoney(stats.total_cost) }}</div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- 主内容 -->
    <a-row :gutter="16">
      <!-- 左侧分类 -->
      <a-col :span="4">
        <a-card :bordered="false" size="small" class="cat-card">
          <div
            v-for="(info, cat) in categories" :key="cat"
            class="cat-item"
            :class="{ active: filterCategory === cat }"
            @click="filterCategory = filterCategory === cat ? '' : cat"
          >
            <span>{{ info.icon }}</span>
            <span class="cat-name">{{ cat }}</span>
            <span class="cat-count">{{ getCategoryCount(cat) }}</span>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧列表 -->
      <a-col :span="20">
        <a-card :bordered="false" size="small">
          <!-- 工具栏 -->
          <div class="toolbar">
            <a-input-search
              v-model:value="keyword"
              placeholder="搜索物品名称/品牌/位置/编号…"
              style="width: 260px"
              allow-clear
              @search="loadItems"
            />
            <a-select v-model:value="filterStatus" placeholder="状态" allow-clear style="width: 100px" @change="loadItems">
              <a-select-option v-for="s in statusList" :key="s" :value="s">{{ s }}</a-select-option>
            </a-select>
            <a-checkbox v-model:checked="importantOnly" @change="loadItems" style="margin-left: 4px">仅重要</a-checkbox>
            <div style="flex:1"></div>
            <!-- 批量操作（选中时有） -->
            <template v-if="selectedIds.length > 0">
              <span style="color: #6366f1; font-size: 13px; margin-right: 8px">
                已选 {{ selectedIds.length }} 项
              </span>
              <a-button size="small" @click="showBatchStatusModal">🔄 批量改状态</a-button>
              <a-popconfirm title="确认删除所选物品？" @confirm="batchDeleteItems">
                <a-button size="small" danger style="margin-left: 6px">🗑️ 批量删除</a-button>
              </a-popconfirm>
              <a-divider type="vertical" style="margin: 0 8px" />
            </template>
            <a-upload :before-upload="handleImport" :show-upload-list="false" accept=".json">
              <a-button>📤 导入</a-button>
            </a-upload>
            <a-button @click="handleExport" style="margin-left: 8px">📥 导出</a-button>
            <a-button type="primary" @click="showModal()" style="margin-left: 8px">+ 添加物品</a-button>
          </div>

          <!-- 物品网格 -->
          <div v-if="items.length" class="item-grid">
            <div v-for="item in items" :key="item.id" class="item-card" :class="{ 'item-selected': selectedIds.includes(item.id) }">
              <!-- 选择框（阻止冒泡，不触发编辑） -->
              <div class="item-check" @click.stop>
                <a-checkbox :checked="selectedIds.includes(item.id)" @change="toggleSelect(item.id)" />
              </div>
              <!-- 图片区 -->
              <div class="item-photo" @click="showModal(item)">
                <img v-if="item.photo_path" :src="'/' + item.photo_path" :alt="item.name" />
                <div v-else class="item-photo-placeholder">
                  <span style="font-size: 36px">{{ item.category_icon }}</span>
                </div>
                <div v-if="item.is_important" class="item-badge">⭐</div>
                <div class="item-status-tag" :style="{ background: statusColor(item.status) }">
                  {{ item.status }}
                </div>
              </div>
              <!-- 信息区 -->
              <div class="item-info">
                <div class="item-name">{{ item.name }}</div>
                <div class="item-meta">
                  <a-tag :color="item.category_color" size="small" style="margin: 0">
                    {{ item.category_icon }} {{ item.category }}
                  </a-tag>
                  <span v-if="item.brand" class="item-brand">{{ item.brand }}</span>
                </div>
                <div v-if="item.location" class="item-location">
                  📍 {{ item.location }}
                </div>
                <div class="item-values">
                  <span v-if="item.estimated_value > 0" class="item-value">
                    估值 ¥{{ formatMoney(item.estimated_value) }}
                  </span>
                  <span v-if="item.purchase_price > 0" class="item-cost">
                    购入 ¥{{ formatMoney(item.purchase_price) }}
                  </span>
                </div>
              </div>
            </div>
          </div>
          <a-empty v-else description="暂无物品，点击右上角添加" style="padding: 80px 0" />

          <!-- 分页 -->
          <div v-if="total > pageSize" style="text-align: center; margin-top: 16px">
            <a-pagination
              v-model:current="page"
              :total="total"
              :page-size="pageSize"
              size="small"
              @change="loadItems"
            />
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 批量改状态弹窗 -->
    <a-modal v-model:open="batchStatusVisible" title="批量修改状态" @ok="doBatchStatus" :confirmLoading="batchLoading" width="400px">
      <a-form layout="vertical">
        <a-form-item label="将选中的 {{ selectedIds.length }} 件物品修改为">
          <a-select v-model:value="batchStatus">
            <a-select-option v-for="s in statusList" :key="s" :value="s">{{ s }}</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingItem ? '编辑物品' : '添加物品'"
      @ok="saveItem"
      :confirmLoading="saving"
      width="640px"
      :destroyOnClose="true"
    >
      <a-form :model="form" layout="vertical" style="margin-top: 12px">
        <!-- 照片上传 -->
        <a-form-item label="物品照片">
          <div class="photo-upload-area">
            <div v-if="form.photo_path" class="photo-preview">
              <img :src="'/' + form.photo_path" />
              <div class="photo-actions">
                <a-button size="small" danger @click="removePhoto">删除</a-button>
              </div>
            </div>
            <a-upload
              v-else
              :before-upload="handlePhotoUpload"
              :show-upload-list="false"
              accept="image/*"
            >
              <div class="photo-placeholder">
                <plus-outlined style="font-size: 24px; color: #94a3b8" />
                <span style="color: #94a3b8; font-size: 12px">上传照片</span>
              </div>
            </a-upload>
          </div>
        </a-form-item>

        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="物品名称" required>
              <a-input v-model:value="form.name" placeholder="如：MacBook Pro 16寸" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="分类">
              <a-select v-model:value="form.category">
                <a-select-option v-for="(info, cat) in categories" :key="cat" :value="cat">
                  {{ info.icon }} {{ cat }}
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="品牌/型号">
              <a-input v-model:value="form.brand" placeholder="如：Apple" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="状态">
              <a-select v-model:value="form.status">
                <a-select-option v-for="s in statusList" :key="s" :value="s">{{ s }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="购入日期">
              <a-date-picker v-model:value="form.purchase_date" style="width: 100%" valueFormat="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="购入价格 (¥)">
              <a-input-number v-model:value="form.purchase_price" style="width: 100%" :min="0" :precision="2" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="当前估值 (¥)">
              <a-input-number v-model:value="form.estimated_value" style="width: 100%" :min="0" :precision="2" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="序列号/编号">
              <a-input v-model:value="form.serial_number" placeholder="SN / 编号" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="存放位置">
          <a-input v-model:value="form.location" placeholder="如：书房抽屉第二格" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="form.notes" :rows="2" placeholder="可选" />
        </a-form-item>
        <a-form-item>
          <a-checkbox v-model:checked="form.is_important">标记为重要物品</a-checkbox>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 删除确认 -->
    <a-modal
      v-model:open="deleteVisible"
      title="确认删除"
      @ok="confirmDelete"
      ok-text="删除"
      okType="danger"
      cancel-text="取消"
    >
      <p>确定删除「<strong>{{ deletingItem?.name }}</strong>」吗？此操作不可撤销。</p>
    </a-modal>

    <!-- 导入确认 -->
    <a-modal
      v-model:open="importVisible"
      title="导入物品数据"
      @ok="confirmImport"
      :confirmLoading="importing"
      ok-text="确认导入"
      cancel-text="取消"
    >
      <a-alert type="warning" show-icon style="margin-bottom: 16px">
        <template #message>导入将根据物品名称和编号进行去重合并。</template>
      </a-alert>
      <a-radio-group v-model:value="importMode">
        <a-radio value="merge">合并（保留现有，更新重复）</a-radio>
        <a-radio value="overwrite">覆盖（清空现有数据）</a-radio>
      </a-radio-group>
      <p style="margin-top: 12px; color: #64748b">文件：{{ importFileName }}</p>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { itemApi } from '@/api/index'

const categories = ref({})
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 16
const keyword = ref('')
const filterCategory = ref('')
const filterStatus = ref(undefined)
const importantOnly = ref(false)
const stats = ref({ total: 0, important_count: 0, total_value: 0, total_cost: 0 })

const modalVisible = ref(false)
const editingItem = ref(null)
const saving = ref(false)
const form = reactive({
  name: '', category: '其他', brand: '', purchase_date: '', purchase_price: 0,
  estimated_value: 0, serial_number: '', location: '', status: '在用',
  photo_path: '', notes: '', is_important: false,
})

const deleteVisible = ref(false)
const deletingItem = ref(null)

const importVisible = ref(false)
const importing = ref(false)
const importMode = ref('merge')
const importFileName = ref('')
let importData = null

const statusList = ['在用', '闲置', '出借', '已出售']

const catCountMap = ref({})

// 批量选择
const selectedIds = ref([])
const batchStatusVisible = ref(false)
const batchStatus = ref('在用')
const batchLoading = ref(false)

function toggleSelect(id) {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

function showBatchStatusModal() {
  batchStatus.value = '在用'
  batchStatusVisible.value = true
}

async function doBatchStatus() {
  if (!batchStatus.value) return message.warning('请选择状态')
  batchLoading.value = true
  try {
    await itemApi.batchUpdate({ ids: selectedIds.value, status: batchStatus.value })
    message.success('批量修改成功')
    batchStatusVisible.value = false
    selectedIds.value = []
    loadItems()
    loadStats()
  } catch { message.error('批量修改失败') }
  finally { batchLoading.value = false }
}

async function batchDeleteItems() {
  if (!selectedIds.value.length) return
  try {
    await itemApi.batchDelete(selectedIds.value)
    message.success('批量删除成功')
    selectedIds.value = []
    loadItems()
    loadStats()
  } catch { message.error('批量删除失败') }
}

function getCategoryCount(cat) {
  return catCountMap.value[cat] || 0
}

function statusColor(s) {
  const map = { '在用': '#22c55e', '闲置': '#94a3b8', '出借': '#3b82f6', '已出售': '#f59e0b' }
  return map[s] || '#94a3b8'
}

function formatMoney(v) {
  if (!v) return '0.00'
  return Number(v).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

async function loadItems() {
  try {
    const params = {
      page: page.value,
      page_size: pageSize,
    }
    if (keyword.value) params.keyword = keyword.value
    if (filterCategory.value) params.category = filterCategory.value
    if (filterStatus.value) params.status = filterStatus.value
    if (importantOnly.value) params.important_only = true
    const { data } = await itemApi.list(params)
    items.value = data.items || []
    total.value = data.total || 0
  } catch (e) {
    message.error('加载失败')
  }
}

async function loadStats() {
  try {
    const [configRes, statsRes] = await Promise.all([
      itemApi.getConfig(),
      itemApi.getStats(),
    ])
    categories.value = configRes.data.categories || {}
    stats.value = statsRes.data
    // 分类计数
    catCountMap.value = {}
    for (const c of statsRes.data.by_category || []) {
      catCountMap.value[c.category] = c.count
    }
  } catch (e) { /* ignore */ }
}

watch(filterCategory, () => {
  page.value = 1
  loadItems()
})

function showModal(item = null) {
  editingItem.value = item
  if (item) {
    Object.assign(form, {
      name: item.name, category: item.category, brand: item.brand,
      purchase_date: item.purchase_date || null,
      purchase_price: item.purchase_price, estimated_value: item.estimated_value,
      serial_number: item.serial_number, location: item.location, status: item.status,
      photo_path: item.photo_path, notes: item.notes, is_important: item.is_important,
    })
  } else {
    Object.assign(form, {
      name: '', category: '其他', brand: '', purchase_date: null,
      purchase_price: 0, estimated_value: 0, serial_number: '', location: '',
      status: '在用', photo_path: '', notes: '', is_important: false,
    })
  }
  modalVisible.value = true
}

async function handlePhotoUpload(file) {
  const isImage = file.type.startsWith('image/')
  if (!isImage) { message.error('请上传图片文件'); return false }
  if (file.size > 5 * 1024 * 1024) { message.error('图片不能超过 5MB'); return false }
  try {
    const { data } = await itemApi.uploadPhoto(file)
    form.photo_path = data.path
    message.success('照片上传成功')
  } catch (e) {
    message.error('上传失败')
  }
  return false
}

async function removePhoto() {
  if (!form.photo_path) return
  try {
    await itemApi.deletePhoto(form.photo_path)
    form.photo_path = ''
  } catch (e) {
    message.error('删除照片失败')
  }
}

async function saveItem() {
  if (!form.name.trim()) { message.warning('请填写物品名称'); return }
  saving.value = true
  try {
    if (editingItem.value) {
      await itemApi.update(editingItem.value.id, { ...form })
      message.success('更新成功')
    } else {
      await itemApi.create({ ...form })
      message.success('添加成功')
    }
    modalVisible.value = false
    loadItems()
    loadStats()
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

function askDelete(item) {
  deletingItem.value = item
  deleteVisible.value = true
}

async function confirmDelete() {
  if (!deletingItem.value) return
  try {
    await itemApi.delete(deletingItem.value.id)
    message.success('已删除')
    deleteVisible.value = false
    loadItems()
    loadStats()
  } catch (e) {
    message.error('删除失败')
  }
}

async function handleExport() {
  try {
    const { data } = await itemApi.exportJson()
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `物品清单_${new Date().toISOString().slice(0, 10)}.json`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch { /* 401 由拦截器处理 */ }
}

function handleImport(file) {
  importFileName.value = file.name
  const reader = new FileReader()
  reader.onload = (e) => {
    try {
      importData = JSON.parse(e.target.result)
      if (!importData.items || !Array.isArray(importData.items)) {
        message.error('JSON 格式不正确，缺少 items 数组')
        importData = null
        return
      }
      importMode.value = 'merge'
      importVisible.value = true
    } catch {
      message.error('文件解析失败，请确认是有效的 JSON 文件')
      importData = null
    }
  }
  reader.readAsText(file)
  return false
}

async function confirmImport() {
  if (!importData) return
  importing.value = true
  try {
    const { data } = await itemApi.importJson({ mode: importMode.value, items: importData.items })
    message.success(data.message)
    importVisible.value = false
    importData = null
    loadItems()
    loadStats()
  } catch (e) {
    message.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadStats()
  loadItems()
})
</script>

<style scoped>
.item-page { max-width: 1400px; }

/* 统计卡片 */
.st-card {
  border-radius: 14px; padding: 18px 20px;
  display: flex; align-items: center; gap: 14px; color: #fff;
  min-height: 90px; transition: transform 0.2s, box-shadow 0.2s;
}
.st-card:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,0,0,.12); }
.st-icon { font-size: 30px; opacity: 0.9; }
.st-info { flex: 1; }
.st-label { font-size: 13px; opacity: 0.85; margin-bottom: 2px; }
.st-val { font-size: 22px; font-weight: 700; letter-spacing: -0.3px; }

/* 分类侧栏 */
.cat-card { border-radius: 12px; }
.cat-card :deep(.ant-card-body) { padding: 8px 0; }
.cat-item {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; cursor: pointer; border-radius: 8px;
  font-size: 13px; color: #475569; transition: all .15s;
}
.cat-item:hover { background: #f1f5f9; color: #1e293b; }
.cat-item.active { background: #eef2ff; color: #4338ca; font-weight: 600; }
.cat-name { flex: 1; }
.cat-count { font-size: 11px; color: #94a3b8; background: #f1f5f9; padding: 1px 7px; border-radius: 10px; }

/* 工具栏 */
.toolbar {
  display: flex; align-items: center; gap: 8px; margin-bottom: 16px; flex-wrap: wrap;
}

/* 物品网格 */
.item-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}
.item-card {
  border: 1px solid #f1f5f9; border-radius: 12px; overflow: hidden;
  transition: all .2s; background: #fff; position: relative;
}
.item-card:hover { border-color: #c7d2fe; box-shadow: 0 4px 16px rgba(0,0,0,.06); transform: translateY(-2px); }
.item-card.item-selected { border-color: #6366f1 !important; box-shadow: 0 0 0 2px rgba(99,102,241,.15); }
.item-check {
  position: absolute; top: 6px; left: 6px; z-index: 2;
  background: rgba(255,255,255,.9); border-radius: 4px; padding: 2px;
  opacity: 0; transition: opacity .15s;
}
.item-card:hover .item-check,
.item-card.item-selected .item-check { opacity: 1; }
.item-photo { cursor: pointer; }

.item-photo {
  height: 140px; position: relative; overflow: hidden; background: #f8fafc;
}
.item-photo img { width: 100%; height: 100%; object-fit: cover; }
.item-photo-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #f1f5f9, #e2e8f0);
}
.item-badge { position: absolute; top: 6px; right: 6px; font-size: 16px; }
.item-status-tag {
  position: absolute; bottom: 6px; right: 6px;
  color: #fff; font-size: 11px; padding: 1px 8px; border-radius: 10px; font-weight: 500;
}

.item-info { padding: 12px; }
.item-name { font-size: 14px; font-weight: 600; color: #1e293b; margin-bottom: 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-meta { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; }
.item-brand { font-size: 12px; color: #64748b; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-location { font-size: 12px; color: #64748b; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.item-values { display: flex; justify-content: space-between; }
.item-value { font-size: 13px; font-weight: 600; color: #e11d48; }
.item-cost { font-size: 12px; color: #94a3b8; }

/* 照片上传 */
.photo-upload-area { width: 200px; }
.photo-preview { position: relative; width: 200px; height: 150px; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; }
.photo-preview img { width: 100%; height: 100%; object-fit: cover; }
.photo-actions { position: absolute; bottom: 0; left: 0; right: 0; background: rgba(0,0,0,.5); text-align: center; padding: 4px; }
.photo-placeholder {
  width: 200px; height: 150px; border: 2px dashed #d1d5db; border-radius: 8px;
  display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; cursor: pointer;
}
.photo-placeholder:hover { border-color: #6366f1; background: #faf5ff; }
</style>
