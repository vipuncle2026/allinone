<template>
  <div class="fund-page">
    <!-- 涨跌排行 -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="12">
        <a-card size="small" title="📈 今日估值涨幅榜">
          <a-list :data-source="rankUp" size="small" :loading="loading">
            <template #renderItem="{ item, index }">
              <a-list-item class="rank-item" @click="showDetail(item)">
                <a-list-item-meta>
                  <template #avatar>
                    <a-badge :count="index + 1"
                      :number-style="{
                        backgroundColor: index < 3 ? '#1a56db' : '#f0f0f0',
                        color: index < 3 ? '#fff' : '#666',
                        fontSize: '11px',
                        minWidth: '22px', height: '22px', borderRadius: '4px'
                      }" />
                  </template>
                  <template #title>
                    <span class="fund-name">{{ item.name }}</span>
                    <span class="fund-code">{{ item.code }}</span>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <span class="nav-val">{{ (item.est_nav || item.nav).toFixed(4) }}</span>
                  <a-tag :color="item.day_chg >= 0 ? 'red' : 'green'">
                    {{ item.day_chg >= 0 ? '+' : '' }}{{ item.day_chg.toFixed(2) }}%
                  </a-tag>
                </template>
              </a-list-item>
            </template>
            <template #empty><div style="padding: 20px; text-align: center; color: #999">请先添加自选基金</div></template>
          </a-list>
        </a-card>
      </a-col>
      <a-col :span="12">
        <a-card size="small" title="📉 今日估值跌幅榜">
          <a-list :data-source="rankDown" size="small" :loading="loading">
            <template #renderItem="{ item, index }">
              <a-list-item class="rank-item" @click="showDetail(item)">
                <a-list-item-meta>
                  <template #avatar>
                    <a-badge :count="index + 1"
                      :number-style="{
                        backgroundColor: index < 3 ? '#cf1322' : '#f0f0f0',
                        color: index < 3 ? '#fff' : '#666',
                        fontSize: '11px',
                        minWidth: '22px', height: '22px', borderRadius: '4px'
                      }" />
                  </template>
                  <template #title>
                    <span class="fund-name">{{ item.name }}</span>
                    <span class="fund-code">{{ item.code }}</span>
                  </template>
                </a-list-item-meta>
                <template #actions>
                  <span class="nav-val">{{ (item.est_nav || item.nav).toFixed(4) }}</span>
                  <a-tag :color="item.day_chg >= 0 ? 'red' : 'green'">
                    {{ item.day_chg >= 0 ? '+' : '' }}{{ item.day_chg.toFixed(2) }}%
                  </a-tag>
                </template>
              </a-list-item>
            </template>
            <template #empty><div style="padding: 20px; text-align: center; color: #999">请先添加自选基金</div></template>
          </a-list>
        </a-card>
      </a-col>
    </a-row>

    <!-- 自选列表 -->
    <a-card title="⭐ 我的自选" size="small">
      <template #extra>
        <a-space>
          <a-select v-model:value="currentGroup" style="width: 120px" size="small"
            @change="loadFunds">
            <a-select-option value="all">全部分组</a-select-option>
            <a-select-option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</a-select-option>
          </a-select>
          <a-button size="small" @click="refreshEstimates" :loading="refreshing">
            🔄 刷新估值
          </a-button>
          <a-button size="small" @click="showGroupManager">📁 分组管理</a-button>
        </a-space>
      </template>

      <!-- 添加栏 -->
      <div class="add-bar">
        <a-input-search
          v-model:value="addCode"
          placeholder="输入6位基金代码，如 110020"
          size="small"
          style="width: 260px"
          :maxlength="6"
          @search="searchToAdd"
          :loading="adding"
          @pressEnter="searchToAdd"
        >
          <template #enterButton>
            <a-button type="primary" size="small">+ 添加</a-button>
          </template>
        </a-input-search>
        <span v-if="funds.length" style="margin-left: 8px; font-size: 12px; color: #999">
          共 {{ funds.length }} 支
        </span>
      </div>

      <!-- 表格 -->
      <a-table
        :dataSource="funds"
        :columns="columns"
        :loading="loading"
        size="small"
        :pagination="{ pageSize: 25, showSizeChanger: false, showTotal: total => `共 ${total} 支` }"
        :scroll="{ x: 1000 }"
        row-key="code"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'name'">
            <a @click="showDetail(record)" style="color: #1a56db; font-weight: 600">
              {{ record.name }}
            </a>
            <a-tag v-if="record.shares > 0" color="blue" style="margin-left: 4px; font-size: 10px">持仓</a-tag>
          </template>
          <template v-if="column.key === 'type'">
            <a-select
              :value="record.type"
              size="small"
              style="width: 80px"
              :bordered="false"
              @change="(val) => changeType(record, val)"
            >
              <a-select-option v-for="t in fundTypes" :key="t">{{ t }}</a-select-option>
            </a-select>
          </template>
          <template v-if="column.key === 'cost_nav'">
            <span :style="{ fontSize: '12px', color: record.cost_nav ? '#f59e0b' : '#999' }">
              {{ record.cost_nav ? record.cost_nav.toFixed(4) : '-' }}
            </span>
          </template>
          <template v-if="column.key === 'day_chg'">
            <span v-if="record.day_chg || record.est_nav > 0">
              <span :style="{ color: record.day_chg >= 0 ? '#e63946' : '#16a34a', fontWeight: 700 }">
                {{ record.day_chg >= 0 ? '+' : '' }}{{ record.day_chg.toFixed(2) }}%
              </span>
              <div style="font-size: 11px; color: #999">{{ record.est_nav ? record.est_nav.toFixed(4) : '--' }}</div>
            </span>
            <span v-else style="color: #999; font-size: 12px">暂无估算</span>
          </template>
          <template v-if="column.key === 'actions'">
            <a-space :size="4">
              <a-button size="small" @click="openHoldingEdit(record)">
                {{ record.shares > 0 ? '📊 持仓' : '设置持仓' }}
              </a-button>
              <a-select size="small" :value="record.group_id" style="width: 90px"
                @change="(val) => changeGroup(record.code, val)">
                <a-select-option v-for="g in groups" :key="g.id" :value="g.id">{{ g.name }}</a-select-option>
              </a-select>
              <a-popconfirm title="确定移出自选？" @confirm="removeFund(record.code)">
                <a-button size="small" danger>移出</a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
        <template #emptyText>
          <div style="padding: 30px; text-align: center; color: #999">
            <div style="font-size: 24px; margin-bottom: 8px">⭐</div>
            <div>暂无自选基金</div>
            <div style="font-size: 12px; color: #bbb; margin-top: 4px">输入基金代码点击添加</div>
          </div>
        </template>
      </a-table>
    </a-card>

    <!-- 添加基金确认弹窗 -->
    <a-modal v-model:open="addModalOpen" title="添加自选基金" @ok="confirmAdd" width="480px" :confirmLoading="adding">
      <template #footer>
        <a-button @click="addModalOpen = false">取消</a-button>
        <a-button type="primary" @click="confirmAdd">确认添加</a-button>
      </template>
      <div v-if="addPreview" style="margin-bottom: 16px">
        <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 16px; padding: 12px; background: #f0f5ff; border-radius: 8px">
          <div style="font-size: 20px; font-weight: 700; color: #1a56db">{{ addPreview.est_nav ? addPreview.est_nav.toFixed(4) : '--' }}</div>
          <div>
            <div style="font-size: 15px; font-weight: 600">{{ addPreview.name }}</div>
            <div style="font-size: 12px; color: #999">
              {{ addPreview.code }} · {{ addPreview.type || '未知' }}
              <span v-if="addPreview.day_chg" :style="{ color: addPreview.day_chg >= 0 ? '#e63946' : '#16a34a', marginLeft: '6px', fontWeight: 600 }">
                {{ addPreview.day_chg >= 0 ? '+' : '' }}{{ addPreview.day_chg.toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>
      </div>
      <a-divider style="margin: 12px 0">持仓信息（可选）</a-divider>
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="持仓份额（份）">
            <a-input-number v-model:value="addShares" :min="0" :step="100" placeholder="如 6468.31" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="成本净值（元）">
            <a-input-number v-model:value="addCostNav" :min="0" :step="0.01" :precision="4" placeholder="如 1.0234" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <div v-if="addShares > 0 && addCostNav > 0" style="background: #f9fafb; border-radius: 8px; padding: 12px; font-size: 13px; color: #666">
        预估持仓成本：<strong style="color: #f59e0b">¥{{ (addShares * addCostNav).toFixed(2) }}</strong>
      </div>
    </a-modal>

    <!-- 持仓编辑弹窗 -->
    <a-modal v-model:open="holdingModalOpen" :title="holdingFund?.name" @ok="saveHolding" width="420px">
      <template #footer>
        <a-button @click="holdingModalOpen = false">取消</a-button>
        <a-button type="primary" @click="saveHolding">保存持仓</a-button>
      </template>
      <div v-if="holdingFund" style="margin-bottom: 16px; font-size: 12px; color: #999">
        {{ holdingFund.code }} · {{ holdingFund.type }}
      </div>
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="持仓份额（份）">
            <a-input-number v-model:value="holdingShares" :min="0" :step="100" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="成本净值（元）">
            <a-input-number v-model:value="holdingCostNav" :min="0" :step="0.01" :precision="4" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>
      <div v-if="holdingFund" style="background: #f9fafb; border-radius: 8px; padding: 12px; font-size: 13px; color: #666">
        当前估算净值：<strong style="color: #333">{{ (holdingFund.est_nav || holdingFund.nav || 0).toFixed(4) }}</strong>
        &nbsp;|&nbsp;
        今日估算：
        <strong :style="{ color: (holdingFund.day_chg || 0) >= 0 ? '#e63946' : '#16a34a' }">
          {{ holdingFund.day_chg ? (holdingFund.day_chg >= 0 ? '+' : '') + holdingFund.day_chg.toFixed(2) + '%' : '--' }}
        </strong>
      </div>
    </a-modal>

    <!-- 基金详情弹窗（三标签页） -->
    <a-modal v-model:open="detailModalOpen" :footer="null" width="700px" :destroyOnClose="true"
      @cancel="detailTab = 'trend'">
      <template #title>
        <div style="display: flex; align-items: center; gap: 8px">
          <span style="font-size: 16px; font-weight: 700">{{ detailFund?.name }}</span>
          <a-tag size="small" color="blue">{{ detailFund?.code }}</a-tag>
        </div>
      </template>
      <template v-if="detailFund">
        <!-- 顶部指标 -->
        <a-row :gutter="12" style="margin-bottom: 16px">
          <a-col :span="8" style="text-align: center; background: var(--blue-100); border-radius: 8px; padding: 12px">
            <div style="font-size: 11px; color: #999; margin-bottom: 4px">最新净值</div>
            <div style="font-size: 22px; font-weight: 800">{{ (detailFund.nav || 0).toFixed(4) }}</div>
            <div style="font-size: 11px; color: #999; margin-top: 2px">{{ detailFund.nav_date || '--' }}</div>
          </a-col>
          <a-col :span="8" style="text-align: center; background: var(--blue-100); border-radius: 8px; padding: 12px">
            <div style="font-size: 11px; color: #999; margin-bottom: 4px">估算净值</div>
            <div style="font-size: 22px; font-weight: 800">{{ (detailFund.est_nav || '--') }}</div>
            <div style="font-size: 11px; color: #999; margin-top: 2px">{{ detailFund.val_time || '--' }}</div>
          </a-col>
          <a-col :span="8" style="text-align: center; border-radius: 8px; padding: 12px"
            :style="{ background: (detailFund.day_chg || 0) >= 0 ? '#fef2f2' : '#f0fdf4' }">
            <div style="font-size: 11px; color: #999; margin-bottom: 4px">今日估算</div>
            <div style="font-size: 22px; font-weight: 800"
              :style="{ color: (detailFund.day_chg || 0) >= 0 ? '#e63946' : '#16a34a' }">
              {{ detailFund.day_chg ? (detailFund.day_chg >= 0 ? '+' : '') + detailFund.day_chg.toFixed(2) + '%' : '--' }}
            </div>
          </a-col>
        </a-row>

        <!-- 三标签页 -->
        <a-tabs v-model:activeKey="detailTab">
          <!-- Tab 1: 近30天净值 -->
          <a-tab-pane key="nav" tab="📊 近30天净值">
            <div v-if="detailLoading" style="text-align: center; padding: 40px; color: #999">加载中...</div>
            <div v-else-if="detailData.nav_history?.length">
              <div style="height: 220px; margin-bottom: 12px"><canvas ref="navChartRef"></canvas></div>
              <a-table :columns="navColumns" :data-source="detailData.nav_history" :pagination="false" size="small" row-key="date"
                :scroll="{ y: 200 }">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'nav'">
                    <span style="font-weight: 600">{{ record.nav.toFixed(4) }}</span>
                  </template>
                  <template v-if="column.key === 'chg'">
                    <span :style="{ color: record.chg >= 0 ? '#e63946' : '#16a34a', fontWeight: 600 }">
                      {{ record.chg >= 0 ? '+' : '' }}{{ record.chg.toFixed(2) }}%
                    </span>
                  </template>
                </template>
              </a-table>
            </div>
            <div v-else style="text-align: center; padding: 40px; color: #ccc">暂无净值数据</div>
          </a-tab-pane>

          <!-- Tab 2: 持仓明细 -->
          <a-tab-pane key="holdings" tab="📋 持仓明细">
            <div v-if="detailLoading" style="text-align: center; padding: 40px; color: #999">加载中...</div>
            <div v-else-if="detailData.holdings?.length">
              <a-table :columns="holdingColumns" :data-source="detailData.holdings" :pagination="false" size="small" row-key="stock_code">
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'stock_name'">
                    <span style="font-weight: 600">{{ record.stock_name }}</span>
                    <span style="color: #999; margin-left: 4px; font-size: 12px">{{ record.stock_code }}</span>
                  </template>
                  <template v-if="column.key === 'ratio'">
                    <a-progress :percent="record.ratio" :showInfo="true" :strokeColor="'#4F5DFE'"
                      :trailColor="'#e5e7eb'" size="small" />
                  </template>
                </template>
              </a-table>
              <div style="margin-top: 8px; font-size: 12px; color: #999">
                数据来源：天天基金（最新季度报告）
              </div>
            </div>
            <div v-else style="text-align: center; padding: 40px; color: #ccc">暂无持仓数据</div>
          </a-tab-pane>

          <!-- Tab 3: 基本信息 -->
          <a-tab-pane key="info" tab="ℹ️ 基本信息">
            <a-row :gutter="12" v-if="detailFund.shares > 0" style="margin-bottom: 16px">
              <a-col :span="6" style="text-align: center; background: #eff6ff; border-radius: 8px; padding: 12px">
                <div style="font-size: 11px; color: #666; margin-bottom: 2px">持仓份额</div>
                <div style="font-size: 16px; font-weight: 700">{{ detailFund.shares }}</div>
              </a-col>
              <a-col :span="6" style="text-align: center; background: #fef3c7; border-radius: 8px; padding: 12px">
                <div style="font-size: 11px; color: #666; margin-bottom: 2px">成本净值</div>
                <div style="font-size: 16px; font-weight: 700">{{ (detailFund.cost_nav || 0).toFixed(4) }}</div>
              </a-col>
              <a-col :span="6" style="text-align: center; background: #f0fdf4; border-radius: 8px; padding: 12px">
                <div style="font-size: 11px; color: #666; margin-bottom: 2px">持仓市值</div>
                <div style="font-size: 16px; font-weight: 700">¥{{ (detailFund.shares * (detailFund.est_nav || detailFund.nav || 0)).toFixed(2) }}</div>
              </a-col>
              <a-col :span="6" style="text-align: center; border-radius: 8px; padding: 12px"
                :style="{ background: detailFund.cost_nav > 0 ? (detailFund.est_nav || detailFund.nav) >= detailFund.cost_nav ? '#fef2f2' : '#f0fdf4' : '#f9fafb' }">
                <div style="font-size: 11px; color: #666; margin-bottom: 2px">持仓收益</div>
                <div v-if="detailFund.cost_nav > 0" style="font-size: 16px; font-weight: 700"
                  :style="{ color: (detailFund.est_nav || detailFund.nav) >= detailFund.cost_nav ? '#e63946' : '#16a34a' }">
                  {{ (((detailFund.est_nav || detailFund.nav) - detailFund.cost_nav) * detailFund.shares).toFixed(2) }}
                </div>
                <div v-else style="font-size: 14px; color: #999">--</div>
              </a-col>
            </a-row>
            <a-row :gutter="8" style="margin-bottom: 16px">
              <a-col :span="6" v-for="item in retItems" :key="item.key" style="text-align: center; padding: 8px; border-radius: 6px; background: #f9fafb">
                <div style="font-size: 11px; color: #999; margin-bottom: 2px">{{ item.label }}</div>
                <div style="font-size: 14px; font-weight: 600"
                  :style="{ color: detailFund[item.key] >= 0 ? '#e63946' : '#16a34a' }">
                  {{ detailFund[item.key] ? (detailFund[item.key] >= 0 ? '+' : '') + detailFund[item.key].toFixed(2) + '%' : '--' }}
                </div>
              </a-col>
            </a-row>
            <a-descriptions :column="2" size="small" bordered>
              <a-descriptions-item label="基金经理">{{ detailFund.manager }}</a-descriptions-item>
              <a-descriptions-item label="基金公司">{{ detailFund.company }}</a-descriptions-item>
              <a-descriptions-item label="基金规模">{{ detailFund.scale ? detailFund.scale.toFixed(1) + '亿' : '--' }}</a-descriptions-item>
              <a-descriptions-item label="分组">{{ getGroupName(detailFund.group_id) }}</a-descriptions-item>
              <a-descriptions-item label="类型">{{ detailFund.type }}</a-descriptions-item>
              <a-descriptions-item label="ETF">{{ detailFund.is_etf ? '是' : '否' }}</a-descriptions-item>
              <a-descriptions-item label="添加时间">{{ detailFund.created_at?.slice(0, 10) || '--' }}</a-descriptions-item>
            </a-descriptions>
          </a-tab-pane>
        </a-tabs>
      </template>
    </a-modal>

    <!-- 分组管理弹窗 -->
    <a-modal v-model:open="groupModalOpen" title="📁 分组管理" :footer="null" width="480px" @cancel="cancelEditGroup">
      <a-list :data-source="groups" size="small">
        <template #renderItem="{ item }">
          <a-list-item>
            <template #avatar>
              <!-- 编辑态：颜色选择 -->
              <div v-if="editingGroupId === item.id" class="edit-color-row">
                <span v-for="c in groupColors" :key="c" class="color-dot"
                  :class="{ selected: editingColor === c }" :style="{ backgroundColor: c }"
                  @click="editingColor = c" />
              </div>
              <!-- 展示态：颜色圆点 -->
              <span v-else style="width: 14px; height: 14px; border-radius: 50%; display: inline-block; margin-top: 6px"
                :style="{ backgroundColor: item.color }" />
            </template>
            <a-list-item-meta>
              <template #title>
                <!-- 编辑态：输入框 -->
                <a-input v-if="editingGroupId === item.id"
                  v-model:value="editingName" size="small" :maxlength="10"
                  style="width: 140px" @pressEnter="saveEditGroup(item)"
                  @keydown.esc="cancelEditGroup" />
                <!-- 展示态：名称 -->
                <span v-else>{{ item.name }}</span>
              </template>
              <template #description>
                <span v-if="editingGroupId === item.id" style="color: #6366f1; font-size: 12px">
                  {{ item.count }} 只基金 · 按 Enter 保存，Esc 取消
                </span>
                <span v-else>{{ item.count }} 只基金</span>
              </template>
            </a-list-item-meta>
            <template #actions>
              <!-- 编辑态：保存 / 取消 -->
              <template v-if="editingGroupId === item.id">
                <a-button size="small" type="link" @click="saveEditGroup(item)">✅</a-button>
                <a-button size="small" type="link" @click="cancelEditGroup">❌</a-button>
              </template>
              <!-- 展示态：编辑 / 删除 -->
              <template v-else>
                <a-button v-if="!item.is_default" size="small" type="link" @click="startEditGroup(item)">✏️</a-button>
                <a-popconfirm v-if="!item.is_default"
                  :title="item.count > 0 ? `删除后 ${item.count} 只基金将移至默认分组` : '确定删除？'"
                  @confirm="deleteGroup(item.id)">
                  <a-button size="small" type="link" danger>🗑️</a-button>
                </a-popconfirm>
              </template>
            </template>
          </a-list-item>
        </template>
      </a-list>
      <a-divider style="margin: 12px 0" />
      <a-space>
        <a-input v-model:value="newGroupName" placeholder="新分组名称" size="small" style="width: 150px" :maxlength="10" />
        <div v-for="c in groupColors" :key="c" class="color-dot"
          :class="{ selected: newGroupColor === c }" :style="{ backgroundColor: c }"
          @click="newGroupColor = c" />
        <a-button type="primary" size="small" @click="addGroup">添加</a-button>
      </a-space>
    </a-modal>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, nextTick, onBeforeUnmount, watch } from 'vue'
import { message } from 'ant-design-vue'
import { fundApi } from '@/api'
import Chart from 'chart.js/auto'

const funds = ref([])
const groups = ref([])
const loading = ref(false)
const refreshing = ref(false)
// 添加基金
const adding = ref(false)
const addCode = ref('')
const addModalOpen = ref(false)
const addPreview = ref(null)
const addShares = ref(0)
const addCostNav = ref(0)

async function searchToAdd() {
  const code = addCode.value.trim().replace(/\D/g, '').padStart(6, '0')
  if (!code || code.length !== 6) {
    message.warning('请输入6位基金代码')
    return
  }
  adding.value = true
  try {
    const res = await fundApi.search(code)
    addPreview.value = res.data
    addShares.value = 0
    addCostNav.value = 0
    addModalOpen.value = true
  } catch (e) {
    message.error(e.response?.data?.detail || '查询失败，请确认基金代码')
  } finally {
    adding.value = false
  }
}

async function confirmAdd() {
  if (!addPreview.value) return
  adding.value = true
  try {
    await fundApi.add(
      addPreview.value.code,
      currentGroup.value === 'all' ? 'default' : currentGroup.value,
      addShares.value,
      addCostNav.value
    )
    addModalOpen.value = false
    addCode.value = ''
    message.success(`已添加：${addPreview.value.name}`)
    await loadFunds()
  } catch (e) {
    message.error(e.response?.data?.detail || '添加失败')
  } finally {
    adding.value = false
  }
}
const currentGroup = ref('all')

// 持仓编辑
const holdingModalOpen = ref(false)
const holdingFund = ref(null)
const holdingShares = ref(0)
const holdingCostNav = ref(0)

// 基金详情（三标签页）
const detailModalOpen = ref(false)
const detailFund = ref(null)
const detailTab = ref('nav')
const detailData = ref({ holdings: [], nav_history: [], estimate_trend: [] })
const detailLoading = ref(false)
const navChartRef = ref(null)
let navChart = null

// 净值表格列
const navColumns = [
  { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
  { title: '单位净值', dataIndex: 'nav', key: 'nav', width: 110 },
  { title: '涨跌幅', key: 'chg', width: 100 },
]

// 持仓明细表格列
const holdingColumns = [
  { title: '股票名称', key: 'stock_name' },
  { title: '占净值比', key: 'ratio', width: 200 },
  { title: '持仓市值(万)', dataIndex: 'amount', key: 'amount', width: 130, align: 'right' },
]

async function showDetail(fund) {
  detailFund.value = fund
  detailTab.value = 'nav'
  detailData.value = { holdings: [], nav_history: [], estimate_trend: [] }
  detailModalOpen.value = true
  detailLoading.value = true
  try {
    const res = await fundApi.detail(fund.code)
    const d = res.data
    // 给净值历史添加涨跌幅
    if (d.nav_history && d.nav_history.length > 1) {
      for (let i = 0; i < d.nav_history.length; i++) {
        if (i === 0) {
          d.nav_history[i].chg = 0
        } else {
          const prev = d.nav_history[i - 1].nav
          d.nav_history[i].chg = prev > 0 ? ((d.nav_history[i].nav - prev) / prev * 100) : 0
        }
      }
    }
    detailData.value = d
    // 合并基本信息到 detailFund（用于基本信息 Tab 显示）
    if (d.basic_info) {
      Object.assign(detailFund.value, {
        manager: d.basic_info.manager || detailFund.value.manager,
        company: d.basic_info.company || detailFund.value.company,
        scale: d.basic_info.scale || detailFund.value.scale,
        type: d.basic_info.type !== '--' ? d.basic_info.type : detailFund.value.type,
      })
    }
    if (d.ret_fields) {
      Object.assign(detailFund.value, d.ret_fields)
    }
    // 等待 DOM 渲染后画图
    await nextTick()
    if (detailTab.value === 'nav') drawNavChart()
  } catch (e) {
    console.error('获取基金详情失败', e)
    message.warning('获取详情数据失败')
  } finally {
    detailLoading.value = false
  }
}

function drawNavChart() {
  const canvas = navChartRef.value
  if (!canvas) return
  if (navChart) { navChart.destroy(); navChart = null }
  const items = detailData.value.nav_history || []
  if (!items.length) return
  const last = items[items.length - 1]
  const first = items[0]
  const isUp = last.nav >= first.nav
  const color = isUp ? '#e63946' : '#16a34a'
  navChart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: items.map(i => i.date.slice(5)),
      datasets: [{
        data: items.map(i => i.nav),
        borderColor: color,
        backgroundColor: isUp ? 'rgba(230,57,70,0.08)' : 'rgba(22,163,74,0.08)',
        fill: true,
        tension: 0.3,
        pointRadius: 0,
        pointHoverRadius: 4,
        borderWidth: 2,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: { label: ctx => '净值: ' + ctx.parsed.y.toFixed(4) }
        }
      },
      scales: {
        x: { ticks: { maxTicksLimit: 8, font: { size: 10 } }, grid: { display: false } },
        y: { ticks: { font: { size: 10 }, callback: v => v.toFixed(4) }, grid: { color: '#f0f0f0' } }
      }
    }
  })
}

