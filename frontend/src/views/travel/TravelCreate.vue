<template>
  <div class="travel-create">
    <a-page-header title="新建旅行" sub-title="创建一个新的旅行计划" @back="$router.push('/travel')" />

    <a-card :bordered="false" style="max-width: 600px">
      <a-form :model="form" layout="vertical" @finish="handleSubmit">
        <a-form-item label="旅行名称" name="name" :rules="[{ required: true, message: '请输入旅行名称' }]">
          <a-input v-model:value="form.name" placeholder="例如：厦门之旅" />
        </a-form-item>

        <a-form-item label="目的地" name="destination">
          <a-input v-model:value="form.destination" placeholder="例如：福建厦门" />
        </a-form-item>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="开始日期" name="start_date">
              <a-date-picker v-model:value="form.start_date" style="width: 100%" value-format="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="结束日期" name="end_date">
              <a-date-picker v-model:value="form.end_date" style="width: 100%" value-format="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="16">
          <a-col :span="12">
            <a-form-item label="预算" name="budget">
              <a-input-number v-model:value="form.budget" :min="0" :precision="2" style="width: 100%" placeholder="0.00" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="计划里程(km)" name="planned_km">
              <a-input-number v-model:value="form.planned_km" :min="0" :precision="1" style="width: 100%" placeholder="0" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-form-item label="备注" name="notes">
          <a-textarea v-model:value="form.notes" :rows="3" placeholder="旅行备注..." />
        </a-form-item>

        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="submitting">创建旅行</a-button>
            <a-button @click="$router.push('/travel')">取消</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { travelApi } from '@/api'

const router = useRouter()
const submitting = ref(false)

const form = reactive({
  name: '',
  destination: '',
  start_date: null,
  end_date: null,
  budget: 0,
  planned_km: 0,
  notes: '',
})

async function handleSubmit() {
  submitting.value = true
  try {
    await travelApi.createTrip(form)
    message.success('旅行创建成功')
    router.push('/travel')
  } catch (e) {
    message.error('创建失败：' + (e.response?.data?.detail || e.message))
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.travel-create {
  padding: 0 4px;
}
</style>
