<template>
  <div>
    <!-- 顶部按钮栏 -->
    <div style="display: flex; justify-content: flex-end; gap: 12px; margin-bottom: 16px">
      <a-button @click="$router.push('/sports/cycling/settings')">⚙️ 骑行设置</a-button>
      <a-button @click="showUploadArea = !showUploadArea">
        <template #icon><UploadOutlined /></template>
        {{ showUploadArea ? '收起上传' : '上传活动' }}
      </a-button>
      <a-button type="primary" @click="showModal(null)">+ 添加车辆</a-button>
    </div>

    <!-- 上传活动区域 -->
    <a-card v-if="showUploadArea" title="上传骑行活动" :bordered="false" style="border-radius: 12px; margin-bottom: 24px">
      <a-upload-dragger
        :before-upload="beforeUpload"
        :show-upload-list="false"
        accept=".gpx,.fit"
        :disabled="uploading"
        style="margin-bottom: 16px"
      >
        <p class="ant-upload-drag-icon">
          <InboxOutlined style="font-size: 48px; color: #667eea" />
        </p>
        <p class="ant-upload-text">点击或拖拽 GPX / FIT 文件到此处</p>
        <p class="ant-upload-hint">支持 Garmin、Wahoo、Strava 等设备导出的文件格式</p>
      </a-upload-dragger>
      <a-spin v-if="uploading" tip="正在解析文件..." />

      <!-- 解析预览 -->
      <template v-if="parsed">
        <a-divider />
        <a-form :model="uploadForm" layout="vertical">
          <a-row :gutter="16">
            <a-col :span="12">
              <a-form-item label="活动名称" required>
                <a-input v-model:value="uploadForm.title" size="large" placeholder="请输入活动名称" />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="路线类型">
                <a-select v-model:value="uploadForm.route_type" placeholder="请选择">
                  <a-select-option value="公路">公路</a-select-option>
                  <a-select-option value="山地">山地</a-select-option>
                  <a-select-option value="砾石">砾石</a-select-option>
                  <a-select-option value="室内">室内</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item label="关联车辆">
                <a-select v-model:value="uploadForm.bike_id" placeholder="请选择" allow-clear>
                  <a-select-option v-for="b in bikes" :key="b.id" :value="b.id">{{ b.name }}</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
          </a-row>

          <!-- 核心指标展示 -->
          <a-descriptions :column="4" bordered size="small" style="margin-bottom: 16px">
            <a-descriptions-item label="距离">
              <span class="stat-value">{{ parsed.distance_km }}</span> km
            </a-descriptions-item>
            <a-descriptions-item label="时长">
              <span class="stat-value">{{ formatDuration(parsed.duration_sec) }}</span>
            </a-descriptions-item>
            <a-descriptions-item label="均速">
              <span class="stat-value">{{ parsed.avg_speed_kmh }}</span> km/h
            </a-descriptions-item>
            <a-descriptions-item label="最高速">
              <span class="stat-value">{{ parsed.max_speed_kmh || '-' }}</span>
              <span v-if="parsed.max_speed_kmh"> km/h</span>
            </a-descriptions-item>
            <a-descriptions-item label="爬升">
              <span class="stat-value">{{ parsed.elevation_gain }}</span> m
            </a-descriptions-item>
            <a-descriptions-item label="下降">
              <span class="stat-value">{{ parsed.elevation_loss }}</span> m
            </a-descriptions-item>
            <a-descriptions-item v-if="parsed.avg_power_w" label="均功率">
              <span class="stat-value">{{ parsed.avg_power_w }}</span> W
            </a-descriptions-item>
            <a-descriptions-item v-if="parsed.normalized_power" label="NP">
              <span class="stat-value">{{ parsed.normalized_power }}</span> W
            </a-descriptions-item>
            <a-descriptions-item v-if="parsed.avg_heart_rate" label="均心率">
              <span class="stat-value">{{ parsed.avg_heart_rate }}</span> bpm
            </a-descriptions-item>
            <a-descriptions-item v-if="parsed.max_heart_rate" label="最高心率">
              <span class="stat-value">{{ parsed.max_heart_rate }}</span> bpm
            </a-descriptions-item>
            <a-descriptions-item v-if="parsed.avg_cadence" label="均踏频">
              <span class="stat-value">{{ parsed.avg_cadence }}</span> rpm
            </a-descriptions-item>
            <a-descriptions-item v-if="parsed.tss" label="TSS">
              <span class="stat-value">{{ parsed.tss }}</span>
            </a-descriptions-item>
          </a-descriptions>

          <!-- 地图 -->
          <TrackMap
            v-if="trackPoints.length"
            :track-points="trackPoints"
            style="height: 360px; border-radius: 8px; overflow: hidden; margin-bottom: 16px"
          />

          <a-form-item label="备注">
            <a-textarea v-model:value="uploadForm.notes" :rows="3" placeholder="添加备注（可选）" />
          </a-form-item>

          <a-button type="primary" size="large" :loading="saving" @click="saveActivity">
            💾 保存活动
          </a-button>
          <a-button style="margin-left: 12px" @click="resetUploadForm">重新上传</a-button>
        </a-form>
      </template>
    </a-card>

    <!-- 车辆卡片列表 -->
    <a-row :gutter="16">
      <a-col :span="8" v-for="bike in bikes" :key="bike.id">
        <!-- ── 美化后的车辆卡片 ── -->
        <div class="bike-card">
          <!-- 顶部渐变条 -->
          <div class="bike-card-header" :style="{ background: getBikeAccent(bike) }">
            <div class="bike-card-title-row">
              <span class="bike-card-name">{{ bike.name }}</span>
              <div class="bike-card-actions">
                <a-button type="link" size="small" class="bike-card-btn" @click="showModal(bike)">编辑</a-button>
                <a-popconfirm title="确认删除？" @confirm="deleteBike(bike.id)">
                  <a-button type="link" danger size="small" class="bike-card-btn">删除</a-button>
                </a-popconfirm>
              </div>
            </div>
            <div class="bike-card-sub" v-if="bike.brand || bike.model">
              {{ [bike.brand, bike.model].filter(Boolean).join(' · ') }}
            </div>
          </div>

          <!-- 主体内容 -->
          <div class="bike-card-body">
            <!-- 核心里程数字 -->
            <div class="bike-km-display">
              <div class="bike-km-value">{{ (bike.total_km || 0).toFixed(1) }}</div>
              <div class="bike-km-unit">km 累计里程</div>
            </div>

            <!-- 基础信息标签 -->
            <div class="bike-info-tags">
              <span class="info-tag" v-if="bike.color">
                <span class="tag-dot" :style="{ background: getBikeAccent(bike) }"></span>
                {{ bike.color }}
              </span>
              <span class="info-tag" v-if="bike.weight_kg">
                {{ bike.weight_kg }} kg
              </span>
              <span class="info-tag" v-if="bike.purchase_date">
                {{ bike.purchase_date }}
              </span>
              <span class="info-tag" v-if="bike.purchase_price">
                ¥{{ bike.purchase_price.toLocaleString() }}
              </span>
            </div>

            <!-- 备注 -->
            <div class="bike-notes" v-if="bike.notes">{{ bike.notes }}</div>

            <!-- 维护记录 -->
            <div class="maint-section">
              <div class="maint-header">
                <span class="maint-title">维护记录</span>
                <a-button type="link" size="small" class="maint-add-btn" @click="showMaintenanceModal(bike.id)">
                  + 添加
                </a-button>
              </div>

              <div v-if="maintenanceLoading[bike.id]" style="text-align: center; padding: 12px 0">
                <a-spin size="small" />
              </div>

              <div v-else-if="(maintenanceMap[bike.id] || []).length === 0" class="maint-empty">
                暂无维护记录
              </div>

              <div v-else class="maint-timeline">
                <div
                  v-for="item in (maintenanceMap[bike.id] || []).slice(0, 3)"
                  :key="item.id"
                  class="maint-item"
                >
                  <div class="maint-dot" :style="{ background: getBikeAccent(bike) }"></div>
                  <div class="maint-content">
                    <div class="maint-main">
                      <span class="maint-date">{{ item.date }}</span>
                      <span class="maint-component">{{ item.component }}</span>
                      <span class="maint-action" :style="{ color: getActionColor(item.action) }">{{ item.action }}</span>
                    </div>
                    <div class="maint-sub" v-if="item.cost || item.notes">
                      <span v-if="item.cost">¥{{ item.cost }}</span>
                      <span v-if="item.notes"> · {{ item.notes }}</span>
                    </div>
                  </div>
                  <a-popconfirm title="删除？" @confirm="deleteMaintenance(item.id, bike.id)">
                    <a class="maint-del">×</a>
                  </a-popconfirm>
                </div>
              </div>
            </div>
          </div>
        </div>
      </a-col>
    </a-row>

    <!-- 车辆编辑弹窗 -->
    <a-modal v-model:open="bikeModalOpen" :title="editingBike ? '编辑车辆' : '添加车辆'" @ok="saveBike">
      <a-form :model="bikeForm" layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="车辆名称" required><a-input v-model:value="bikeForm.name" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="品牌"><a-input v-model:value="bikeForm.brand" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="型号"><a-input v-model:value="bikeForm.model" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="颜色"><a-input v-model:value="bikeForm.color" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="重量 (kg)"><a-input-number v-model:value="bikeForm.weight_kg" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="购入价格 (¥)"><a-input-number v-model:value="bikeForm.purchase_price" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="购入日期">
              <a-date-picker v-model:value="bikeForm.purchase_date" style="width: 100%" valueFormat="YYYY-MM-DD" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model:value="bikeForm.notes" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>

    <!-- 维护记录弹窗 -->
    <a-modal v-model:open="maintModalOpen" title="添加维护记录" @ok="saveMaintenance">
      <a-form :model="maintForm" layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="维护部件" required>
              <a-select v-model:value="maintForm.component" show-search allow-clear>
                <a-select-option v-for="c in componentOptions" :key="c" :value="c">{{ c }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="维护类型" required>
              <a-select v-model:value="maintForm.action">
                <a-select-option value="更换">更换</a-select-option>
                <a-select-option value="调整">调整</a-select-option>
                <a-select-option value="清洁">清洁</a-select-option>
                <a-select-option value="润滑">润滑</a-select-option>
                <a-select-option value="检查">检查</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="维护日期"><a-input v-model:value="maintForm.date" placeholder="YYYY-MM-DD" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="费用 (¥)"><a-input-number v-model:value="maintForm.cost" style="width: 100%" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model:value="maintForm.notes" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { UploadOutlined, InboxOutlined } from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { cyclingApi } from '@/api/index'
import TrackMap from '@/components/TrackMap.vue'

const router = useRouter()
const route = useRoute()

const bikes = ref([])
const maintenanceMap = reactive({})
const maintenanceLoading = reactive({})

// 上传活动相关
const showUploadArea = ref(route.query.upload === '1')
const uploading = ref(false)
const saving = ref(false)
const parsed = ref(null)
const trackPoints = ref([])
const uploadForm = ref({
  title: '',
  date: '',
  route_type: '公路',
  bike_id: null,
  notes: '',
})

// 车辆弹窗
const bikeModalOpen = ref(false)
const editingBike = ref(null)
const bikeForm = ref({ name: '', brand: '', model: '', color: '', weight_kg: null, purchase_price: null, purchase_date: null, notes: '' })

// 维护弹窗
const maintModalOpen = ref(false)
const maintForm = ref({ bike_id: null, component: '', action: '更换', date: dayjs().format('YYYY-MM-DD'), cost: null, notes: '' })

const componentOptions = ['链条', '刹车片', '轮胎', '内胎', '变速线', '刹车线', '飞轮', '牙盘', '踏板', '车把带', '坐垫']

loadBikes()

async function loadBikes() {
  try {
    const { data } = await cyclingApi.listBikes()
    bikes.value = data
    data.forEach(b => loadMaintenance(b.id))
  } catch (e) {}
}

async function loadMaintenance(bikeId) {
  maintenanceLoading[bikeId] = true
  try {
    const { data } = await cyclingApi.listMaintenance(bikeId)
    maintenanceMap[bikeId] = data
  } finally {
    maintenanceLoading[bikeId] = false
  }
}

// === 上传活动 ===
async function beforeUpload(file) {
  uploading.value = true
  parsed.value = null
  trackPoints.value = []

  try {
    const { data } = await cyclingApi.upload(file)
    parsed.value = data

    uploadForm.value.title = data.suggested_title || '骑行活动'
    uploadForm.value.date = data.start_time
      ? dayjs(data.start_time).format('YYYY-MM-DD')
      : dayjs().format('YYYY-MM-DD')

    if (data.track_json) {
      try {
        trackPoints.value = typeof data.track_json === 'string'
          ? JSON.parse(data.track_json)
          : data.track_json
      } catch (e) {}
    }
  } catch (e) {
    message.error(e.response?.data?.detail || '文件解析失败，请检查文件格式')
  } finally {
    uploading.value = false
  }
  return false
}

async function saveActivity() {
  if (!uploadForm.value.title) {
    message.warning('请填写活动名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...uploadForm.value,
      distance_km: parsed.value.distance_km,
      duration_sec: parsed.value.duration_sec,
      elevation_gain: parsed.value.elevation_gain,
      elevation_loss: parsed.value.elevation_loss,
      max_elevation: parsed.value.max_elevation,
      min_elevation: parsed.value.min_elevation,
      avg_speed_kmh: parsed.value.avg_speed_kmh,
      max_speed_kmh: parsed.value.max_speed_kmh,
      avg_power_w: parsed.value.avg_power_w,
      max_power_w: parsed.value.max_power_w,
      normalized_power: parsed.value.normalized_power,
      tss: parsed.value.tss,
      avg_heart_rate: parsed.value.avg_heart_rate,
      max_heart_rate: parsed.value.max_heart_rate,
      avg_cadence: parsed.value.avg_cadence,
      max_cadence: parsed.value.max_cadence,
      calories: parsed.value.calories,
      start_time: parsed.value.start_time,
      end_time: parsed.value.end_time,
      file_type: parsed.value.file_type,
      file_path: parsed.value.file_path,
      track_json: parsed.value.track_json,
    }
    await cyclingApi.saveActivity(payload)
    message.success('活动保存成功！')
    showUploadArea.value = false
    resetUploadForm()
    loadBikes()
    router.push('/sports/cycling/list')
  } catch (e) {
    message.error('保存失败')
  } finally {
    saving.value = false
  }
}

function resetUploadForm() {
  parsed.value = null
  trackPoints.value = []
  uploadForm.value = { title: '', date: '', route_type: '公路', bike_id: null, notes: '' }
}

function formatDuration(sec) {
  if (!sec) return '-'
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  const s = sec % 60
  if (h > 0) return `${h}h ${m}m`
  return `${m}m ${s}s`
}

// === 车辆管理 ===
function showModal(bike) {
  editingBike.value = bike
  if (bike) {
    bikeForm.value = { ...bike }
  } else {
    bikeForm.value = { name: '', brand: '', model: '', color: '', weight_kg: null, purchase_price: null, purchase_date: null, notes: '' }
  }
  bikeModalOpen.value = true
}

async function saveBike() {
  if (!bikeForm.value.name) { message.warning('请填写车辆名称'); return }
  try {
    if (editingBike.value) {
      await cyclingApi.updateBike(editingBike.value.id, bikeForm.value)
    } else {
      await cyclingApi.createBike(bikeForm.value)
    }
    message.success('保存成功')
    bikeModalOpen.value = false
    loadBikes()
  } catch (e) {
    message.error('保存失败')
  }
}

async function deleteBike(id) {
  await cyclingApi.deleteBike(id)
  message.success('已删除')
  loadBikes()
}

// === 维护记录 ===
function showMaintenanceModal(bikeId) {
  maintForm.value = { bike_id: bikeId, component: '', action: '更换', date: dayjs().format('YYYY-MM-DD'), cost: null, notes: '' }
  maintModalOpen.value = true
}

async function saveMaintenance() {
  try {
    await cyclingApi.createMaintenance(maintForm.value)
    message.success('记录已添加')
    maintModalOpen.value = false
    loadMaintenance(maintForm.value.bike_id)
  } catch (e) {
    message.error('保存失败')
  }
}

async function deleteMaintenance(id, bikeId) {
  await cyclingApi.deleteMaintenance(id)
  message.success('已删除')
  loadMaintenance(bikeId)
}

// ── 卡片美化辅助 ──────────────────────────────────────────────
const bikeColors = [
  'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',   // 紫蓝
  'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',   // 粉红
  'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',   // 青蓝
  'linear-gradient(135deg, #43e97b 0%, #38f9d7 100%)',   // 绿松
  'linear-gradient(135deg, #fa709a 0%, #fee140 100%)',   // 橙粉
  'linear-gradient(135deg, #a18cd1 0%, #fbc2eb 100%)',   // 淡紫
  'linear-gradient(135deg, #30cfd0 0%, #330867 100%)',   // 深青
  'linear-gradient(135deg, #f7971e 0%, #ffd200 100%)',   // 金黄
]
const actionColors = {
  '更换': '#e63946',
  '调整': '#f4a261',
  '清洁': '#2a9d8f',
  '润滑': '#457b9d',
  '检查': '#6c757d',
}

function getBikeAccent(bike) {
  // 根据 bike.id 取模分配渐变色，保证同一车辆颜色固定
  return bikeColors[(bike.id - 1) % bikeColors.length]
}

function getActionColor(action) {
  return actionColors[action] || '#6c757d'
}
</script>

<style scoped>
/* ── 上传解析指标 ─────────────────────────────────── */
.stat-value {
  font-size: 18px;
  font-weight: bold;
  color: #667eea;
}

/* ── 车辆卡片（美化版） ─────────────────────────────── */
.bike-card {
  background: #fff;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: transform .2s, box-shadow .2s;
  margin-bottom: 16px;
}
.bike-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

/* 顶部渐变头 */
.bike-card-header {
  padding: 16px 16px 14px;
  color: #fff;
}
.bike-card-title-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.bike-card-name {
  font-size: 17px;
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,.2);
}
.bike-card-actions {
  display: flex;
  gap: 4px;
}
.bike-card-btn {
  color: rgba(255,255,255,.9) !important;
  padding: 0 6px !important;
  font-size: 12px !important;
}
.bike-card-btn:hover { color: #fff !important; }
.bike-card-sub {
  font-size: 12px;
  color: rgba(255,255,255,.85);
  margin-top: 3px;
}

/* 主体 */
.bike-card-body {
  padding: 16px;
}

/* 核心里程 */
.bike-km-display {
  text-align: center;
  padding: 8px 0 14px;
  border-bottom: 1px dashed #f0f0f0;
  margin-bottom: 12px;
}
.bike-km-value {
  font-size: 36px;
  font-weight: 800;
  color: #1e293b;
  line-height: 1;
  letter-spacing: -1px;
}
.bike-km-unit {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 4px;
}

/* 信息标签 */
.bike-info-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 10px;
}
.info-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #64748b;
  background: #f1f5f9;
  padding: 3px 8px;
  border-radius: 20px;
}
.tag-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 备注 */
.bike-notes {
  font-size: 12px;
  color: #94a3b8;
  margin-bottom: 12px;
  line-height: 1.5;
  padding: 6px 10px;
  background: #fafafa;
  border-radius: 6px;
  border-left: 3px solid #e2e8f0;
}

/* 维护记录 */
.maint-section {
  margin-top: 4px;
}
.maint-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.maint-title {
  font-size: 13px;
  font-weight: 600;
  color: #475569;
}
.maint-add-btn {
  font-size: 12px !important;
  padding: 0 !important;
  color: #667eea !important;
}
.maint-empty {
  font-size: 12px;
  color: #cbd5e1;
  text-align: center;
  padding: 8px 0;
}
.maint-timeline {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.maint-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  position: relative;
}
.maint-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
  margin-top: 4px;
}
.maint-content {
  flex: 1;
  min-width: 0;
}
.maint-main {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.maint-date {
  font-size: 12px;
  color: #94a3b8;
  flex-shrink: 0;
}
.maint-component {
  font-size: 12px;
  color: #334155;
  font-weight: 500;
}
.maint-action {
  font-size: 12px;
  font-weight: 600;
}
.maint-sub {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 1px;
}
.maint-del {
  font-size: 16px;
  color: #cbd5e1;
  line-height: 1;
  flex-shrink: 0;
  cursor: pointer;
  padding: 0 2px;
}
.maint-del:hover { color: #ef4444; }
</style>
