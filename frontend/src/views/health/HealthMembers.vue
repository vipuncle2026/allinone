<template>
  <div class="health-members">
    <div class="toolbar">
      <a-input-search
        v-model:value="keyword"
        placeholder="搜索成员姓名…"
        style="width: 220px"
        allow-clear
        @search="load"
      />
      <div style="flex: 1"></div>
      <a-button type="primary" @click="openModal()">+ 添加成员</a-button>
    </div>

    <a-spin :spinning="loading">
      <div v-if="members.length" class="member-grid">
        <div v-for="m in members" :key="m.id" class="member-card">
          <div class="member-avatar">
            <img v-if="m.photo_path" :src="'/' + m.photo_path" :alt="m.name" />
            <span v-else class="avatar-fallback">{{ m.name?.slice(0, 1) }}</span>
          </div>
          <div class="member-head">
            <div class="member-name">
              {{ m.name }}
              <a-tag size="small" :bordered="false" color="blue" style="margin-left: 6px">{{ m.relationship }}</a-tag>
            </div>
            <div class="member-basic">
              <span v-if="m.gender">{{ m.gender }}</span>
              <span v-if="m.birthday"> · {{ ageOf(m.birthday) }} 岁</span>
              <span v-if="m.blood_type"> · {{ m.blood_type }} 型</span>
            </div>
          </div>
          <div class="member-stats">
            <div class="ms-item"><span class="ms-num">{{ m.checkup_count }}</span><span class="ms-label">体检</span></div>
            <div class="ms-item"><span class="ms-num">{{ m.disease_count }}</span><span class="ms-label">疾病</span></div>
            <div class="ms-item"><span class="ms-num">{{ m.height || '-' }}</span><span class="ms-label">身高cm</span></div>
            <div class="ms-item"><span class="ms-num">{{ m.weight || '-' }}</span><span class="ms-label">体重kg</span></div>
          </div>
          <div v-if="m.allergy_history" class="member-allergy">
            <span class="allergy-tag">过敏史</span> {{ m.allergy_history }}
          </div>
          <div class="member-actions">
            <a-button size="small" @click="openModal(m)">编辑</a-button>
            <a-popconfirm title="删除成员将同时删除其体检、疾病、就诊记录及报告，确认？" ok-text="删除" cancel-text="取消" @confirm="remove(m)">
              <a-button size="small" danger>删除</a-button>
            </a-popconfirm>
          </div>
        </div>
      </div>
      <a-empty v-else-if="!loading" description="还没有成员，点击右上角添加" style="margin-top: 60px" />
    </a-spin>

    <a-modal v-model:open="modalOpen" :title="form.id ? '编辑成员' : '添加成员'" :width="560" @ok="submit" :confirm-loading="saving">
      <a-form :model="form" layout="vertical">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="姓名" required>
              <a-input v-model:value="form.name" placeholder="姓名" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="与本人关系">
              <a-select v-model:value="form.relationship" style="width: 100%">
                <a-select-option v-for="r in relationships" :key="r" :value="r">{{ r }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="8">
            <a-form-item label="性别">
              <a-select v-model:value="form.gender" allow-clear style="width: 100%">
                <a-select-option value="男">男</a-select-option>
                <a-select-option value="女">女</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="出生日期">
              <a-input v-model:value="form.birthday" placeholder="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="血型">
              <a-select v-model:value="form.blood_type" allow-clear style="width: 100%">
                <a-select-option v-for="b in ['A', 'B', 'AB', 'O']" :key="b" :value="b">{{ b }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="身高 (cm)">
              <a-input-number v-model:value="form.height" :min="0" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="体重 (kg)">
              <a-input-number v-model:value="form.weight" :min="0" :step="0.1" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="过敏史">
          <a-textarea v-model:value="form.allergy_history" :rows="2" placeholder="如：青霉素过敏、花粉过敏等" />
        </a-form-item>
        <a-form-item label="既往病史">
          <a-textarea v-model:value="form.medical_history" :rows="2" placeholder="如：高血压、糖尿病等" />
        </a-form-item>
        <a-form-item label="备注">
          <a-textarea v-model:value="form.notes" :rows="2" />
        </a-form-item>
        <a-form-item label="头像">
          <a-upload :before-upload="handlePhoto" :show-upload-list="false" accept="image/*">
            <a-button>上传头像</a-button>
          </a-upload>
          <img v-if="form.photo_path" :src="'/' + form.photo_path" class="photo-preview" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { healthApi } from '@/api'

const loading = ref(false)
const members = ref([])
const keyword = ref('')
const relationships = ref(['本人', '配偶', '父亲', '母亲', '儿子', '女儿', '其他'])

const modalOpen = ref(false)
const saving = ref(false)
const emptyForm = () => ({
  id: null, name: '', relationship: '本人', gender: '', birthday: '', blood_type: '',
  height: 0, weight: 0, photo_path: '', allergy_history: '', medical_history: '', notes: '',
})
const form = reactive(emptyForm())

function ageOf(birthday) {
  if (!birthday) return '-'
  const b = new Date(birthday)
  if (isNaN(b.getTime())) return '-'
  const now = new Date()
  let age = now.getFullYear() - b.getFullYear()
  const m = now.getMonth() - b.getMonth()
  if (m < 0 || (m === 0 && now.getDate() < b.getDate())) age--
  return age
}

async function load() {
  loading.value = true
  try {
    const { data } = await healthApi.listMembers({ keyword: keyword.value || undefined })
    members.value = data || []
  } catch (e) {
    message.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function loadConfig() {
  try {
    const { data } = await healthApi.getConfig()
    if (data?.relationships?.length) relationships.value = data.relationships
  } catch { /* ignore */ }
}

function openModal(m = null) {
  Object.assign(form, emptyForm())
  if (m) Object.assign(form, m)
  modalOpen.value = true
}

async function submit() {
  if (!form.name.trim()) return message.warning('请输入姓名')
  saving.value = true
  try {
    const payload = { ...form }
    delete payload.id
    delete payload.checkup_count
    delete payload.disease_count
    if (form.id) {
      await healthApi.updateMember(form.id, payload)
    } else {
      await healthApi.createMember(payload)
    }
    message.success('保存成功')
    modalOpen.value = false
    load()
  } catch (e) {
    message.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function remove(m) {
  healthApi.deleteMember(m.id).then(() => {
    message.success('已删除')
    load()
  }).catch(e => message.error(e.response?.data?.detail || '删除失败'))
}

async function handlePhoto(file) {
  try {
    const { data } = await healthApi.uploadMemberPhoto(file)
    form.photo_path = data.path
    message.success('头像已上传')
  } catch (e) {
    message.error(e.response?.data?.detail || '上传失败')
  }
  return false
}

onMounted(() => {
  loadConfig()
  load()
})
</script>

<style scoped>
.health-members { padding: 4px; }
.toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 18px; }
.member-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px; }
.member-card {
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-color, #e8e8e8);
  border-radius: 14px;
  padding: 18px;
  transition: box-shadow 0.2s, transform 0.2s;
}
.member-card:hover { box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08); transform: translateY(-2px); }
.member-avatar {
  width: 56px; height: 56px; border-radius: 50%; overflow: hidden;
  background: linear-gradient(135deg, #60a5fa, #3b82f6);
  display: flex; align-items: center; justify-content: center; margin-bottom: 12px;
}
.member-avatar img { width: 100%; height: 100%; object-fit: cover; }
.avatar-fallback { color: #fff; font-size: 22px; font-weight: 600; }
.member-head { margin-bottom: 14px; }
.member-name { font-size: 16px; font-weight: 600; color: var(--text-primary, #1e293b); }
.member-basic { font-size: 12px; color: var(--text-tertiary, #94a3b8); margin-top: 4px; }
.member-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 12px; }
.ms-item { text-align: center; background: var(--bg-secondary, #f8fafc); border-radius: 8px; padding: 8px 4px; }
.ms-num { display: block; font-size: 16px; font-weight: 600; color: #3b82f6; }
.ms-label { font-size: 11px; color: var(--text-tertiary, #94a3b8); }
.member-allergy {
  font-size: 12px; color: #b45309; background: #fef3c7; border-radius: 8px;
  padding: 6px 10px; margin-bottom: 12px; line-height: 1.5;
}
.allergy-tag { font-weight: 600; margin-right: 4px; }
.member-actions { display: flex; gap: 8px; justify-content: flex-end; }
.photo-preview { width: 60px; height: 60px; object-fit: cover; border-radius: 8px; margin-left: 12px; vertical-align: middle; }
</style>