// 切换标签页时画图
watch(detailTab, async (val) => {
  if (val === 'nav') {
    await nextTick()
    drawNavChart()
  }
})

// 清理 chart
onBeforeUnmount(() => { if (navChart) { navChart.destroy(); navChart = null } })

// 分组管理
const groupModalOpen = ref(false)
const newGroupName = ref('')
const newGroupColor = ref('#6b7280')
const groupColors = ['#6b7280', '#1a56db', '#16a34a', '#f59e0b', '#e63946', '#7c3aed', '#0891b2', '#ec4899']

// 行内编辑分组
const editingGroupId = ref(null)
const editingName = ref('')
const editingColor = ref('')

const fundTypes = ['股票型', '混合型', '债券型', '指数型', '商品型', '跨境型', '货币型', 'QDII', 'ETF', 'LOF']

const retItems = [
  { key: 'ret_1m', label: '近1月' },
  { key: 'ret_3m', label: '近3月' },
  { key: 'ret_6m', label: '近6月' },
  { key: 'ret_1y', label: '近1年' },
]

const rankUp = computed(() =>
  [...funds.value].filter(f => f.day_chg).sort((a, b) => b.day_chg - a.day_chg).slice(0, 8)
)
const rankDown = computed(() =>
  [...funds.value].filter(f => f.day_chg).sort((a, b) => a.day_chg - b.day_chg).slice(0, 8)
)

