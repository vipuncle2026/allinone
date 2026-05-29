<template>
  <div>
    <!-- 统计卡片 -->
    <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 14px; margin-bottom: 20px">
      <!-- 燃油车统计 -->
      <template v-if="!isElectric">
        <div class="stat-card" style="background: linear-gradient(135deg, #0ea5e9, #38bdf8)">
          <div class="stat-label">加油次数</div>
          <div class="stat-val">{{ stats.fuel_count || 0 }}</div>
          <div class="stat-unit">次</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #059669, #10b981)">
          <div class="stat-label">总加油量</div>
          <div class="stat-val">{{ stats.total_fuel_liters || 0 }}</div>
          <div class="stat-unit">升</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #b45309, #d97706)">
          <div class="stat-label">总油费</div>
          <div class="stat-val">¥{{ (stats.total_fuel_cost || 0).toLocaleString() }}</div>
          <div class="stat-unit">元</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #8b5cf6, #a78bfa)">
          <div class="stat-label">平均油耗</div>
          <div class="stat-val">{{ stats.avg_consumption || '-' }}</div>
          <div class="stat-unit">L/100km</div>
        </div>
      </template>
      <!-- 电动车统计 -->
      <template v-else>
        <div class="stat-card" style="background: linear-gradient(135deg, #0ea5e9, #38bdf8)">
          <div class="stat-label">充电次数</div>
          <div class="stat-val">{{ stats.fuel_count || 0 }}</div>
          <div class="stat-unit">次</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #059669, #10b981)">
          <div class="stat-label">总充电量</div>
          <div class="stat-val">{{ stats.total_energy_kwh || 0 }}</div>
          <div class="stat-unit">kWh</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #b45309, #d97706)">
          <div class="stat-label">总电费</div>
          <div class="stat-val">¥{{ (stats.total_fuel_cost || 0).toLocaleString() }}</div>
          <div class="stat-unit">元</div>
        </div>
        <div class="stat-card" style="background: linear-gradient(135deg, #8b5cf6, #a78bfa)">
          <div class="stat-label">平均电耗</div>
          <div class="stat-val">{{ stats.avg_electricity_consumption || '-' }}</div>
          <div class="stat-unit">kWh/100km</div>
        </div>
      </template>
      <div class="stat-card" style="background: linear-gradient(135deg, #ef4444, #f87171)">
        <div class="stat-label">总费用</div>
        <div class="stat-val">¥{{ (stats.total_expense || 0).toLocaleString() }}</div>
        <div class="stat-unit">元</div>
      </div>
      <div class="stat-card" style="background: linear-gradient(135deg, #e11d48, #fb7185)">
        <div class="stat-label">总支出</div>
        <div class="stat-val">¥{{ (stats.total_spending || 0).toLocaleString() }}</div>
        <div class="stat-unit">元</div>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="filter-bar">
      <a-radio-group v-model:value="activeTab" button-style="solid" @change="loadData">
        <a-radio-button value="fuel">{{ isElectric ? '⚡ 充电记录' : '⛽ 油耗记录' }}</a-radio-button>
        <a-radio-button value="expense">🔧 费用记录</a-radio-button>
      </a-radio-group>
      <div style="flex: 1"></div>
      <a-upload :before-upload="handleImport" :show-upload-list="false" accept=".xlsx,.xls">
        <a-button>📤 导入 Excel</a-button>
      </a-upload>
      <a-button @click="handleExport" style="margin-left: 8px">📥 导出 Excel</a-button>
      <a-button type="primary" @click="showAddModal" style="margin-left: 8px">+ 添加</a-button>
      <a-button @click="$router.push('/vehicle/list')" style="margin-left: 8px">← 返回</a-button>
    </div>

    <!-- 油耗/充电记录表格 -->
    <a-table v-if="activeTab === 'fuel'"
      :data-source="fuelRecords" :columns="currentFuelColumns" :loading="loading"
      :pagination="pagination" row-key="id" @change="onPageChange"
    >
      <template #bodyCell="{ column, record }">
        <!-- 燃油车列 -->
        <template v-if="column.key === 'unit_price'">
          <span style="color: #f59e0b">{{ record.unit_price ? '¥' + record.unit_price.toFixed(2) : '-' }}</span>
        </template>
        <template v-if="column.key === 'trip_mileage'">
          <span>{{ record.trip_mileage ? record.trip_mileage + ' km' : '-' }}</span>
        </template>
        <template v-if="column.key === 'fuel_amount'">
          <span>{{ record.fuel_amount != null ? record.fuel_amount + ' L' : '-' }}</span>
        </template>
        <template v-if="column.key === 'total_mileage'">
          <span>{{ record.total_mileage != null ? record.total_mileage.toLocaleString() : '-' }}</span>
        </template>
        <template v-if="column.key === 'actual_cost'">
          <span style="font-weight: bold; color: #f59e0b">¥{{ (record.actual_cost || 0).toFixed(2) }}</span>
        </template>
        <template v-if="column.key === 'fuel_consumption'">
          <span :style="{ color: record.fuel_consumption > 10 ? '#ef4444' : '#059669', fontWeight: 600 }">
            {{ record.fuel_consumption ? record.fuel_consumption + ' L' : '-' }}
          </span>
        </template>
        <template v-if="column.key === 'is_full'">
          <a-tag :color="record.is_full ? 'green' : 'default'">{{ record.is_full ? '加满' : '未满' }}</a-tag>
        </template>
        <!-- 电动车列 -->
        <template v-if="column.key === 'energy_kwh'">
          <span>{{ record.energy_kwh != null ? record.energy_kwh + ' kWh' : '-' }}</span>
        </template>
        <template v-if="column.key === 'electricity_price'">
          <span style="color: #f59e0b">{{ record.electricity_price ? '¥' + record.electricity_price.toFixed(3) : '-' }}</span>
        </template>
        <template v-if="column.key === 'electricity_consumption'">
          <span :style="{ color: record.electricity_consumption > 20 ? '#ef4444' : '#059669', fontWeight: 600 }">
            {{ record.electricity_consumption ? record.electricity_consumption + ' kWh' : '-' }}
          </span>
        </template>
        <template v-if="column.key === 'charge_type'">
          <a-tag :color="chargeTypeColor(record.charge_type)">{{ record.charge_type || '-' }}</a-tag>
        </template>
        <template v-if="column.key === 'soc_range'">
          <span v-if="record.soc_start != null && record.soc_end != null">
            {{ record.soc_start }}% → {{ record.soc_end }}%
          </span>
          <span v-else>-</span>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="showEditFuel(record)">编辑</a-button>
            <a-popconfirm title="确认删除？" @confirm="deleteFuel(record.id)">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- 费用表格 -->
    <a-table v-if="activeTab === 'expense'"
      :data-source="expenseRecords" :columns="expenseColumns" :loading="loading"
      :pagination="pagination" row-key="id" @change="onPageChange"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'amount'">
          <span style="font-weight: bold; color: #ef4444">¥{{ (record.amount || 0).toFixed(2) }}</span>
        </template>
        <template v-if="column.key === 'expense_type'">
          <a-tag color="blue">{{ record.expense_type || '其他' }}</a-tag>
        </template>
        <template v-if="column.key === 'action'">
          <a-space>
            <a-button type="link" size="small" @click="showEditExpense(record)">编辑</a-button>
            <a-popconfirm title="确认删除？" @confirm="deleteExpense(record.id)">
              <a-button type="link" danger size="small">删除</a-button>
            </a-popconfirm>
          </a-space>
        </template>
      </template>
    </a-table>

    <!-- ═══════════ 油耗录入弹窗（燃油车） ═══════════ -->
    <a-modal v-if="!isElectric" v-model:open="fuelModalOpen"
      :title="editingFuel ? '编辑加油记录' : '添加加油记录'" @ok="saveFuel" width="640px"
    >
      <a-alert v-if="computedTrip" type="info" show-icon style="margin-bottom: 16px">
        <template #message>与上次加油间隔 <b>{{ computedTrip }} km</b>，上次里程 {{ lastMileage }} km</template>
      </a-alert>
      <a-form :model="fuelForm" layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="日期时间" required>
              <a-date-picker v-model:value="fuelForm.fuel_date" show-time style="width: 100%" valueFormat="YYYY-MM-DD HH:mm:ss" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="总里程 (km)">
              <a-input-number v-model:value="fuelForm.total_mileage" style="width: 100%" @change="onMileageChange" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="油号">
              <a-select v-model:value="fuelForm.fuel_grade">
                <a-select-option value="92#">92#</a-select-option>
                <a-select-option value="95#">95#</a-select-option>
                <a-select-option value="98#">98#</a-select-option>
                <a-select-option value="0#柴油">0#柴油</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="单价 (元/L)">
              <a-input-number v-model:value="fuelForm.unit_price" :precision="2" :min="0" style="width: 100%" @change="onPriceOrCostChange('price')" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="实付金额 (元)">
              <a-input-number v-model:value="fuelForm.actual_cost" :precision="2" :min="0" style="width: 100%" @change="onPriceOrCostChange('cost')" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="加油量 (L)">
              <a-input-number v-model:value="fuelForm.fuel_amount" :precision="2" :min="0" style="width: 100%"
                :placeholder="autoFuelAmount ? '自动计算' : ''"
                @change="onFuelAmountChange" />
              <div v-if="autoFuelAmount" style="font-size: 11px; color: #999; margin-top: 2px">自动 = 金额 ÷ 单价</div>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="机显金额"><a-input-number v-model:value="fuelForm.display_cost" :precision="2" :min="0" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="油耗 (L/100km)">
              <a-input-number v-model:value="fuelForm.fuel_consumption" :precision="2" :min="0" style="width: 100%"
                :placeholder="autoFuelConsumption ? '自动计算' : ''" />
              <div v-if="autoFuelConsumption" style="font-size: 11px; color: #999; margin-top: 2px">自动 = 加油量 ÷ 行程 × 100</div>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="加满"><a-switch v-model:checked="fuelForm.is_full" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="亮灯"><a-switch v-model:checked="fuelForm.is_low_fuel" /></a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="跳过"><a-switch v-model:checked="fuelForm.is_missed" /></a-form-item>
          </a-col>
          <a-col :span="24">
            <a-form-item label="加油站"><a-input v-model:value="fuelForm.station_name" /></a-form-item>
          </a-col>
          <a-col :span="24">
            <a-form-item label="备注"><a-textarea v-model:value="fuelForm.notes" :rows="2" /></a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>

    <!-- ═══════════ 充电录入弹窗（电动车） ═══════════ -->
    <a-modal v-if="isElectric" v-model:open="fuelModalOpen"
      :title="editingFuel ? '编辑充电记录' : '添加充电记录'" @ok="saveFuel" width="520px"
    >
      <a-alert v-if="computedTrip" type="info" show-icon style="margin-bottom: 16px">
        <template #message>与上次充电间隔 <b>{{ computedTrip }} km</b>，上次里程 {{ lastMileage }} km</template>
      </a-alert>

      <div class="ev-form">
        <!-- Row 1: 日期 + 里程 -->
        <div class="ev-row">
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">充电日期</div>
            <a-date-picker v-model:value="fuelForm.fuel_date" show-time style="width: 100%" valueFormat="YYYY-MM-DD HH:mm:ss" />
          </div>
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">当前里程 (km)</div>
            <a-input-number v-model:value="fuelForm.total_mileage" :precision="0" style="width: 100%" placeholder="必填" @change="onMileageChange" />
          </div>
        </div>

        <!-- Row 2: 充电方式 -->
        <div class="ev-row">
          <div class="ev-field">
            <div class="ev-label">充电方式</div>
            <a-radio-group v-model:value="fuelForm.charge_type" button-style="solid">
              <a-radio-button value="快充">快充</a-radio-button>
              <a-radio-button value="慢充">慢充</a-radio-button>
              <a-radio-button value="家充">家充</a-radio-button>
            </a-radio-group>
          </div>
        </div>

        <!-- Row 3: SOC 电量 -->
        <div class="ev-row">
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">充电前电量 (%)</div>
            <a-input-number v-model:value="fuelForm.soc_start" :precision="0" :min="0" :max="100" style="width: 100%" placeholder="0" />
          </div>
          <div style="display: flex; align-items: center; padding-bottom: 18px; color: #bbb; font-size: 16px">→</div>
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">充电后电量 (%)</div>
            <a-input-number v-model:value="fuelForm.soc_end" :precision="0" :min="0" :max="100" style="width: 100%" placeholder="100" />
          </div>
        </div>

        <!-- SOC 进度条 -->
        <div v-if="fuelForm.soc_start != null && fuelForm.soc_end != null" class="soc-bar-wrap">
          <div class="soc-bar">
            <div class="soc-bar-fill" :style="{ width: fuelForm.soc_end + '%', marginLeft: fuelForm.soc_start + '%' }"></div>
          </div>
          <div class="soc-bar-labels">
            <span>{{ fuelForm.soc_start }}%</span>
            <span style="color: #059669; font-weight: 600">+{{ Math.max(0, fuelForm.soc_end - fuelForm.soc_start) }}%</span>
            <span>{{ fuelForm.soc_end }}%</span>
          </div>
        </div>

        <!-- 分割线 -->
        <div class="ev-divider">费用信息</div>

        <!-- Row 4: 电价 + 金额 -->
        <div class="ev-row">
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">电价 (元/kWh)</div>
            <a-input-number v-model:value="fuelForm.electricity_price" :precision="3" :min="0" style="width: 100%" placeholder="1.500"
              @change="onElecPriceOrCostChange('price')" />
          </div>
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">实付金额 (元)</div>
            <a-input-number v-model:value="fuelForm.actual_cost" :precision="2" :min="0" style="width: 100%" placeholder="0.00"
              @change="onElecPriceOrCostChange('cost')" />
          </div>
        </div>

        <!-- Row 5: 充电量 + 电耗 -->
        <div class="ev-row">
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">充电量 (kWh)</div>
            <a-input-number v-model:value="fuelForm.energy_kwh" :precision="2" :min="0" style="width: 100%"
              :placeholder="autoEnergyKwh ? '自动计算' : '0.00'"
              @change="onEnergyKwhChange" />
            <div v-if="autoEnergyKwh" class="ev-hint">自动 = 金额 ÷ 电价</div>
          </div>
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">电耗 (kWh/100km)</div>
            <a-input-number v-model:value="fuelForm.electricity_consumption" :precision="2" :min="0" style="width: 100%"
              :placeholder="autoElecConsumption ? '自动计算' : '0.00'" />
            <div v-if="autoElecConsumption" class="ev-hint">自动 = 充电量 ÷ 行程 × 100</div>
          </div>
        </div>

        <!-- 分割线 -->
        <div class="ev-divider">其他信息</div>

        <!-- Row 6: 充电站 + 备注 -->
        <div class="ev-row">
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">充电站</div>
            <a-input v-model:value="fuelForm.station_name" placeholder="充电站/充电桩名称" />
          </div>
        </div>
        <div class="ev-row">
          <div class="ev-field" style="flex: 1">
            <div class="ev-label">备注</div>
            <a-textarea v-model:value="fuelForm.notes" :rows="2" placeholder="可选" />
          </div>
        </div>
      </div>
    </a-modal>

    <!-- 费用录入弹窗 -->
    <a-modal v-model:open="expenseModalOpen" :title="editingExpense ? '编辑费用记录' : '添加费用记录'" @ok="saveExpense" width="500px">
      <a-form :model="expenseForm" layout="vertical">
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="日期时间" required>
              <a-date-picker v-model:value="expenseForm.expense_date" show-time style="width: 100%" valueFormat="YYYY-MM-DD HH:mm:ss" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="金额 (¥)"><a-input-number v-model:value="expenseForm.amount" :precision="2" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="费用类型">
              <a-select v-model:value="expenseForm.expense_type" show-search allow-clear>
                <a-select-option v-for="t in expenseTypes" :key="t" :value="t">{{ t }}</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="当时里程 (km)"><a-input-number v-model:value="expenseForm.mileage_at" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="24">
            <a-form-item label="备注"><a-textarea v-model:value="expenseForm.notes" :rows="2" /></a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import dayjs from 'dayjs'
