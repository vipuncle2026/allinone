<template>
  <div>
    <div style="display: flex; justify-content: flex-end; margin-bottom: 16px">
      <a-button type="primary" @click="showVehicleModal(null)">+ 添加车辆</a-button>
    </div>

    <a-row :gutter="20">
      <a-col :span="8" v-for="v in vehicles" :key="v.id">
        <div class="vehicle-card" :class="getFuelClass(v.fuel_type)" @click="goFuel(v.id)">
          <!-- 顶部操作栏 -->
          <div class="card-actions">
            <a-button type="text" size="small" class="action-btn" @click.stop="showVehicleModal(v)">
              ✏️ 编辑
            </a-button>
            <a-popconfirm title="确认删除该车辆及其所有记录？" @confirm="deleteVehicle(v.id)">
              <a-button type="text" size="small" class="action-btn danger" @click.stop>🗑️ 删除</a-button>
            </a-popconfirm>
          </div>

          <!-- 车辆图标 + 名称 -->
          <div class="card-header">
            <div class="vehicle-icon" :class="getFuelClass(v.fuel_type)">
              {{ getVehicleEmoji(v.fuel_type) }}
            </div>
            <div class="vehicle-name">{{ v.name }}</div>
            <div class="fuel-badge" :class="getFuelClass(v.fuel_type)">{{ v.fuel_type || '未知' }}</div>
          </div>

          <!-- 基本信息 -->
          <div class="card-info">
            <div class="info-row" v-if="v.brand || v.model">
              <span class="info-label">品牌型号</span>
              <span class="info-value">{{ [v.brand, v.model].filter(Boolean).join(' ') || '-' }}</span>
            </div>
            <div class="info-row" v-if="v.plate">
              <span class="info-label">车牌号</span>
              <span class="info-value plate">{{ v.plate }}</span>
            </div>
            <div class="info-row" v-if="v.purchase_date">
              <span class="info-label">购入日期</span>
              <span class="info-value">{{ v.purchase_date }}</span>
            </div>
          </div>

          <!-- 分割线 -->
          <div class="card-divider" :class="getFuelClass(v.fuel_type)"></div>

          <!-- 数据统计 -->
          <div class="card-stats">
            <div class="stat-item">
              <div class="stat-number mileage">{{ (v.current_mileage || 0).toLocaleString() }}</div>
              <div class="stat-label">当前里程 (km)</div>
            </div>
            <div class="stat-item">
              <div class="stat-number">{{ v.fuel_count || 0 }}</div>
              <div class="stat-label">{{ isElectric(v.fuel_type) ? '充电次数' : '加油次数' }}</div>
            </div>
            <div class="stat-item">
              <div class="stat-number cost">¥{{ (v.total_spending || 0).toLocaleString() }}</div>
              <div class="stat-label">总支出</div>
            </div>
          </div>
        </div>
      </a-col>
      <a-col :span="8" v-if="!vehicles.length">
        <div class="empty-card">
          <div class="empty-icon">🚗</div>
          <div style="color: #999; font-size: 14px">暂无车辆</div>
          <div style="color: #bbb; font-size: 12px; margin-top: 4px">点击右上角添加</div>
        </div>
      </a-col>
    </a-row>

    <!-- 车辆编辑弹窗 -->
    <a-modal v-model:open="vehicleModalOpen" :title="editingVehicle ? '编辑车辆' : '添加车辆'" @ok="saveVehicle" width="600px">
      <a-form :model="vehicleForm" layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="车辆名称" required><a-input v-model:value="vehicleForm.name" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="品牌"><a-input v-model:value="vehicleForm.brand" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="型号"><a-input v-model:value="vehicleForm.model" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="颜色"><a-input v-model:value="vehicleForm.color" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="车牌号"><a-input v-model:value="vehicleForm.plate" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="燃料类型">
              <a-select v-model:value="vehicleForm.fuel_type">
                <a-select-option value="汽油">汽油</a-select-option>
                <a-select-option value="柴油">柴油</a-select-option>
                <a-select-option value="电动">电动</a-select-option>
                <a-select-option value="混动">混动</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="购入价格 (¥)"><a-input-number v-model:value="vehicleForm.purchase_price" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="购入日期"><a-date-picker v-model:value="vehicleForm.purchase_date" style="width: 100%" valueFormat="YYYY-MM-DD" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="当前里程 (km)"><a-input-number v-model:value="vehicleForm.current_mileage" style="width: 100%" /></a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="备注"><a-textarea v-model:value="vehicleForm.notes" :rows="2" /></a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { vehicleApi } from '@/api/index'

const router = useRouter()
const vehicles = ref([])
const vehicleModalOpen = ref(false)
const editingVehicle = ref(null)
const vehicleForm = ref({
  name: '', brand: '', model: '', color: '', plate: '', fuel_type: '汽油',
  purchase_date: null, purchase_price: null, current_mileage: 0, notes: ''
})

function isElectric(type) {
  return ['电动', '纯电', '纯电动'].includes(type)
}

function getFuelClass(type) {
  if (isElectric(type)) return 'ev'
  if (type === '混动') return 'hybrid'
  return 'fuel'
}

function getVehicleEmoji(type) {
  if (isElectric(type)) return '⚡'
  if (type === '混动') return '🔋'
  return '⛽'
}

onMounted(loadVehicles)

async function loadVehicles() {
  try {
    const { data } = await vehicleApi.list()
    vehicles.value = data
  } catch (e) { message.error('加载失败') }
}

