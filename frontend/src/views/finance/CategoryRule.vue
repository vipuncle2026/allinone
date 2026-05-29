<template>
  <div class="category-rules">
    <!-- 操作栏 -->
    <a-card :bordered="false" size="small" class="section-card">
      <div style="display: flex; justify-content: space-between; align-items: center">
        <div class="section-title" style="margin-bottom: 0">
          <span class="section-title-icon">🏷️</span>
          <span>分类规则</span>
          <span class="table-count">{{ rules.length }} 条</span>
        </div>
        <a-space>
          <a-popconfirm title="重新应用所有规则到已导入的记录？" @confirm="handleReapply" :disabled="!rules.length">
            <a-button size="small" :disabled="!rules.length">
              🔄 重新应用规则
            </a-button>
          </a-popconfirm>
          <a-button type="primary" size="small" @click="showModal()" style="background: #6366f1; border-color: #6366f1">
            ➕ 新增规则
          </a-button>
        </a-space>
      </div>
    </a-card>

    <!-- 规则列表 -->
    <a-card :bordered="false" size="small" class="section-card" style="margin-top: 12px">
      <a-table
        :dataSource="rules"
        :columns="ruleColumns"
        size="small"
        row-key="id"
        :pagination="false"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'match'">
            <div class="match-cell">
              <a-tag size="small" color="blue">{{ matchFieldLabel[record.match_field] }}</a-tag>
              <a-tag size="small">{{ matchTypeLabel[record.match_type] }}</a-tag>
              <code class="match-value">"{{ record.match_value }}"</code>
            </div>
          </template>
          <template v-if="column.key === 'scope'">
            <a-space size="4">
              <a-tag v-if="record.txn_type !== 'all'" :color="record.txn_type === 'income' ? 'red' : 'green'" size="small">
                {{ record.txn_type === 'income' ? '收入' : '支出' }}
              </a-tag>
              <a-tag v-if="record.platform !== 'all'" size="small" color="default">
                {{ record.platform === 'alipay' ? '支付宝' : '微信' }}
              </a-tag>
              <span v-if="record.txn_type === 'all' && record.platform === 'all'" style="color: #94a3b8; font-size: 12px">全部</span>
            </a-space>
          </template>
          <template v-if="column.key === 'category'">
            <a-tag color="orange">{{ record.category }}</a-tag>
          </template>
          <template v-if="column.key === 'enabled'">
            <a-switch
              :checked="record.is_enabled === 1"
              size="small"
              @change="(val) => toggleEnabled(record, val)"
            />
          </template>
          <template v-if="column.key === 'actions'">
            <a-space>
              <a-button type="link" size="small" @click="showModal(record)">编辑</a-button>
              <a-popconfirm title="确定删除此规则？" @confirm="deleteRule(record.id)">
                <a-button type="link" size="small" danger>删除</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
      <a-empty v-if="!rules.length" description="暂无分类规则" style="padding: 40px 0" />
    </a-card>

    <!-- 新增/编辑弹窗 -->
    <a-modal
      v-model:open="modalVisible"
      :title="editingRule ? '编辑规则' : '新增规则'"
      @ok="saveRule"
      :confirmLoading="saving"
      width="540px"
    >
      <a-form :label-col="{ span: 5 }" :wrapper-col="{ span: 18 }" style="margin-top: 16px">
        <a-form-item label="规则名称" required>
          <a-input v-model:value="form.name" placeholder="如：美团→餐饮" :maxlength="50" />
        </a-form-item>
        <a-form-item label="匹配字段" required>
          <a-select v-model:value="form.match_field">
            <a-select-option value="description">交易描述</a-select-option>
            <a-select-option value="counterparty">交易对方</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="匹配方式" required>
          <a-select v-model:value="form.match_type">
            <a-select-option value="contains">包含关键词</a-select-option>
            <a-select-option value="equals">完全匹配</a-select-option>
            <a-select-option value="regex">正则表达式</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="匹配值" required>
          <a-input v-if="form.match_type === 'regex'" v-model:value="form.match_value" placeholder="如：美团|饿了么|瑞幸" />
          <a-textarea v-else v-model:value="form.match_value" :rows="3" :placeholder="form.match_type === 'equals' ? '如：\n二维码支付\n充值' : '如：\n美团\n饿了么\n瑞幸'" />
        </a-form-item>
        <a-form-item label="目标分类" required>
          <a-select v-model:value="form.category" show-search :filter-option="filterOption" placeholder="选择分类">
            <a-select-option v-for="c in allCategories" :key="c" :value="c">{{ c }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="适用类型">
          <a-select v-model:value="form.txn_type">
            <a-select-option value="all">全部</a-select-option>
            <a-select-option value="income">仅收入</a-select-option>
            <a-select-option value="expense">仅支出</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="适用平台">
          <a-select v-model:value="form.platform">
            <a-select-option value="all">全部</a-select-option>
            <a-select-option value="alipay">仅支付宝</a-select-option>
            <a-select-option value="wechat">仅微信</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="优先级">
          <a-input-number v-model:value="form.priority" :min="1" :max="999" style="width: 100%" />
          <div style="color: #94a3b8; font-size: 12px; margin-top: 4px">数字越小越优先，默认 100</div>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { financeApi } from '@/api'

const rules = ref([])
const allCategories = ref([])
const saving = ref(false)
const modalVisible = ref(false)
const editingRule = ref(null)

const form = ref({
  name: '',
  match_field: 'description',
  match_type: 'contains',
  match_value: '',
  category: '',
  txn_type: 'all',
  platform: 'all',
  priority: 100,
})

const matchFieldLabel = { description: '描述', counterparty: '对方' }
const matchTypeLabel = { contains: '包含', equals: '等于', regex: '正则' }

const ruleColumns = [
  { title: '优先级', dataIndex: 'priority', width: 70, align: 'center', sorter: (a, b) => a.priority - b.priority },
  { title: '规则名称', dataIndex: 'name', width: 150 },
  { title: '匹配条件', key: 'match' },
  { title: '目标分类', key: 'category', width: 110 },
  { title: '适用范围', key: 'scope', width: 130 },
  { title: '启用', key: 'enabled', width: 60, align: 'center' },
  { title: '操作', key: 'actions', width: 120, align: 'center' },
]

function filterOption(input, option) {
  return option.value.toLowerCase().includes(input.toLowerCase())
}

function showModal(rule = null) {
  editingRule.value = rule
  if (rule) {
    form.value = { ...rule }
  } else {
    form.value = {
      name: '', match_field: 'description', match_type: 'contains',
      match_value: '', category: '', txn_type: 'all', platform: 'all', priority: 100,
    }
  }
  modalVisible.value = true
}

async function saveRule() {
  if (!form.value.name || !form.value.match_value || !form.value.category) {
    return message.warning('请填写必要字段')
  }
  saving.value = true
  try {
    if (editingRule.value) {
      await financeApi.updateCategoryRule(editingRule.value.id, form.value)
      message.success('规则已更新')
    } else {
      await financeApi.createCategoryRule(form.value)
      message.success('规则已创建')
    }
    modalVisible.value = false
    loadRules()
  } catch (e) {
    message.error(e.response?.data?.detail || '操作失败')
  } finally {
    saving.value = false
  }
}

async function deleteRule(id) {
  try {
    await financeApi.deleteCategoryRule(id)
    message.success('规则已删除')
    loadRules()
  } catch (e) {
    message.error('删除失败')
  }
}

async function toggleEnabled(rule, val) {
  try {
    await financeApi.updateCategoryRule(rule.id, { is_enabled: val ? 1 : 0 })
    rule.is_enabled = val ? 1 : 0
    message.success(val ? '规则已启用' : '规则已禁用')
  } catch (e) {
    message.error('操作失败')
  }
}

async function handleReapply() {
  try {
    const { data } = await financeApi.reapplyCategoryRules()
    message.success(data.message)
  } catch (e) {
    message.error(e.response?.data?.detail || '操作失败')
  }
}

async function loadRules() {
  try {
    const { data } = await financeApi.listCategoryRules()
    rules.value = data
  } catch { /* ignore */ }
}

async function loadCategories() {
  try {
    const { data } = await financeApi.getConfig()
    allCategories.value = [...data.income_categories, ...data.expense_categories]
  } catch { /* ignore */ }
}

onMounted(() => {
  loadCategories()
  loadRules()
})
</script>

<style scoped>
.category-rules {
  max-width: 1400px;
  display: flex;
  flex-direction: column;
  gap: 0;
}
.section-card {
  border-radius: 14px;
  border: 1px solid #f1f5f9;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.section-title {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  display: flex;
  align-items: center;
  gap: 8px;
}
.section-title-icon { font-size: 16px; }
.table-count {
  font-size: 12px;
  color: #94a3b8;
  background: #f8fafc;
  padding: 2px 10px;
  border-radius: 10px;
}
.match-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;
}
.match-value {
  background: #f1f5f9;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
  color: #334155;
}
:deep(.ant-table-thead > tr > th) {
  background: linear-gradient(135deg, #f8fafc, #f1f5f9) !important;
  color: #475569;
  font-weight: 600;
}
</style>
