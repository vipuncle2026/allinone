<template>
  <div class="health-checkup">
    <div class="toolbar">
      <a-select v-model:value="filterMember" placeholder="全部成员" allow-clear style="width: 140px" @change="load">
        <a-select-option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</a-select-option>
      </a-select>
      <a-select v-model:value="filterYear" placeholder="全部年份" allow-clear style="width: 120px" @change="load">
        <a-select-option v-for="y in years" :key="y" :value="y">{{ y }} 年</a-select-option>
      </a-select>
      <a-input-search v-model:value="keyword" placeholder="搜索机构/结论…" style="width: 200px" allow-clear @search="load" />
      <div style="flex: 1"></div>
      <a-button type="primary" :disabled="!members.length" @click="openModal()">+ 新增体检</a-button>
    </div>

    <a-table
      :data-source="list" :columns="columns" :loading="loading"
      row-key="id" size="middle" :pagination="{ pageSize: 10, hideOnSinglePage: true }"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'date'">
          <span class="mono">{{ record.checkup_date }}</span>
        </template>
        <template v-else-if="column.key === 'type'">
          <a-tag :bordered="false">{{ record.checkup_type }}</a-tag>
        </template>
        <template v-else-if="column.key === 'items'">
          <span>{{ record.item_count }} 项</span>
          <a-tag v-if="record.abnormal_count > 0" color="red" :bordered="false" style="margin-left: 6px">
            异常 {{ record.abnormal_count }}
          </a-tag>
          <a-tag v-else-if="record.item_count > 0" color="green" :bordered="false" style="margin-left: 6px">正常</a-tag>
        </template>
        <template v-else-if="column.key === 'cost'">
          <span class="mono">{{ record.cost ? '¥' + Number(record.cost).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) : '-' }}</span>
        </template>
        <template v-else-if="column.key === 'attach'">
          <a-badge :count="record.attachments?.length || 0" :show-zero="false">
            <span class="attach-icon">📎</span>
          </a-badge>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button type="link" size="small" @click="openDetail(record)">详情</a-button>
          <a-button type="link" size="small" @click="openModal(record)">编辑</a-button>
          <a-popconfirm title="删除该体检记录及其指标、报告？" @confirm="remove(record)">
            <a-button type="link" size="small" danger>删除</a-button>
          </a-popconfirm>
        </template>
      </template>
    </a-table>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalOpen" :title="form.id ? '编辑体检记录' : '新增体检记录'"
      :width="820" @ok="submit" :confirm-loading="saving" ok-text="保存"
    >
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="6">
            <a-form-item label="成员" required>
              <a-select v-model:value="form.member_id" style="width: 100%">
                <a-select-option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="体检日期" required>
              <a-input v-model:value="form.checkup_date" placeholder="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="类型">
              <a-select v-model:value="form.checkup_type" style="width: 100%">
                <a-select-option v-for="t in checkupTypes" :key="t" :value="t">{{ t }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="6">
            <a-form-item label="体检机构">
              <a-input v-model:value="form.hospital" placeholder="医院/体检中心" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="6">
            <a-form-item label="体检花费">
              <a-input-number
                v-model:value="form.cost" :min="0" :precision="2" style="width: 100%"
                placeholder="0.00" :formatter="(v) => v ? `¥ ${v}` : ''" :parser="(v) => v.replace(/[^\d.]/g, '')"
              />
            </a-form-item>
          </a-col>
          <a-col :span="18">
            <a-form-item label="备注">
              <a-input v-model:value="form.notes" placeholder="可选，如体检套餐名称、报销信息" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="体检总评/结论">
          <a-textarea v-model:value="form.summary" :rows="2" placeholder="如：总体正常，血脂偏高" />
        </a-form-item>

        <div class="items-head">
          <span class="items-title">体检指标</span>
          <a-button size="small" type="dashed" @click="addItem">+ 添加指标</a-button>
        </div>
        <div v-if="form.items.length" class="items-table">
          <div class="items-row items-row-head">
            <span class="c-name">指标名称</span>
            <span class="c-cat">分类</span>
            <span class="c-val">数值</span>
            <span class="c-unit">单位</span>
            <span class="c-ref">参考范围</span>
            <span class="c-flag">标记</span>
            <span class="c-op"></span>
          </div>
          <div v-for="(it, idx) in form.items" :key="idx" class="items-row">
            <a-input v-model:value="it.item_name" size="small" class="c-name" placeholder="如 收缩压" />
            <a-select v-model:value="it.item_category" size="small" class="c-cat" allow-clear placeholder="分类">
              <a-select-option v-for="c in itemCategories" :key="c" :value="c">{{ c }}</a-select-option>
            </a-select>
            <a-input-number v-model:value="it.value" size="small" class="c-val" placeholder="0" />
            <a-input v-model:value="it.unit" size="small" class="c-unit" placeholder="单位" />
            <a-input v-model:value="it.reference_range" size="small" class="c-ref" placeholder="参考" />
            <a-select v-model:value="it.abnormal_flag" size="small" class="c-flag">
              <a-select-option value="正常">正常</a-select-option>
              <a-select-option value="偏高">偏高</a-select-option>
              <a-select-option value="偏低">偏低</a-select-option>
              <a-select-option value="异常">异常</a-select-option>
            </a-select>
            <a-button size="small" type="text" danger class="c-op" @click="form.items.splice(idx, 1)">✕</a-button>
          </div>
        </div>
        <div v-else class="items-empty">暂无指标，点击「添加指标」录入；报告图片可在保存后于详情页上传</div>

        <div class="items-head" style="margin-top: 18px">
          <span class="items-title">体检报告</span>
          <a-upload :before-upload="pickReport" :show-upload-list="false" accept="image/*,.pdf" multiple>
            <a-button size="small" type="dashed">+ 选择文件</a-button>
          </a-upload>
        </div>
        <div v-if="pendingFiles.length" class="file-list">
          <div v-for="(f, i) in pendingFiles" :key="'p' + i" class="file-row">
            <span class="fr-name">{{ f.name }}</span>
            <span class="fr-size">{{ (f.size / 1024 / 1024).toFixed(2) }} MB</span>
            <a-tag color="blue" :bordered="false" style="margin: 0 6px">待上传</a-tag>
            <a-button size="small" type="text" danger @click="pendingFiles.splice(i, 1)">✕</a-button>
          </div>
        </div>
        <div v-if="form.id && existingAttachments.length" class="file-list">
          <div v-for="a in existingAttachments" :key="'e' + a.id" class="file-row">
            <span class="fr-name">📎 {{ a.file_name }}</span>
            <a-tag :bordered="false" style="margin: 0 6px">已上传</a-tag>
            <a-button size="small" type="text" danger @click="removeAttachmentInModal(a)">✕</a-button>
          </div>
        </div>
        <div v-if="!pendingFiles.length && !existingAttachments.length" class="items-empty">
          支持图片或 PDF，单文件 ≤ 20MB，保存时自动上传
        </div>
      </a-form>
    </a-modal>

    <!-- 详情抽屉 -->
    <a-drawer v-model:open="detailOpen" :width="640" :title="detail?.checkup_date + ' 体检详情'">
      <template v-if="detail">
        <a-descriptions :column="2" size="small" bordered>
          <a-descriptions-item label="机构">{{ detail.hospital || '-' }}</a-descriptions-item>
          <a-descriptions-item label="类型">{{ detail.checkup_type }}</a-descriptions-item>
          <a-descriptions-item label="花费">
            <span class="cost-value">{{ detail.cost ? '¥' + Number(detail.cost).toLocaleString('zh-CN', { minimumFractionDigits: 2 }) : '未记录' }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="报告份数">{{ detail.attachments?.length || 0 }} 份</a-descriptions-item>
          <a-descriptions-item label="总评" :span="2">{{ detail.summary || '-' }}</a-descriptions-item>
          <a-descriptions-item v-if="detail.notes" label="备注" :span="2">{{ detail.notes }}</a-descriptions-item>
        </a-descriptions>

        <div class="drawer-section">
          <div class="section-title">体检指标（{{ detail.items.length }}）</div>
          <a-table :data-source="detail.items" :columns="itemColumns" row-key="id" size="small" :pagination="false">
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'flag'">
                <a-tag :color="flagColor(record.abnormal_flag)" :bordered="false">{{ record.abnormal_flag }}</a-tag>
              </template>
            </template>
          </a-table>
        </div>

        <div class="drawer-section">
          <div class="section-title">
            检查报告（{{ detail.attachments?.length || 0 }}）
            <a-upload :before-upload="(f) => handleUpload('checkup', detail.id, f)" :show-upload-list="false" accept="image/*,.pdf" multiple>
              <a-button size="small" type="primary" ghost style="margin-left: 10px">+ 上传报告</a-button>
            </a-upload>
          </div>
          <div v-if="detail.attachments?.length" class="attach-grid">
            <div v-for="a in detail.attachments" :key="a.id" class="attach-item">
              <img v-if="a.file_type === 'image'" :src="'/' + a.file_path" @click="previewImage(a.file_path)" />
              <a v-else :href="'/' + a.file_path" target="_blank" class="pdf-box">📄<span>{{ a.file_name }}</span></a>
              <a-button size="small" type="text" danger class="attach-del" @click="removeAttachment(a)">✕</a-button>
            </div>
          </div>
          <div v-else class="attach-empty">暂无报告，支持图片或 PDF（单文件 ≤ 20MB）</div>
        </div>
      </template>
    </a-drawer>

    <a-image-preview-group>
      <a-image v-if="previewSrc" :src="previewSrc" style="display: none" :preview="{ visible: true, onVisibleChange: (v) => { if (!v) previewSrc = '' } }" />
    </a-image-preview-group>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { healthApi } from '@/api'

const loading = ref(false)
const list = ref([])
const members = ref([])
const filterMember = ref(undefined)
const filterYear = ref(undefined)
const keyword = ref('')
const years = (() => {
  const now = new Date().getFullYear()
  return Array.from({ length: 8 }, (_, i) => now - i)
})()
const checkupTypes = ['年度体检', '入职体检', '专项检查', '其他']
const itemCategories = ['一般检查', '血常规', '血脂', '肝功能', '肾功能', '血糖', '尿常规', '其他']

const columns = [
  { title: '体检日期', key: 'date', dataIndex: 'checkup_date', width: 120 },
  { title: '成员', dataIndex: 'member_name', width: 90 },
  { title: '类型', key: 'type', width: 110 },
  { title: '机构', dataIndex: 'hospital', ellipsis: true },
  { title: '花费', key: 'cost', width: 110 },
  { title: '指标', key: 'items', width: 150 },
  { title: '报告', key: 'attach', width: 80 },
  { title: '操作', key: 'action', width: 170 },
]
const itemColumns = [
  { title: '指标', dataIndex: 'item_name' },
  { title: '数值', dataIndex: 'value', width: 80, customRender: ({ record }) => record.value ?? record.text_value ?? '-' },
  { title: '单位', dataIndex: 'unit', width: 70 },
  { title: '参考范围', dataIndex: 'reference_range', width: 100 },
  { title: '标记', key: 'flag', width: 80 },
]

const modalOpen = ref(false)
const saving = ref(false)
const emptyForm = () => ({ id: null, member_id: undefined, checkup_date: today(), hospital: '', checkup_type: '年度体检', cost: null, summary: '', notes: '', items: [] })
const form = reactive(emptyForm())
const pendingFiles = ref([])
const existingAttachments = ref([])

const detailOpen = ref(false)
const detail = ref(null)
const previewSrc = ref('')

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function flagColor(f) {
  if (f === '偏高') return 'red'
  if (f === '偏低') return 'orange'
  if (f === '异常') return 'volcano'
  return 'green'
}

async function loadMembers() {
  try {
    const { data } = await healthApi.listMembers()
    members.value = data || []
    if (members.value.length && form.member_id === undefined) form.member_id = members.value[0].id
  } catch { /* ignore */ }
}

async function load() {
  loading.value = true
  try {
    const { data } = await healthApi.listCheckups({
      member_id: filterMember.value || undefined,
      year: filterYear.value || undefined,
      keyword: keyword.value || undefined,
    })
    list.value = data || []
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function addItem() {
  form.items.push({ item_name: '', item_category: '', value: null, text_value: '', unit: '', reference_range: '', abnormal_flag: '正常' })
}

async function openModal(record = null) {
  Object.assign(form, emptyForm())
  pendingFiles.value = []
  existingAttachments.value = []
  if (record) {
    form.id = record.id
    form.member_id = record.member_id
    form.checkup_date = record.checkup_date
    form.hospital = record.hospital
    form.checkup_type = record.checkup_type
    form.cost = record.cost || null
    form.summary = record.summary
    form.notes = record.notes
    const { data } = await healthApi.getCheckup(record.id)
    form.items = (data.items || []).map(i => ({
      item_name: i.item_name, item_category: i.item_category, value: i.value,
      text_value: i.text_value, unit: i.unit, reference_range: i.reference_range, abnormal_flag: i.abnormal_flag,
    }))
    existingAttachments.value = data.attachments || []
  }
  modalOpen.value = true
}

function pickReport(file) {
  if (file.size > 20 * 1024 * 1024) {
    message.warning(`${file.name} 超过 20MB`)
    return false
  }
  pendingFiles.value.push(file)
  return false
}

async function uploadPending(targetId) {
  const files = pendingFiles.value.slice()
  let ok = 0
  for (const f of files) {
    try {
      await healthApi.uploadAttachment('checkup', targetId, f)
      ok++
    } catch (e) {
      message.error(`${f.name} 上传失败：${e.response?.data?.detail || '未知错误'}`)
    }
  }
  pendingFiles.value = []
  return ok
}

async function removeAttachmentInModal(a) {
  try {
    await healthApi.deleteAttachment(a.id)
    existingAttachments.value = existingAttachments.value.filter(x => x.id !== a.id)
    message.success('已删除')
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function submit() {
  if (!form.member_id) return message.warning('请选择成员')
  if (!form.checkup_date) return message.warning('请填写体检日期')
  saving.value = true
  try {
    const payload = {
      member_id: form.member_id,
      checkup_date: form.checkup_date,
      hospital: form.hospital,
      checkup_type: form.checkup_type,
      cost: form.cost || 0,
      summary: form.summary,
      notes: form.notes,
      items: form.items.filter(i => i.item_name && i.item_name.trim()),
    }
    let targetId = form.id
    if (form.id) await healthApi.updateCheckup(form.id, payload)
    else {
      const { data } = await healthApi.createCheckup(payload)
      targetId = data.id
    }
    const uploaded = pendingFiles.value.length ? await uploadPending(targetId) : 0
    message.success(uploaded ? `保存成功，已上传 ${uploaded} 份报告` : '保存成功')
    modalOpen.value = false
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function remove(record) {
  healthApi.deleteCheckup(record.id).then(() => {
    message.success('已删除')
    load()
  }).catch(e => message.error(e.response?.data?.detail || '删除失败'))
}

async function openDetail(record) {
  try {
    const { data } = await healthApi.getCheckup(record.id)
    detail.value = data
    detailOpen.value = true
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  }
}

async function handleUpload(refType, refId, file) {
  try {
    await healthApi.uploadAttachment(refType, refId, file)
    message.success('报告已上传')
    const { data } = await healthApi.getCheckup(refId)
    detail.value = data
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '上传失败')
  }
  return false
}

async function removeAttachment(a) {
  try {
    await healthApi.deleteAttachment(a.id)
    message.success('已删除')
    const { data } = await healthApi.getCheckup(detail.value.id)
    detail.value = data
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

function previewImage(path) {
  previewSrc.value = '/' + path
}

onMounted(async () => {
  await loadMembers()
  load()
})
</script>

<style scoped>
.health-checkup { padding: 4px; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
.mono { font-family: var(--font-mono, monospace); }
.attach-icon { font-size: 15px; }
.items-head { display: flex; align-items: center; justify-content: space-between; margin: 8px 0 10px; }
.items-title { font-weight: 600; font-size: 14px; }
.items-table { border: 1px solid var(--border-color, #eee); border-radius: 8px; overflow: hidden; }
.items-row { display: flex; gap: 8px; padding: 8px 10px; border-bottom: 1px solid var(--border-color, #f0f0f0); align-items: center; }
.items-row:last-child { border-bottom: none; }
.items-row-head { background: var(--bg-secondary, #fafafa); font-size: 12px; color: var(--text-tertiary, #888); font-weight: 500; }
.c-name { flex: 2; }
.c-cat { flex: 1.4; }
.c-val { flex: 1; }
.c-unit { flex: 0.9; }
.c-ref { flex: 1.2; }
.c-flag { flex: 1; }
.c-op { flex: 0 0 28px; }
.items-empty { color: var(--text-tertiary, #999); font-size: 13px; padding: 16px; background: var(--bg-secondary, #fafafa); border-radius: 8px; text-align: center; }
.drawer-section { margin-top: 22px; }
.section-title { font-weight: 600; font-size: 14px; margin-bottom: 12px; display: flex; align-items: center; }
.attach-grid { display: flex; flex-wrap: wrap; gap: 12px; }
.attach-item { position: relative; width: 100px; height: 100px; border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color, #eee); }
.attach-item img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.pdf-box { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; font-size: 12px; color: #b91c1c; background: #fef2f2; text-decoration: none; padding: 6px; text-align: center; }
.attach-del { position: absolute; top: 2px; right: 2px; background: rgba(255, 255, 255, 0.85) !important; }
.attach-empty { color: var(--text-tertiary, #999); font-size: 13px; padding: 16px; background: var(--bg-secondary, #fafafa); border-radius: 8px; text-align: center; }
.file-list { border: 1px solid var(--border-color, #eee); border-radius: 8px; overflow: hidden; }
.file-row { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-bottom: 1px solid var(--border-color, #f0f0f0); font-size: 13px; }
.file-row:last-child { border-bottom: none; }
.fr-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary, #1e293b); }
.fr-size { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.cost-value { font-weight: 600; color: #b45309; font-family: var(--font-mono, monospace); }
</style>