import { vehicleApi } from '@/api/index'

const route = useRoute()
const router = useRouter()
const vehicleId = ref(parseInt(route.query.vid) || 0)
const activeTab = ref('fuel')
const loading = ref(false)
const fuelRecords = ref([])
const expenseRecords = ref([])
const pagination = ref({ current: 1, pageSize: 20, total: 0 })
const stats = ref({})

// 当前车辆信息（用于判断电动/燃油）
const currentVehicle = ref(null)
const isElectric = computed(() => {
  const ft = currentVehicle.value?.fuel_type || ''
  return ft === '电动' || ft === '纯电'
})

const expenseTypes = ['车辆保养', '车辆保险', '车辆维修', '洗车打蜡', '维修保养', '内外车品', '停车费', '违章罚款', '过路费', '其他']

// 弹窗
const fuelModalOpen = ref(false)
const editingFuel = ref(null)
const fuelForm = ref({
  fuel_date: '', total_mileage: null,
  // 燃油车
  unit_price: null, fuel_amount: null, display_cost: null, actual_cost: null,
  fuel_grade: '95#', is_full: true, is_low_fuel: false, is_missed: false, fuel_consumption: null,
  // 电动车
  energy_kwh: null, electricity_price: null, electricity_consumption: null, charge_type: '快充',
  soc_start: null, soc_end: null,
  station_name: '', notes: ''
})

