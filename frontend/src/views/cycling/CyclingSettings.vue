<template>
  <div class="cycling-settings">
    <a-card title="🚴 骑行参数设置" :bordered="false" style="border-radius: 12px; max-width: 600px">
      <a-alert
        message="默认 FTP 设置后，每次上传 FIT/GPX 文件时会自动填入，无需重复填写。"
        type="info"
        show-icon
        style="margin-bottom: 24px"
      />

      <a-form layout="vertical">
        <a-form-item label="默认 FTP（功能阈值功率）">
          <template #extra>
            FTP（Functional Threshold Power）是骑行者能够持续保持1小时的最高平均功率，单位为瓦特（W）。用于计算 NP、TSS 等训练指标。
          </template>
          <a-input-number
            v-model:value="ftp"
            :min="50"
            :max="500"
            :step="5"
            addon-after="W"
            style="width: 200px; font-size: 16px"
            size="large"
          />
          <div style="margin-top: 8px; color: #64748b; font-size: 13px">
            快速设置：
            <a-tag v-for="ref in ftpRefs" :key="ref.level" :color="ref.color" style="margin-right: 4px; cursor: pointer" @click="ftp = ref.ftp">
              {{ ref.level }}：{{ ref.ftp }}W
            </a-tag>
          </div>
        </a-form-item>

        <a-form-item>
          <a-button type="primary" size="large" :loading="saving" @click="save">
            💾 保存设置
          </a-button>
          <span v-if="saved" style="margin-left: 16px; color: #22c55e; font-size: 14px">✓ 已保存</span>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="📊 FTP 等级参考" :bordered="false" style="border-radius: 12px; max-width: 600px; margin-top: 20px">
      <a-table
        :dataSource="levelTable"
        :columns="columns"
        size="small"
        :pagination="false"
        row-key="level"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'level'">
            <a-tag :color="record.color">{{ record.level }}</a-tag>
          </template>
          <template v-if="column.dataIndex === 'wkg'">
            <span :style="{ color: record.color }">{{ record.wkg }} W/kg</span>
          </template>
        </template>
      </a-table>
      <div style="color: #94a3b8; font-size: 12px; margin-top: 12px">
        * W/kg = FTP / 体重（kg），数据仅供参考，实际 FTP 建议通过 FTP 测试获得。
      </div>
    </a-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { cyclingApi } from '@/api/index'

const ftp = ref(200)
const saving = ref(false)
const saved = ref(false)

const ftpRefs = [
  { level: '入门', ftp: 150, color: 'green' },
  { level: '业余', ftp: 200, color: 'blue' },
  { level: '进阶', ftp: 250, color: 'orange' },
  { level: '精英', ftp: 300, color: 'red' },
]

const levelTable = [
  { level: '入门级', ftp: '100~180', wkg: '1.5~2.5', color: '#22c55e' },
  { level: '业余爱好者', ftp: '180~220', wkg: '2.5~3.0', color: '#3b82f6' },
  { level: '进阶骑手', ftp: '220~280', wkg: '3.0~3.5', color: '#f59e0b' },
  { level: '精英骑手', ftp: '280~340', wkg: '3.5~4.5', color: '#ef4444' },
  { level: '职业车手', ftp: '340+', wkg: '4.5+', color: '#7c3aed' },
]

const columns = [
  { title: '等级', dataIndex: 'level', width: 150 },
  { title: 'FTP 范围', dataIndex: 'ftp', width: 200 },
  { title: 'W/kg 参考', dataIndex: 'wkg', width: 150 },
]

async function loadDefaults() {
  try {
    const { data } = await cyclingApi.getDefaults()
    ftp.value = data.default_ftp || 200
  } catch {}
}

async function save() {
  saving.value = true
  saved.value = false
  try {
    await cyclingApi.saveDefaults({ default_ftp: ftp.value })
    message.success('保存成功')
    saved.value = true
    setTimeout(() => { saved.value = false }, 3000)
  } catch {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadDefaults)
</script>

<style scoped>
.cycling-settings { max-width: 700px; }
</style>