function showVehicleModal(v) {
  editingVehicle.value = v
  if (v) {
    vehicleForm.value = { ...v, purchase_date: v.purchase_date || null }
  } else {
    vehicleForm.value = { name: '', brand: '', model: '', color: '', plate: '', fuel_type: '汽油', purchase_date: null, purchase_price: null, current_mileage: 0, notes: '' }
  }
  vehicleModalOpen.value = true
}

async function saveVehicle() {
  if (!vehicleForm.value.name) { message.warning('请填写车辆名称'); return }
  try {
    if (editingVehicle.value) {
      await vehicleApi.update(editingVehicle.value.id, vehicleForm.value)
    } else {
      await vehicleApi.create(vehicleForm.value)
    }
    message.success('保存成功')
    vehicleModalOpen.value = false
    loadVehicles()
  } catch (e) { message.error('保存失败') }
}

async function deleteVehicle(id) {
  await vehicleApi.delete(id)
  message.success('已删除')
  loadVehicles()
}

function goFuel(id) {
  router.push(`/vehicle/fuel?vid=${id}`)
}
</script>

<style scoped>
.vehicle-card {
  position: relative;
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 20px;
  cursor: pointer;
  transition: all 0.3s ease;
  overflow: hidden;
}

.vehicle-card::before {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  opacity: 0;
  transition: opacity 0.3s ease;
  border-radius: 16px;
}

.vehicle-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
}

/* ── 燃油车：暖橙色调 ── */
.vehicle-card.fuel {
  background: linear-gradient(145deg, #fff7ed 0%, #fef3e2 100%);
  border: 1px solid #fed7aa;
}
.vehicle-card.fuel:hover::before {
  opacity: 1;
  background: linear-gradient(145deg, #fff7ed 0%, #fde6c4 100%);
}

/* ── 电动车：清新绿色调 ── */
.vehicle-card.ev {
  background: linear-gradient(145deg, #f0fdf4 0%, #dcfce7 100%);
  border: 1px solid #bbf7d0;
}
.vehicle-card.ev:hover::before {
  opacity: 1;
  background: linear-gradient(145deg, #f0fdf4 0%, #d1fae5 100%);
}

/* ── 混动：紫蓝色调 ── */
.vehicle-card.hybrid {
  background: linear-gradient(145deg, #faf5ff 0%, #f3e8ff 100%);
  border: 1px solid #e9d5ff;
}
.vehicle-card.hybrid:hover::before {
  opacity: 1;
  background: linear-gradient(145deg, #faf5ff 0%, #ede5ff 100%);
}

/* ── 顶部操作栏 ── */
.card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
  margin-bottom: 12px;
  position: relative;
  z-index: 1;
}
.action-btn {
  font-size: 12px;
  color: #94a3b8;
  padding: 0 8px;
}
.action-btn.danger {
  color: #ef4444;
}
.action-btn:hover {
  color: #475569;
  background: rgba(0,0,0,0.04);
}
.action-btn.danger:hover {
  color: #dc2626;
  background: rgba(239, 68, 68, 0.06);
}

/* ── 车辆头部 ── */
.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  position: relative;
  z-index: 1;
}
.vehicle-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  flex-shrink: 0;
}
.vehicle-icon.fuel {
  background: linear-gradient(135deg, #fb923c, #f97316);
  box-shadow: 0 4px 12px rgba(249, 115, 22, 0.3);
}
.vehicle-icon.ev {
  background: linear-gradient(135deg, #34d399, #10b981);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
}
.vehicle-icon.hybrid {
  background: linear-gradient(135deg, #a78bfa, #8b5cf6);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
}
.vehicle-name {
  font-size: 18px;
  font-weight: 700;
  color: #1e293b;
  flex: 1;
}
.fuel-badge {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 20px;
  font-weight: 600;
  flex-shrink: 0;
}
.fuel-badge.fuel {
  background: #fff7ed;
  color: #ea580c;
  border: 1px solid #fdba74;
}
.fuel-badge.ev {
  background: #f0fdf4;
  color: #16a34a;
  border: 1px solid #86efac;
}
.fuel-badge.hybrid {
  background: #faf5ff;
  color: #7c3aed;
  border: 1px solid #c4b5fd;
}

/* ── 基本信息 ── */
.card-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  position: relative;
  z-index: 1;
}
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.info-label {
  color: #94a3b8;
}
.info-value {
  color: #475569;
  font-weight: 500;
}
.info-value.plate {
  font-family: 'SF Mono', 'Menlo', monospace;
  letter-spacing: 1px;
  background: rgba(0,0,0,0.04);
  padding: 1px 8px;
  border-radius: 4px;
}

/* ── 分割线 ── */
.card-divider {
  height: 1px;
  margin: 16px 0;
  position: relative;
  z-index: 1;
}
.card-divider.fuel {
  background: linear-gradient(90deg, transparent, #fdba74, transparent);
}
.card-divider.ev {
  background: linear-gradient(90deg, transparent, #86efac, transparent);
}
.card-divider.hybrid {
  background: linear-gradient(90deg, transparent, #c4b5fd, transparent);
}

/* ── 数据统计 ── */
.card-stats {
  display: flex;
  justify-content: space-around;
  position: relative;
  z-index: 1;
}
.stat-item {
  text-align: center;
}
.stat-number {
  font-size: 20px;
  font-weight: 700;
  color: #1e293b;
}
.stat-number.mileage {
  color: #0ea5e9;
}
.stat-number.cost {
  color: #e11d48;
}
.stat-label {
  font-size: 11px;
  color: #94a3b8;
  margin-top: 2px;
}

/* ── 空状态 ── */
.empty-card {
  border-radius: 16px;
  border: 2px dashed #e2e8f0;
  padding: 60px 20px;
  text-align: center;
  margin-bottom: 20px;
}
.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.3;
}
</style>