const lastMileage = ref(null)

const computedTrip = computed(() => {
  if (!fuelForm.value.total_mileage || !lastMileage.value) return null
  const diff = fuelForm.value.total_mileage - lastMileage.value
  return diff > 0 ? Math.round(diff * 10) / 10 : null
})

// ── 燃油车自动计算 ──────────────────────────
const autoFuelAmount = computed(() => fuelForm.value.unit_price > 0 && fuelForm.value.actual_cost > 0)
const autoFuelConsumption = computed(() => computedTrip.value > 0 && fuelForm.value.fuel_amount > 0 && fuelForm.value.is_full)

// ── 电动车自动计算 ──────────────────────────
const autoEnergyKwh = computed(() => fuelForm.value.electricity_price > 0 && fuelForm.value.actual_cost > 0)
const autoElecConsumption = computed(() => computedTrip.value > 0 && fuelForm.value.energy_kwh > 0)

const expenseModalOpen = ref(false)
const editingExpense = ref(null)
const expenseForm = ref({ expense_date: '', expense_type: '', amount: null, mileage_at: null, notes: '' })

// ── 表格列定义 ──────────────────────────────
const fuelColumns = [
  { title: '日期', key: 'fuel_date', dataIndex: 'fuel_date', width: 155, align: 'center', customCell: () => ({ style: { whiteSpace: 'nowrap' } }) },
  { title: '里程(km)', key: 'total_mileage', dataIndex: 'total_mileage', width: 95, align: 'center' },
  { title: '行程(km)', key: 'trip_mileage', dataIndex: 'trip_mileage', width: 95, align: 'center' },
  { title: '油号', key: 'fuel_grade', dataIndex: 'fuel_grade', width: 65, align: 'center' },
  { title: '单价(元/L)', key: 'unit_price', dataIndex: 'unit_price', width: 105, align: 'center' },
  { title: '加油量(L)', key: 'fuel_amount', dataIndex: 'fuel_amount', width: 100, align: 'center' },
  { title: '实付金额', key: 'actual_cost', dataIndex: 'actual_cost', width: 100, align: 'center' },
  { title: '油耗(L)', key: 'fuel_consumption', dataIndex: 'fuel_consumption', width: 95, align: 'center' },
  { title: '加满', key: 'is_full', dataIndex: 'is_full', width: 65, align: 'center' },
  { title: '加油站', key: 'station_name', dataIndex: 'station_name', ellipsis: true },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

const electricColumns = [
  { title: '日期', key: 'fuel_date', dataIndex: 'fuel_date', width: 155, align: 'center', customCell: () => ({ style: { whiteSpace: 'nowrap' } }) },
  { title: '里程(km)', key: 'total_mileage', dataIndex: 'total_mileage', width: 95, align: 'center' },
  { title: '行程(km)', key: 'trip_mileage', dataIndex: 'trip_mileage', width: 95, align: 'center' },
  { title: '充电方式', key: 'charge_type', dataIndex: 'charge_type', width: 80, align: 'center' },
  { title: '电量', key: 'soc_range', width: 110, align: 'center' },
  { title: '电价', key: 'electricity_price', dataIndex: 'electricity_price', width: 90, align: 'center' },
  { title: '充电量', key: 'energy_kwh', dataIndex: 'energy_kwh', width: 95, align: 'center' },
  { title: '金额', key: 'actual_cost', dataIndex: 'actual_cost', width: 90, align: 'center' },
  { title: '电耗', key: 'electricity_consumption', dataIndex: 'electricity_consumption', width: 90, align: 'center', customCell: () => ({ style: { whiteSpace: 'nowrap' } }) },
  { title: '充电站', key: 'station_name', dataIndex: 'station_name', ellipsis: true },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

const currentFuelColumns = computed(() => isElectric.value ? electricColumns : fuelColumns)

const expenseColumns = [
  { title: '日期', key: 'expense_date', dataIndex: 'expense_date', width: 160, align: 'center', customCell: () => ({ style: { whiteSpace: 'nowrap' } }) },
  { title: '类型', key: 'expense_type', dataIndex: 'expense_type', width: 120, align: 'center' },
  { title: '金额', key: 'amount', dataIndex: 'amount', width: 110, align: 'center' },
  { title: '里程(km)', key: 'mileage_at', dataIndex: 'mileage_at', width: 100, align: 'center' },
  { title: '备注', key: 'notes', dataIndex: 'notes', ellipsis: true },
  { title: '操作', key: 'action', width: 120, fixed: 'right' },
]

function chargeTypeColor(type) {
  if (type === '快充') return 'orange'
  if (type === '慢充') return 'blue'
  if (type === '家充') return 'green'
  return 'default'
}

onMounted(async () => {
  if (vehicleId.value) {
    // 先加载车辆信息，判断类型
    try {
      const { data: vehicles } = await vehicleApi.list()
      currentVehicle.value = vehicles.find(v => v.id === vehicleId.value) || null
    } catch (e) { /* ignore */ }
    loadData()
  }
})

async function loadData() {
  if (!vehicleId.value) return
  loading.value = true
  try {
    const [{ data: s }, { data: f }, { data: e }] = await Promise.all([
      vehicleApi.getStats(vehicleId.value),
      vehicleApi.listFuel(vehicleId.value, 1, 9999),
      vehicleApi.listExpense(vehicleId.value, 1, 9999),
    ])
    stats.value = s
    fuelRecords.value = f.items || []
    expenseRecords.value = e.items || []
  } catch (err) { message.error('加载失败') }
  finally { loading.value = false }
}

function onPageChange(pag) { pagination.value.current = pag.current; loadData() }

function showAddModal() {
  if (activeTab.value === 'fuel') {
    editingFuel.value = null
    lastMileage.value = null
    if (fuelRecords.value.length > 0) {
      const latestMileage = fuelRecords.value.find(r => r.total_mileage != null)
      if (latestMileage) lastMileage.value = latestMileage.total_mileage
    }
    fuelForm.value = {
      fuel_date: dayjs().format('YYYY-MM-DD HH:mm:ss'),
      total_mileage: null,
      unit_price: null, fuel_amount: null, display_cost: null, actual_cost: null,
      fuel_grade: '95#', is_full: true, is_low_fuel: false, is_missed: false, fuel_consumption: null,
      energy_kwh: null, electricity_price: null, electricity_consumption: null, charge_type: '快充',
      soc_start: null, soc_end: null,
      station_name: '', notes: ''
    }
    fuelModalOpen.value = true
  } else {
    editingExpense.value = null
    expenseForm.value = { expense_date: dayjs().format('YYYY-MM-DD HH:mm:ss'), expense_type: '', amount: null, mileage_at: null, notes: '' }
    expenseModalOpen.value = true
  }
}

function showEditFuel(r) {
  editingFuel.value = r
  lastMileage.value = null
  const idx = fuelRecords.value.findIndex(rec => rec.id === r.id)
  if (idx < fuelRecords.value.length - 1) {
    const prev = fuelRecords.value[idx + 1]
    if (prev && prev.total_mileage != null) lastMileage.value = prev.total_mileage
  }
  fuelForm.value = {
    ...fuelForm.value, // 保留默认值结构
    ...r,
    charge_type: r.charge_type || '快充',
  }
  fuelModalOpen.value = true
}

// ── 燃油车计算逻辑 ──────────────────────────
function onPriceOrCostChange() {
  const price = fuelForm.value.unit_price
  const cost = fuelForm.value.actual_cost
  if (price > 0 && cost > 0) {
    fuelForm.value.fuel_amount = Math.round(cost / price * 100) / 100
  }
  recalcFuelConsumption()
}

function onFuelAmountChange() {
  const price = fuelForm.value.unit_price
  const amount = fuelForm.value.fuel_amount
  if (price > 0 && amount > 0) {
    fuelForm.value.actual_cost = Math.round(price * amount * 100) / 100
  }
  recalcFuelConsumption()
}

function onMileageChange() {
  if (isElectric.value) {
    recalcElecConsumption()
  } else {
    recalcFuelConsumption()
  }
}

function recalcFuelConsumption() {
  const trip = computedTrip.value
  const amount = fuelForm.value.fuel_amount
  if (trip > 0 && amount > 0 && fuelForm.value.is_full) {
    fuelForm.value.fuel_consumption = Math.round(amount / trip * 100 * 100) / 100
  }
}

// ── 电动车计算逻辑 ──────────────────────────
function onElecPriceOrCostChange() {
  const price = fuelForm.value.electricity_price
  const cost = fuelForm.value.actual_cost
  if (price > 0 && cost > 0) {
    fuelForm.value.energy_kwh = Math.round(cost / price * 100) / 100
  }
  recalcElecConsumption()
}

function onEnergyKwhChange() {
  const price = fuelForm.value.electricity_price
  const kwh = fuelForm.value.energy_kwh
  if (price > 0 && kwh > 0) {
    fuelForm.value.actual_cost = Math.round(price * kwh * 100) / 100
  }
  recalcElecConsumption()
}

function recalcElecConsumption() {
  const trip = computedTrip.value
  const kwh = fuelForm.value.energy_kwh
  if (trip > 0 && kwh > 0) {
    fuelForm.value.electricity_consumption = Math.round(kwh / trip * 100 * 100) / 100
  }
}

function showEditExpense(r) {
  editingExpense.value = r
  expenseForm.value = { ...r }
  expenseModalOpen.value = true
}

watch(() => fuelForm.value.is_full, () => recalcFuelConsumption())

async function saveFuel() {
  if (!fuelForm.value.fuel_date) { message.warning('请选择日期'); return }
  if (isElectric.value) {
    if (!fuelForm.value.total_mileage) { message.warning('请填写当前里程'); return }
    if (!fuelForm.value.energy_kwh && !fuelForm.value.actual_cost) {
      message.warning('请填写充电量或实付金额'); return
    }
  }
  try {
    if (editingFuel.value) {
      await vehicleApi.updateFuel(editingFuel.value.id, fuelForm.value)
    } else {
      await vehicleApi.createFuel({ vehicle_id: vehicleId.value, ...fuelForm.value })
    }
    message.success('保存成功'); fuelModalOpen.value = false; loadData()
  } catch (e) { message.error('保存失败') }
}

async function saveExpense() {
  if (!expenseForm.value.expense_date) { message.warning('请选择日期'); return }
  try {
    if (editingExpense.value) {
      await vehicleApi.updateExpense(editingExpense.value.id, expenseForm.value)
    } else {
      await vehicleApi.createExpense({ vehicle_id: vehicleId.value, ...expenseForm.value })
    }
    message.success('保存成功'); expenseModalOpen.value = false; loadData()
  } catch (e) { message.error('保存失败') }
}

async function deleteFuel(id) { await vehicleApi.deleteFuel(id); message.success('已删除'); loadData() }
async function deleteExpense(id) { await vehicleApi.deleteExpense(id); message.success('已删除'); loadData() }

async function handleImport(file) {
  try {
    const { data } = await vehicleApi.importXlsx(vehicleId.value, file)
    message.success(data.message)
    loadData()
  } catch (e) {
    message.error(e.response?.data?.detail || '导入失败')
  }
  return false
}

async function handleExport() {
  try {
    const { data: blob } = await vehicleApi.exportXlsx(vehicleId.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `车辆记录_${vehicleId.value}.xlsx`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch {
    // 401 等错误由 axios 拦截器处理
  }
}
</script>

<style scoped>
.stat-card { border-radius: 12px; padding: 16px; color: #fff; }
.stat-label { font-size: 12px; opacity: .85; margin-bottom: 6px; }
.stat-val { font-size: 24px; font-weight: 800; }
.stat-unit { font-size: 11px; opacity: .7; margin-top: 4px; }
.filter-bar { display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }

/* ── 电动车弹窗样式 ── */
.ev-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.ev-row {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.ev-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ev-label {
  font-size: 13px;
  color: #555;
  font-weight: 500;
}
.ev-hint {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}
.ev-divider {
  font-size: 12px;
  color: #aaa;
  border-top: 1px solid #f0f0f0;
  padding-top: 8px;
  margin-top: 4px;
  letter-spacing: 1px;
}

/* SOC 进度条 */
.soc-bar-wrap {
  padding: 0 4px;
}
.soc-bar {
  height: 8px;
  background: #f0f0f0;
  border-radius: 4px;
  position: relative;
  overflow: hidden;
}
.soc-bar-fill {
  position: absolute;
  top: 0;
  height: 100%;
  background: linear-gradient(90deg, #059669, #34d399);
  border-radius: 4px;
  transition: width 0.3s, margin-left 0.3s;
}
.soc-bar-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #999;
  margin-top: 4px;
}
</style>
