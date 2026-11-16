<template>
  <div class="health-disease">
    <div class="toolbar">
      <a-select v-model:value="filterMember" placeholder="全部成员" allow-clear style="width: 140px" @change="load">
        <a-select-option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</a-select-option>
      </a-select>
      <a-select v-model:value="filterStatus" placeholder="全部状态" allow-clear style="width: 130px" @change="load">
        <a-select-option v-for="s in statuses" :key="s" :value="s">{{ s }}</a-select-option>
      </a-select>
      <a-input-search v-model:value="keyword" placeholder="搜索疾病/医院…" style="width: 200px" allow-clear @search="load" />
      <div style="flex: 1"></div>
      <a-button type="primary" :disabled="!members.length" @click="openDiseaseModal()">+ 新增疾病</a-button>
    </div>

    <a-spin :spinning="loading">
      <div v-if="list.length" class="disease-list">
        <div v-for="d in list" :key="d.id" class="disease-card" :class="{ 'is-chronic': d.status === '慢性病' }">
          <div class="dc-main" style="cursor: pointer" @click="openDetail(d)">
            <div class="dc-title">
              <span class="dc-name">{{ d.disease_name }}</span>
              <a-tag :color="statusColor(d.status)" :bordered="false">{{ d.status }}</a-tag>
              <a-tag v-if="d.severity" :bordered="false" color="default">{{ d.severity }}</a-tag>
            </div>
            <div class="dc-meta">
              <span>{{ d.member_name }}</span>
              <span v-if="d.diagnosed_date"> · 确诊 {{ d.diagnosed_date }}</span>
              <span v-if="d.hospital"> · {{ d.hospital }}</span>
              <span v-if="d.doctor"> · {{ d.doctor }}</span>
            </div>
            <div v-if="d.notes" class="dc-notes">{{ d.notes }}</div>
          </div>
          <div class="dc-side">
            <div class="dc-visits">
              <div><span class="dc-visit-num">{{ d.visit_count }}</span><span class="dc-visit-label">次就诊</span></div>
              <div v-if="d.expense_total" class="dc-exp">花费 ¥{{ money(d.expense_total) }}</div>
              <div v-if="d.attachment_count" class="dc-exp">📎 {{ d.attachment_count }} 份资料</div>
            </div>
            <div class="dc-actions">
              <a-button size="small" type="primary" @click="openDetail(d)">查看详情</a-button>
              <a-button size="small" @click="openDiseaseModal(d)">编辑</a-button>
              <a-popconfirm title="删除疾病将同时删除其就诊记录及报告，确认？" @confirm="removeDisease(d)">
                <a-button size="small" danger>删除</a-button>
              </a-popconfirm>
            </div>
          </div>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="暂无疾病记录" style="margin-top: 60px" />
    </a-spin>

    <!-- 疾病弹窗 -->
    <a-modal v-model:open="modalOpen" :title="form.id ? '编辑疾病档案' : '新增疾病档案'" :width="560" @ok="submitDisease" :confirm-loading="saving">
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="成员" required>
              <a-select v-model:value="form.member_id" style="width: 100%">
                <a-select-option v-for="m in members" :key="m.id" :value="m.id">{{ m.name }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="16">
            <a-form-item label="疾病名称" required>
              <a-input v-model:value="form.disease_name" placeholder="如：高血压、2型糖尿病" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="确诊日期">
              <a-input v-model:value="form.diagnosed_date" placeholder="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="状态">
              <a-select v-model:value="form.status" style="width: 100%">
                <a-select-option v-for="s in statuses" :key="s" :value="s">{{ s }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="严重程度">
              <a-select v-model:value="form.severity" allow-clear style="width: 100%">
                <a-select-option value="轻微">轻微</a-select-option>
                <a-select-option value="中度">中度</a-select-option>
                <a-select-option value="严重">严重</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="确诊医院">
              <a-input v-model:value="form.hospital" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="主治医生">
              <a-input v-model:value="form.doctor" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注">
          <a-textarea v-model:value="form.notes" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 疾病详情抽屉 -->
    <a-drawer v-model:open="detailOpen" :width="720" :title="currentDisease?.disease_name">
      <template v-if="currentDisease">
        <a-descriptions :column="2" size="small" bordered>
          <a-descriptions-item label="成员">{{ currentDisease.member_name }}</a-descriptions-item>
          <a-descriptions-item label="状态">
            <a-tag :color="statusColor(currentDisease.status)" :bordered="false">{{ currentDisease.status }}</a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="确诊日期">{{ currentDisease.diagnosed_date || '-' }}</a-descriptions-item>
          <a-descriptions-item label="严重程度">{{ currentDisease.severity || '-' }}</a-descriptions-item>
          <a-descriptions-item label="医院">{{ currentDisease.hospital || '-' }}</a-descriptions-item>
          <a-descriptions-item label="主治医生">{{ currentDisease.doctor || '-' }}</a-descriptions-item>
          <a-descriptions-item label="累计花费">
            <span class="exp-amount">¥{{ money(expenseTotal) }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="资料附件">{{ diseaseAttachments.length }} 份</a-descriptions-item>
          <a-descriptions-item v-if="currentDisease.notes" label="备注" :span="2">{{ currentDisease.notes }}</a-descriptions-item>
        </a-descriptions>

        <a-tabs v-model:activeKey="detailTab" style="margin-top: 18px">
          <!-- 就诊记录 -->
          <a-tab-pane key="visits" :tab="`就诊记录 (${visits.length})`">
            <div class="visits-head">
              <span class="visits-sub">按就诊日期倒序</span>
              <a-button type="primary" size="small" @click="openVisitModal()">+ 添加就诊记录</a-button>
            </div>

            <a-timeline v-if="visits.length" style="margin-top: 18px">
              <a-timeline-item v-for="v in visits" :key="v.id" :color="v.attachments?.length ? 'blue' : 'gray'">
                <div class="visit-card">
                  <div class="vc-head">
                    <span class="vc-date">{{ v.visit_date }}</span>
                    <span v-if="v.hospital" class="vc-hospital">{{ v.hospital }}<span v-if="v.department"> · {{ v.department }}</span></span>
                    <div style="flex: 1"></div>
                    <a-button type="text" size="small" @click="openVisitModal(v)">编辑</a-button>
                    <a-popconfirm title="删除该就诊记录及报告？" @confirm="removeVisit(v)">
                      <a-button type="text" size="small" danger>删除</a-button>
                    </a-popconfirm>
                  </div>
                  <div v-if="v.doctor" class="vc-line"><b>医生：</b>{{ v.doctor }}</div>
                  <div v-if="v.diagnosis" class="vc-line"><b>诊断：</b>{{ v.diagnosis }}</div>
                  <div v-if="v.treatment" class="vc-line"><b>处理：</b>{{ v.treatment }}</div>
                  <div v-if="v.notes" class="vc-line"><b>医嘱：</b>{{ v.notes }}</div>

                  <div class="vc-attach">
                    <a-upload :before-upload="(f) => handleUpload('visit', v.id, f)" :show-upload-list="false" accept="image/*,.pdf" multiple>
                      <a-button size="small" type="dashed">📎 上传检查报告</a-button>
                    </a-upload>
                    <div v-if="v.attachments?.length" class="attach-grid">
                      <div v-for="a in v.attachments" :key="a.id" class="attach-item">
                        <img v-if="a.file_type === 'image'" :src="'/' + a.file_path" @click="previewSrc = '/' + a.file_path" />
                        <a v-else :href="'/' + a.file_path" target="_blank" class="pdf-box">📄<span>{{ a.file_name }}</span></a>
                        <a-button size="small" type="text" danger class="attach-del" @click="removeAttachment(a)">✕</a-button>
                      </div>
                    </div>
                  </div>
                </div>
              </a-timeline-item>
            </a-timeline>
            <a-empty v-else description="暂无就诊记录，点击右上角添加" style="margin-top: 30px" />
          </a-tab-pane>

          <!-- 费用 -->
          <a-tab-pane key="expenses" :tab="`费用 (${expenses.length})`">
            <div class="exp-head">
              <div>
                <span class="exp-label">累计花费</span>
                <span class="exp-amount big">¥{{ money(expenseTotal) }}</span>
              </div>
              <a-button type="primary" size="small" @click="openExpenseModal()">+ 添加费用</a-button>
            </div>
            <a-table
              v-if="expenses.length" :data-source="expenses" :columns="expenseColumns"
              row-key="id" size="small" :pagination="false" style="margin-top: 14px"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'amount'">
                  <span class="exp-amount">¥{{ money(record.amount) }}</span>
                </template>
                <template v-else-if="column.key === 'action'">
                  <a-button type="link" size="small" @click="openExpenseModal(record)">编辑</a-button>
                  <a-popconfirm title="删除该费用记录？" @confirm="removeExpense(record)">
                    <a-button type="link" size="small" danger>删除</a-button>
                  </a-popconfirm>
                </template>
              </template>
            </a-table>
            <a-empty v-else description="暂无费用记录" style="margin-top: 30px" />
          </a-tab-pane>

          <!-- 附件 -->
          <a-tab-pane key="attachments" :tab="`附件 (${diseaseAttachments.length})`">
            <div class="visits-head">
              <span class="visits-sub">病历、检查单、出院小结等（图片 / PDF）</span>
              <a-upload :before-upload="(f) => handleUpload('disease', currentDisease.id, f)" :show-upload-list="false" accept="image/*,.pdf" multiple>
                <a-button type="primary" size="small">+ 上传附件</a-button>
              </a-upload>
            </div>
            <div v-if="diseaseAttachments.length" class="attach-grid" style="margin-top: 16px">
              <div v-for="a in diseaseAttachments" :key="a.id" class="attach-item big">
                <img v-if="a.file_type === 'image'" :src="'/' + a.file_path" @click="previewSrc = '/' + a.file_path" />
                <a v-else :href="'/' + a.file_path" target="_blank" class="pdf-box">📄<span>{{ a.file_name }}</span></a>
                <a-button size="small" type="text" danger class="attach-del" @click="removeAttachment(a)">✕</a-button>
              </div>
            </div>
            <a-empty v-else description="暂无附件，支持图片或 PDF（单文件 ≤ 20MB）" style="margin-top: 30px" />
          </a-tab-pane>
        </a-tabs>
      </template>
    </a-drawer>

    <!-- 费用弹窗 -->
    <a-modal
      v-model:open="expenseModalOpen" :title="expenseForm.id ? '编辑费用' : '添加费用'"
      :width="520" @ok="submitExpense" :confirm-loading="expenseSaving"
    >
      <a-form :model="expenseForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="费用日期">
              <a-input v-model:value="expenseForm.expense_date" placeholder="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="类别">
              <a-select v-model:value="expenseForm.category" style="width: 100%">
                <a-select-option v-for="c in expenseCategories" :key="c" :value="c">{{ c }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="金额" required>
          <a-input-number
            v-model:value="expenseForm.amount" :min="0" :precision="2" style="width: 100%"
            :formatter="(v) => v ? `¥ ${v}` : ''" :parser="(v) => v.replace(/[^\d.]/g, '')"
          />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="expenseForm.note" :rows="2" placeholder="如：血常规+肝功能套餐，医保报销后自付" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 就诊记录弹窗 -->
    <a-modal v-model:open="visitModalOpen" :title="visitForm.id ? '编辑就诊记录' : '添加就诊记录'" :width="560" @ok="submitVisit" :confirm-loading="visitSaving">
      <a-form :model="visitForm" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="就诊日期" required>
              <a-input v-model:value="visitForm.visit_date" placeholder="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="医院">
              <a-input v-model:value="visitForm.hospital" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="科室">
              <a-input v-model:value="visitForm.department" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="医生">
          <a-input v-model:value="visitForm.doctor" />
        </a-form-item>
        <a-form-item label="诊断结论">
          <a-textarea v-model:value="visitForm.diagnosis" :rows="2" />
        </a-form-item>
        <a-form-item label="处理方案 / 用药">
          <a-textarea v-model:value="visitForm.treatment" :rows="2" placeholder="如：口服××药，每日1次；3个月后复查" />
        </a-form-item>
        <a-form-item label="医嘱 / 备注">
          <a-textarea v-model:value="visitForm.notes" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-image-preview-group>
      <a-image v-if="previewSrc" :src="previewSrc" style="display: none" :preview="{ visible: true, onVisibleChange: (v) => { if (!v) previewSrc = '' } }" />
    </a-image-preview-group>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { healthApi } from '@/api'

const loading = ref(false)
const list = ref([])
const members = ref([])
const statuses = ref(['治疗中', '慢性病', '已治愈', '已停访'])
const expenseCategories = ref(['挂号', '检查', '药品', '治疗', '住院', '其他'])
const filterMember = ref(undefined)
const filterStatus = ref(undefined)
const keyword = ref('')

const modalOpen = ref(false)
const saving = ref(false)
const emptyForm = () => ({ id: null, member_id: undefined, disease_name: '', diagnosed_date: '', status: '治疗中', severity: '', hospital: '', doctor: '', notes: '' })
const form = reactive(emptyForm())

const detailOpen = ref(false)
const detailTab = ref('visits')
const currentDisease = ref(null)
const visits = ref([])
const diseaseAttachments = ref([])
const expenses = ref([])
const expenseModalOpen = ref(false)
const expenseSaving = ref(false)
const emptyExpense = () => ({ id: null, expense_date: today(), category: '挂号', amount: null, note: '' })
const expenseForm = reactive(emptyExpense())
const visitModalOpen = ref(false)
const visitSaving = ref(false)
const emptyVisit = () => ({ id: null, visit_date: today(), hospital: '', department: '', doctor: '', diagnosis: '', treatment: '', notes: '' })
const visitForm = reactive(emptyVisit())
const previewSrc = ref('')

const expenseTotal = computed(() =>
  expenses.value.reduce((sum, e) => sum + (Number(e.amount) || 0), 0)
)
const expenseColumns = [
  { title: '日期', dataIndex: 'expense_date', width: 110 },
  { title: '类别', dataIndex: 'category', width: 90 },
  { title: '金额', key: 'amount', width: 110 },
  { title: '备注', dataIndex: 'note', ellipsis: true },
  { title: '操作', key: 'action', width: 110 },
]

function money(v) {
  return Number(v || 0).toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}
function statusColor(s) {
  if (s === '慢性病') return 'orange'
  if (s === '治疗中') return 'red'
  if (s === '已治愈') return 'green'
  return 'default'
}

async function loadConfig() {
  try {
    const { data } = await healthApi.getConfig()
    if (data?.disease_statuses?.length) statuses.value = data.disease_statuses
    if (data?.expense_categories?.length) expenseCategories.value = data.expense_categories
  } catch { /* ignore */ }
}
async function loadMembers() {
  try {
    const { data } = await healthApi.listMembers()
    members.value = data || []
  } catch { /* ignore */ }
}
async function load() {
  loading.value = true
  try {
    const { data } = await healthApi.listDiseases({
      member_id: filterMember.value || undefined,
      status: filterStatus.value || undefined,
      keyword: keyword.value || undefined,
    })
    list.value = data || []
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openDiseaseModal(d = null) {
  Object.assign(form, emptyForm())
  if (!d && members.value.length) form.member_id = members.value[0].id
  if (d) Object.assign(form, d)
  modalOpen.value = true
}
async function submitDisease() {
  if (!form.member_id) return message.warning('请选择成员')
  if (!form.disease_name.trim()) return message.warning('请填写疾病名称')
  saving.value = true
  try {
    const payload = { ...form }
    delete payload.id
    delete payload.visit_count
    delete payload.member_name
    if (form.id) await healthApi.updateDisease(form.id, payload)
    else await healthApi.createDisease(payload)
    message.success('保存成功')
    modalOpen.value = false
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}
function removeDisease(d) {
  healthApi.deleteDisease(d.id).then(() => {
    message.success('已删除')
    load()
  }).catch(e => message.error(e.response?.data?.detail || '删除失败'))
}

async function openDetail(d) {
  currentDisease.value = d
  detailTab.value = 'visits'
  detailOpen.value = true
  await Promise.all([loadVisits(), loadExpenses(), loadDiseaseAttachments()])
}
async function loadVisits() {
  if (!currentDisease.value) return
  try {
    const { data } = await healthApi.listVisits(currentDisease.value.id)
    visits.value = data || []
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  }
}
async function loadExpenses() {
  if (!currentDisease.value) return
  try {
    const { data } = await healthApi.listExpenses('disease', currentDisease.value.id)
    expenses.value = data?.items || []
  } catch (e) {
    message.error(e.response?.data?.detail || '加载费用失败')
  }
}
async function loadDiseaseAttachments() {
  if (!currentDisease.value) return
  try {
    const { data } = await healthApi.listAttachments('disease', currentDisease.value.id)
    diseaseAttachments.value = data || []
  } catch (e) {
    message.error(e.response?.data?.detail || '加载附件失败')
  }
}

// ─── 费用 ───
function openExpenseModal(e = null) {
  Object.assign(expenseForm, emptyExpense())
  if (e) Object.assign(expenseForm, { id: e.id, expense_date: e.expense_date, category: e.category, amount: e.amount, note: e.note })
  expenseModalOpen.value = true
}
async function submitExpense() {
  if (!expenseForm.amount || expenseForm.amount <= 0) return message.warning('请填写金额')
  expenseSaving.value = true
  try {
    const payload = {
      expense_date: expenseForm.expense_date,
      category: expenseForm.category,
      amount: expenseForm.amount,
      note: expenseForm.note,
    }
    if (expenseForm.id) await healthApi.updateExpense(expenseForm.id, payload)
    else await healthApi.createExpense({
      ref_type: 'disease',
      ref_id: currentDisease.value.id,
      member_id: currentDisease.value.member_id,
      ...payload,
    })
    message.success('保存成功')
    expenseModalOpen.value = false
    await loadExpenses()
    if (currentDisease.value) currentDisease.value.expense_total = expenseTotal.value
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    expenseSaving.value = false
  }
}
async function removeExpense(e) {
  try {
    await healthApi.deleteExpense(e.id)
    message.success('已删除')
    await loadExpenses()
    if (currentDisease.value) currentDisease.value.expense_total = expenseTotal.value
    load()
  } catch (err) {
    message.error(err.response?.data?.detail || '删除失败')
  }
}

function openVisitModal(v = null) {
  Object.assign(visitForm, emptyVisit())
  if (v) {
    Object.assign(visitForm, {
      id: v.id, visit_date: v.visit_date, hospital: v.hospital, department: v.department,
      doctor: v.doctor, diagnosis: v.diagnosis, treatment: v.treatment, notes: v.notes,
    })
  }
  visitModalOpen.value = true
}
async function submitVisit() {
  if (!visitForm.visit_date) return message.warning('请填写就诊日期')
  visitSaving.value = true
  try {
    const payload = {
      disease_id: currentDisease.value.id,
      member_id: currentDisease.value.member_id,
      visit_date: visitForm.visit_date,
      hospital: visitForm.hospital,
      department: visitForm.department,
      doctor: visitForm.doctor,
      diagnosis: visitForm.diagnosis,
      treatment: visitForm.treatment,
      notes: visitForm.notes,
    }
    if (visitForm.id) await healthApi.updateVisit(visitForm.id, payload)
    else await healthApi.createVisit(payload)
    message.success('保存成功')
    visitModalOpen.value = false
    await loadVisits()
    load() // 刷新就诊次数
  } catch (e) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    visitSaving.value = false
  }
}
async function removeVisit(v) {
  try {
    await healthApi.deleteVisit(v.id)
    message.success('已删除')
    await loadVisits()
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

async function handleUpload(refType, refId, file) {
  try {
    await healthApi.uploadAttachment(refType, refId, file)
    message.success('附件已上传')
    if (refType === 'disease') {
      await loadDiseaseAttachments()
      load()
    } else {
      await loadVisits()
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '上传失败')
  }
  return false
}
async function removeAttachment(a) {
  try {
    await healthApi.deleteAttachment(a.id)
    message.success('已删除')
    if (a.ref_type === 'disease') {
      await loadDiseaseAttachments()
      load()
    } else {
      await loadVisits()
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(async () => {
  loadConfig()
  await loadMembers()
  load()
})
</script>

<style scoped>
.health-disease { padding: 4px; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
.disease-list { display: flex; flex-direction: column; gap: 12px; }
.disease-card {
  display: flex; gap: 16px; background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #eee); border-left: 4px solid #f87171;
  border-radius: 12px; padding: 16px 18px; transition: box-shadow 0.2s;
}
.disease-card.is-chronic { border-left-color: #fb923c; }
.disease-card:hover { box-shadow: 0 4px 16px rgba(0, 0, 0, 0.07); }
.dc-main { flex: 1; min-width: 0; }
.dc-title { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.dc-name { font-size: 16px; font-weight: 600; color: var(--text-primary, #1e293b); }
.dc-meta { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.dc-notes { font-size: 12px; color: var(--text-secondary, #64748b); margin-top: 8px; background: var(--bg-secondary, #f8fafc); border-radius: 8px; padding: 6px 10px; }
.dc-side { display: flex; flex-direction: column; align-items: flex-end; justify-content: space-between; gap: 10px; }
.dc-visits { text-align: right; }
.dc-visit-num { font-size: 22px; font-weight: 700; color: #3b82f6; }
.dc-visit-label { font-size: 12px; color: var(--text-tertiary, #94a3b8); margin-left: 4px; }
.dc-actions { display: flex; gap: 6px; }
.visits-head { display: flex; align-items: center; justify-content: space-between; }
.visits-sub { font-size: 13px; color: var(--text-tertiary, #94a3b8); }
.visit-card { background: var(--bg-card, #fff); border: 1px solid var(--border-color, #eee); border-radius: 10px; padding: 12px 14px; }
.vc-head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.vc-date { font-weight: 600; font-size: 14px; color: var(--text-primary, #1e293b); }
.vc-hospital { font-size: 12px; color: var(--text-tertiary, #94a3b8); }
.vc-line { font-size: 13px; color: var(--text-secondary, #475569); line-height: 1.7; }
.vc-line b { color: var(--text-primary, #334155); }
.vc-attach { margin-top: 10px; }
.attach-grid { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 10px; }
.attach-item { position: relative; width: 84px; height: 84px; border-radius: 8px; overflow: hidden; border: 1px solid var(--border-color, #eee); }
.attach-item img { width: 100%; height: 100%; object-fit: cover; cursor: zoom-in; }
.pdf-box { display: flex; flex-direction: column; align-items: center; justify-content: center; width: 100%; height: 100%; font-size: 11px; color: #b91c1c; background: #fef2f2; text-decoration: none; padding: 4px; text-align: center; }
.attach-del { position: absolute; top: 2px; right: 2px; background: rgba(255, 255, 255, 0.85) !important; }
.attach-item.big { width: 104px; height: 104px; }
.dc-exp { font-size: 12px; color: var(--text-tertiary, #94a3b8); margin-top: 2px; }
.exp-head { display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: var(--bg-secondary, #f8fafc); border-radius: 10px; }
.exp-label { font-size: 13px; color: var(--text-secondary, #64748b); margin-right: 8px; }
.exp-amount { font-family: var(--font-mono, monospace); font-weight: 600; color: #b45309; }
.exp-amount.big { font-size: 20px; }
</style>