const columns = [
  { title: '基金名称', key: 'name', width: 180 },
  { title: '代码', dataIndex: 'code', key: 'code', width: 80 },
  { title: '类型', key: 'type', width: 80 },
  { title: '成本净值', dataIndex: 'cost_nav', key: 'cost_nav', width: 100, customRender: ({ text }) => text ? text.toFixed(4) : '-' },
  { title: '单位净值', dataIndex: 'nav', key: 'nav', width: 100, customRender: ({ text }) => (text || 0).toFixed(4) },
  { title: '今日估算', key: 'day_chg', width: 100 },
  { title: '估值时间', dataIndex: 'val_time', key: 'val_time', width: 140, ellipsis: true },
  { title: '操作', key: 'actions', width: 260, fixed: 'right' },
]

function typeColor(type) {
  const map = { '股票型': 'blue', '混合型': 'gold', '债券型': 'green', '指数型': 'purple', '商品型': 'pink', '跨境型': 'cyan' }
  return map[type] || 'default'
}

function getGroupColor(groupId) {
  const g = groups.value.find(g => g.id === groupId)
  return g ? g.color : '#6b7280'
}
function getGroupName(groupId) {
  const g = groups.value.find(g => g.id === groupId)
  return g ? g.name : '默认分组'
}

async function loadFunds() {
  loading.value = true
  try {
    const [res, gRes] = await Promise.all([
      fundApi.list(currentGroup.value),
      fundApi.listGroups(),
    ])
    funds.value = res.data
    groups.value = gRes.data
  } catch (e) {
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function refreshEstimates() {
  refreshing.value = true
  try {
    const res = await fundApi.refresh()
    message.success(res.data.message)
    await loadFunds()
  } catch (e) {
    message.error('刷新失败')
  } finally {
    refreshing.value = false
  }
}

async function removeFund(code) {
  try {
    await fundApi.remove(code)
    message.success('已移出自选')
    await loadFunds()
  } catch (e) {
    message.error('移除失败')
  }
}

async function changeGroup(code, groupId) {
  try {
    await fundApi.changeGroup(code, groupId)
    const groupName = getGroupName(groupId)
    message.success(`已移至"${groupName}"`)
    await loadFunds()
  } catch (e) {
    message.error('修改分组失败')
  }
}

async function changeType(fund, newType) {
  try {
    await fundApi.updateHolding(fund.code, fund.shares, fund.cost_nav, newType)
    fund.type = newType
    message.success(`已改为"${newType}"`)
  } catch (e) {
    message.error('修改类型失败')
  }
}

function openHoldingEdit(fund) {
  holdingFund.value = fund
  holdingShares.value = fund.shares || 0
  holdingCostNav.value = fund.cost_nav || 0
  holdingModalOpen.value = true
}

async function saveHolding() {
  try {
    await fundApi.updateHolding(holdingFund.value.code, holdingShares.value, holdingCostNav.value)
    holdingModalOpen.value = false
    message.success('持仓已保存')
    await loadFunds()
  } catch (e) {
    message.error('保存失败')
  }
}

function showGroupManager() {
  groupModalOpen.value = true
}

async function addGroup() {
  if (!newGroupName.value.trim()) { message.warning('请输入分组名称'); return }
  try {
    await fundApi.createGroup(newGroupName.value.trim(), newGroupColor)
    newGroupName.value = ''
    newGroupColor.value = '#6b7280'
    message.success('分组已添加')
    await loadGroups()
  } catch (e) {
    message.error(e.response?.data?.detail || '添加失败')
  }
}

function startEditGroup(group) {
  editingGroupId.value = group.id
  editingName.value = group.name
  editingColor.value = group.color || '#6b7280'
}

function cancelEditGroup() {
  editingGroupId.value = null
  editingName.value = ''
  editingColor.value = ''
}

async function saveEditGroup(group) {
  const name = editingName.value.trim()
  if (!name) { message.warning('分组名称不能为空'); return }
  if (name === group.name && editingColor.value === group.color) {
    cancelEditGroup()
    return
  }
  try {
    await fundApi.updateGroup(group.id, name, editingColor.value)
    message.success('分组已更新')
    editingGroupId.value = null
    await loadGroups()
    await loadFunds()
  } catch (e) {
    message.error(e.response?.data?.detail || '更新失败')
  }
}

async function deleteGroup(groupId) {
  try {
    await fundApi.deleteGroup(groupId)
    message.success('分组已删除')
    if (currentGroup.value === groupId) currentGroup.value = 'all'
    await loadGroups()
    await loadFunds()
  } catch (e) {
    message.error('删除失败')
  }
}

async function loadGroups() {
  try {
    const res = await fundApi.listGroups()
    groups.value = res.data
  } catch (e) {}
}

onMounted(() => {
  loadFunds()
})
</script>

<style scoped>
.fund-page { max-width: 1400px; }
.add-bar { padding: 10px 0; display: flex; align-items: center; }
.rank-item { cursor: pointer; }
.fund-name { font-weight: 600; font-size: 13px; }
.fund-code { font-size: 11px; color: #999; margin-left: 6px; }
.nav-val { font-weight: 600; font-size: 13px; margin-right: 8px; }
.color-dot {
  width: 20px; height: 20px; border-radius: 50%;
  cursor: pointer; border: 2px solid transparent;
  display: inline-block; transition: all 0.15s;
}
.color-dot:hover { transform: scale(1.15); }
.color-dot.selected { border-color: #1a56db; }
.edit-color-row {
  display: flex; gap: 4px; flex-wrap: wrap; margin-top: 4px;
  max-width: 180px;
}
.edit-color-row .color-dot {
  width: 16px; height: 16px;
}
</style>
