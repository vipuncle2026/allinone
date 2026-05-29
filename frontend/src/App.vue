<template>
  <a-config-provider :locale="zhCN">
    <!-- 登录页：独立布局 -->
    <router-view v-if="route.name === 'login'" />
    <!-- 主应用布局 -->
    <a-layout v-else style="height: 100vh; overflow: hidden; display: flex; flex-direction: row">
      <!-- 移动端遮罩 -->
      <div v-if="isMobile && !collapsed" class="mobile-overlay" @click="collapsed = true"></div>
      <!-- 侧边栏 -->
      <a-layout-sider
        v-model:collapsed="collapsed"
        collapsible
        :width="230"
        :trigger="null"
        theme="dark"
        class="sidebar"
        :class="{ 'sidebar-mobile': isMobile, 'sidebar-mobile-open': isMobile && !collapsed }"
      >
        <div class="logo">
          <div class="logo-icon">AIO</div>
          <span v-if="!collapsed" class="logo-text">All-in-One</span>
          <template v-if="!collapsed">
            <a-tooltip title="展开全部">
              <a-button type="text" size="small" class="logo-action-btn" @click="expandAll">
                <MenuUnfoldOutlined />
              </a-button>
            </a-tooltip>
            <a-tooltip title="收起全部">
              <a-button type="text" size="small" class="logo-action-btn" @click="collapseAll">
                <MenuFoldOutlined />
              </a-button>
            </a-tooltip>
          </template>
        </div>
        <a-menu
          v-model:selectedKeys="selectedKeys"
          v-model:openKeys="openKeys"
          theme="dark"
          mode="inline"
          class="sidebar-menu"
          @click="onMenuClick"
        >
          <a-menu-item key="dashboard">
            <template #icon><DashboardOutlined /></template>
            <span>看板</span>
          </a-menu-item>

          <a-sub-menu key="fund">
            <template #icon><FundOutlined /></template>
            <template #title>基金管理</template>
            <a-menu-item key="fund-list">自选基金</a-menu-item>
            <a-menu-item key="fund-holdings">持仓分析</a-menu-item>
            <a-menu-item key="fund-snapshot">持仓快照</a-menu-item>
          </a-sub-menu>

          <a-sub-menu key="finance">
            <template #icon><MoneyCollectOutlined /></template>
            <template #title>财务管理</template>
            <a-sub-menu key="finance-accounts">
              <template #title>账户管理</template>
              <a-menu-item key="finance-accounts-list">我的账户</a-menu-item>
              <a-menu-item key="finance-snapshots">快照记录</a-menu-item>
            </a-sub-menu>
            <a-menu-item key="finance-bills">账单导入</a-menu-item>
            <a-menu-item key="finance-records">收支记录</a-menu-item>
            <a-menu-item key="finance-category-rules">分类规则</a-menu-item>
            <a-menu-item key="finance-stats">统计分析</a-menu-item>
          </a-sub-menu>

          <!-- 运动管理 -->
          <a-sub-menu key="sports">
            <template #icon><FireOutlined /></template>
            <template #title>运动管理</template>
            <a-sub-menu key="cycling" title="骑行">
              <template #icon><EnvironmentOutlined /></template>
              <a-menu-item key="cycling-bikes">我的车辆</a-menu-item>
              <a-menu-item key="cycling-list">骑行记录</a-menu-item>
              <a-menu-item key="cycling-stats">统计分析</a-menu-item>
            </a-sub-menu>
            <a-sub-menu key="hiking" title="徒步">
              <template #icon><CompassOutlined /></template>
              <a-menu-item key="hiking-list">徒步记录</a-menu-item>
              <a-menu-item key="hiking-upload">导入活动</a-menu-item>
              <a-menu-item key="hiking-stats">统计分析</a-menu-item>
            </a-sub-menu>
            <a-sub-menu key="running" title="跑步">
              <template #icon><TrophyOutlined /></template>
              <a-menu-item key="running-list">跑步记录</a-menu-item>
              <a-menu-item key="running-upload">导入活动</a-menu-item>
              <a-menu-item key="running-stats">统计分析</a-menu-item>
            </a-sub-menu>

            <!-- 运动成就 -->
            <a-menu-item key="sports-achievements">
              <template #icon><TrophyOutlined /></template>
              <span>运动成就</span>
            </a-menu-item>
          </a-sub-menu>

          <a-sub-menu key="vehicle">
            <template #icon><CarOutlined /></template>
            <template #title>车辆管理</template>
            <a-menu-item key="vehicle-list">我的车辆</a-menu-item>
            <a-menu-item key="vehicle-stats">统计分析</a-menu-item>
          </a-sub-menu>

          <a-sub-menu key="travel">
            <template #icon><GlobalOutlined /></template>
            <template #title>旅行管理</template>
            <a-menu-item key="travel-home">旅行总览</a-menu-item>
            <a-menu-item key="travel-stats">统计分析</a-menu-item>
          </a-sub-menu>

          <a-sub-menu key="item">
            <template #icon><BoxPlotOutlined /></template>
            <template #title>物品管理</template>
            <a-menu-item key="item-list">物品清单</a-menu-item>
          </a-sub-menu>

          <a-menu-item key="backup-center">
            <template #icon><CloudServerOutlined /></template>
            <span>备份中心</span>
          </a-menu-item>
        </a-menu>
        <div v-if="!collapsed" class="sidebar-blank" @click="toggleAllMenus">
          {{ isAllExpanded ? '收起全部' : '展开全部' }}
        </div>
      </a-layout-sider>

      <!-- 主内容区 -->
      <a-layout class="main-layout">
        <a-layout-header class="app-header">
          <a-button type="text" class="collapse-btn" @click="collapsed = !collapsed">
            <MenuUnfoldOutlined v-if="collapsed" />
            <MenuFoldOutlined v-else />
          </a-button>
          <h2 class="page-title">{{ pageTitle }}</h2>
          <!-- 滚动公告栏 -->
          <div class="header-marquee" :class="{ 'marquee-empty': !marqueeText }" @dblclick="openMarqueeEdit">
            <div v-if="marqueeText" class="marquee-track" :class="{ 'marquee-scroll': marqueeText.length > 20 }">
              {{ marqueeText }}
            </div>
            <span v-else class="marquee-placeholder">双击设置公告</span>
          </div>
          <a-tooltip title="编辑公告" v-if="marqueeText">
            <a-button type="text" size="small" style="margin-left: 6px; color: var(--text-tertiary)" @click="openMarqueeEdit">
              <template #icon><EditOutlined /></template>
            </a-button>
          </a-tooltip>
          <div class="header-right">
            <!-- 全局搜索 -->
            <a-tooltip title="搜索 (⌘K)">
              <a-button type="text" class="search-btn" @click="openSearch">
                <template #icon><SearchOutlined /></template>
              </a-button>
            </a-tooltip>
            <a-dropdown>
              <a-button type="text" class="user-btn">
                <UserOutlined />
                <span class="user-name">{{ currentUser }}</span>
              </a-button>
              <template #overlay>
                <a-menu @click="onUserMenu">
                  <a-menu-item key="password">
                    <template #icon><KeyOutlined /></template>
                    修改密码
                  </a-menu-item>
                  <a-menu-item key="security-code">
                    <template #icon><SafetyOutlined /></template>
                    安全码设置
                  </a-menu-item>
                  <a-menu-divider />
                  <a-menu-item key="logout">
                    <template #icon><LogoutOutlined /></template>
                    退出登录
                  </a-menu-item>
                </a-menu>
              </template>
            </a-dropdown>
            <span class="today-date">{{ todayStr }}</span>
          </div>
        </a-layout-header>
        <a-layout-content class="app-content">
          <router-view />
        </a-layout-content>
        <a-layout-footer class="app-footer">
          All-in-One 个人管理系统 ©2026
        </a-layout-footer>
      </a-layout>

      <!-- 公告编辑弹窗 -->
      <a-modal v-model:open="marqueeEditOpen" title="设置公告栏文字" ok-text="保存" cancel-text="取消" @ok="saveMarquee" width="480px">
        <p style="color: var(--text-tertiary); font-size: 13px; margin-bottom: 8px">
          输入要滚动显示的文字，留空则不显示公告栏（双击公告栏也可编辑）
        </p>
        <a-textarea v-model:value="marqueeInput" :rows="3" :maxlength="200" show-count placeholder="输入公告内容..." />
      </a-modal>

      <!-- 修改密码弹窗 -->
      <a-modal v-model:open="pwdModalOpen" title="修改密码" ok-text="确认" cancel-text="取消" @ok="handleChangePwd" :confirm-loading="pwdSaving" width="400px">
        <a-form layout="vertical" style="margin-top: 16px">
          <a-form-item label="旧密码">
            <a-input-password v-model:value="pwdForm.old" placeholder="输入旧密码" />
          </a-form-item>
          <a-form-item label="新密码">
            <a-input-password v-model:value="pwdForm.new" placeholder="至少 4 个字符" />
          </a-form-item>
          <a-form-item label="确认新密码">
            <a-input-password v-model:value="pwdForm.confirm" placeholder="再次输入新密码" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 安全码设置弹窗 -->
      <a-modal v-model:open="scModalOpen" title="安全码设置" ok-text="确认" cancel-text="取消" @ok="handleSetSecurityCode" :confirm-loading="scSaving" width="400px">
        <a-alert message="安全码用于忘记密码时重置密码，请牢记" type="info" show-icon style="margin-bottom: 16px" />
        <a-form layout="vertical" style="margin-top: 8px">
          <a-form-item label="当前密码">
            <a-input-password v-model:value="scForm.password" placeholder="输入当前密码以确认身份" />
          </a-form-item>
          <a-form-item label="安全码">
            <a-input-password v-model:value="scForm.code" placeholder="至少 4 个字符" />
          </a-form-item>
          <a-form-item label="确认安全码">
            <a-input-password v-model:value="scForm.confirm" placeholder="再次输入安全码" />
          </a-form-item>
        </a-form>
      </a-modal>

      <!-- 全局搜索弹窗 -->
      <a-modal
        v-model:open="searchOpen"
        :footer="null"
        :width="560"
        :closable="true"
        :bodyStyle="{ padding: 0 }"
        @cancel="searchOpen = false"
        class="global-search-modal"
      >
        <div class="search-input-wrap">
          <SearchOutlined class="search-input-icon" />
          <a-input
            ref="searchInputRef"
            v-model:value="searchKeyword"
            placeholder="搜索旅行、骑行、徒步、财务、基金、物品..."
            size="large"
            :bordered="false"
            @pressEnter="doSearch"
            allowClear
          />
          <a-tag v-if="searchKeyword" style="margin-right: 8px">Enter 搜索</a-tag>
          <a-tag v-else style="margin-right: 8px">⌘K</a-tag>
        </div>
        <div class="search-results" v-if="searchResults.length">
          <div
            v-for="(item, idx) in searchResults"
            :key="idx"
            class="search-result-item"
            @click="goSearchResult(item)"
          >
            <div class="search-result-icon">{{ item.icon }}</div>
            <div class="search-result-body">
              <div class="search-result-title">{{ item.title }}</div>
              <div class="search-result-sub">{{ item.subtitle }}</div>
            </div>
            <div class="search-result-meta">
              <a-tag size="small" :bordered="false" color="default">{{ item.module }}</a-tag>
              <span class="search-result-date" v-if="item.date">{{ item.date.slice(0, 10) }}</span>
            </div>
          </div>
        </div>
        <div class="search-empty" v-else-if="searchDone">
          <a-empty description="未找到相关结果" :image-style="{ height: '40px' }" />
        </div>
        <div class="search-hint" v-else>
          <span style="color: var(--text-tertiary); font-size: 13px">输入关键词，跨模块搜索所有数据</span>
        </div>
      </a-modal>
    </a-layout>
  </a-config-provider>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  DashboardOutlined,
  FundOutlined,
  MoneyCollectOutlined,
  EnvironmentOutlined,
  CompassOutlined,
  CarOutlined,
  GlobalOutlined,
  CloudServerOutlined,
  BoxPlotOutlined,
  FireOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  EditOutlined,
  UserOutlined,
  KeyOutlined,
  SafetyOutlined,
  SearchOutlined,
  LogoutOutlined,
  TrophyOutlined,
} from '@ant-design/icons-vue'
import zhCN from 'ant-design-vue/es/locale/zh_CN'
import './styles/variables.css'
import './styles/global.css'
import { authApi, setAppRouter } from '@/api'
import axios from 'axios'
import { Modal } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
setAppRouter(router)
const collapsed = ref(false)
const selectedKeys = ref(['dashboard'])
const openKeys = ref(['fund'])

// 移动端检测
const isMobile = ref(window.innerWidth < 768)
function onResize() {
  const mobile = window.innerWidth < 768
  isMobile.value = mobile
  if (mobile) {
    collapsed.value = true // 移动端默认折叠
  }
}

const allSubKeys = ['fund', 'finance', 'sports', 'vehicle', 'travel', 'item']
const isAllExpanded = computed(() => allSubKeys.every(k => openKeys.value.includes(k)))

function toggleAllMenus() {
  if (isAllExpanded.value) {
    openKeys.value = []
  } else {
    openKeys.value = [...allSubKeys]
  }
}
function expandAll() {
  openKeys.value = [...allSubKeys]
}
function collapseAll() {
  openKeys.value = []
}

// ── 滚动公告 ──
const marqueeText = ref(localStorage.getItem('app-marquee') || '')
const marqueeEditOpen = ref(false)
const marqueeInput = ref('')

function openMarqueeEdit() {
  marqueeInput.value = marqueeText.value
  marqueeEditOpen.value = true
}
function saveMarquee() {
  marqueeText.value = marqueeInput.value
  localStorage.setItem('app-marquee', marqueeInput.value)
  marqueeEditOpen.value = false
}

const todayStr = computed(() => {
  const d = new Date()
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return `${d.getMonth() + 1}月${d.getDate()}日 ${weekdays[d.getDay()]}`
})

const menuGroupMap = {
  'cycling-list': 'sports', 'cycling-bikes': 'sports', 'cycling-stats': 'sports', 'cycling-detail': 'sports',
  'finance-accounts-list': 'finance', 'finance-records': 'finance', 'finance-snapshots': 'finance', 'finance-stats': 'finance',
  'finance-bills': 'finance', 'finance-category-rules': 'finance',
  'fund-list': 'fund', 'fund-holdings': 'fund', 'fund-snapshot': 'fund',
  'hiking-list': 'sports', 'hiking-upload': 'sports', 'hiking-detail': 'sports', 'hiking-stats': 'sports',
  'running-list': 'sports', 'running-upload': 'sports', 'running-stats': 'sports', 'running-detail': 'sports',
  'sports-achievements': 'sports',
  'vehicle-list': 'vehicle', 'vehicle-fuel': 'vehicle', 'vehicle-stats': 'vehicle',
  'travel': 'travel', 'travel-home': 'travel', 'travel-stats': 'travel',
  'item-list': 'item',
}

// 详情页没有对应的菜单项，映射到父级列表页的 key
const detailToParentMap = {
  'cycling-detail': 'cycling-list',
  'hiking-detail': 'hiking-list',
  'running-detail': 'running-list',
}

const pageTitles = {
  'dashboard': '看板',
  'cycling-list': '骑行记录',
  'cycling-bikes': '我的车辆',
  'cycling-stats': '骑行统计',
  'finance-accounts-list': '我的账户',
  'finance-bills': '账单导入',
  'finance-records': '收支记录',
  'finance-category-rules': '分类规则',
  'finance-snapshots': '快照记录',
  'finance-stats': '财务统计',
  'fund-list': '自选基金',
  'fund-holdings': '持仓分析',
  'fund-snapshot': '持仓快照',
  'hiking-list': '徒步记录',
  'hiking-upload': '导入徒步活动',
  'hiking-detail': '活动详情',
  'hiking-stats': '徒步统计',
  'running-list': '跑步记录',
  'running-upload': '导入跑步活动',
  'running-detail': '活动详情',
  'running-stats': '跑步统计',
  'sports-achievements': '运动成就',
  'vehicle-list': '车辆管理',
  'vehicle-fuel': '能耗与费用',
  'vehicle-stats': '统计分析',
  'travel': '旅行管理',
  'travel-home': '旅行总览',
  'travel-stats': '统计分析',
  'backup-center': '备份中心',
}

const pageTitle = computed(() => pageTitles[selectedKeys.value[0]] || 'All-in-One')

function onMenuClick({ key }) {
  selectedKeys.value = [key]
  router.push({ name: key })
  // 移动端点击菜单后自动关闭侧边栏
  if (isMobile.value) {
    collapsed.value = true
  }
}

watch(() => route.name, (name) => {
  if (name) {
    // 详情页高亮对应的列表菜单项
    selectedKeys.value = [detailToParentMap[name] || name]
    const group = menuGroupMap[name]
    if (group && !openKeys.value.includes(group)) {
      openKeys.value.push(group)
    }
  }
}, { immediate: true })

// ── 用户菜单 ──
const currentUser = computed(() => {
  try {
    return JSON.parse(localStorage.getItem('user') || '{}').username || '用户'
  } catch {
    return '用户'
  }
})

const pwdModalOpen = ref(false)
const pwdSaving = ref(false)
const pwdForm = reactive({ old: '', new: '', confirm: '' })

const scModalOpen = ref(false)
const scSaving = ref(false)
const scForm = reactive({ password: '', code: '', confirm: '' })

function onUserMenu({ key }) {
  if (key === 'password') {
    pwdForm.old = ''
    pwdForm.new = ''
    pwdForm.confirm = ''
    pwdModalOpen.value = true
  } else if (key === 'security-code') {
    scForm.password = ''
    scForm.code = ''
    scForm.confirm = ''
    scModalOpen.value = true
  } else if (key === 'logout') {
    Modal.confirm({
      title: '确认退出',
      content: '确定要退出登录吗？',
      okText: '退出',
      cancelText: '取消',
      async onOk() {
        try { await authApi.logout() } catch {}
        localStorage.removeItem('token')
        localStorage.removeItem('user')
        router.push('/login')
      },
    })
  }
}

async function handleChangePwd() {
  if (!pwdForm.old || !pwdForm.new) {
    Modal.warning({ title: '提示', content: '请填写旧密码和新密码' })
    return
  }
  if (pwdForm.new.length < 4) {
    Modal.warning({ title: '提示', content: '新密码至少 4 个字符' })
    return
  }
  if (pwdForm.new !== pwdForm.confirm) {
    Modal.warning({ title: '提示', content: '两次输入的新密码不一致' })
    return
  }
  pwdSaving.value = true
  try {
    await authApi.changePassword(pwdForm.old, pwdForm.new)
    Modal.success({ title: '成功', content: '密码修改成功，下次登录生效' })
    pwdModalOpen.value = false
  } catch (e) {
    Modal.error({ title: '修改失败', content: e.response?.data?.detail || '请检查旧密码是否正确' })
  } finally {
    pwdSaving.value = false
  }
}

async function handleSetSecurityCode() {
  if (!scForm.password || !scForm.code) {
    Modal.warning({ title: '提示', content: '请填写当前密码和安全码' })
    return
  }
  if (scForm.code.length < 4) {
    Modal.warning({ title: '提示', content: '安全码至少 4 个字符' })
    return
  }
  if (scForm.code !== scForm.confirm) {
    Modal.warning({ title: '提示', content: '两次输入的安全码不一致' })
    return
  }
  scSaving.value = true
  try {
    await authApi.setSecurityCode(scForm.password, scForm.code)
    Modal.success({ title: '成功', content: '安全码设置成功，忘记密码时可通过安全码重置' })
    scModalOpen.value = false
  } catch (e) {
    Modal.error({ title: '设置失败', content: e.response?.data?.detail || '请检查密码是否正确' })
  } finally {
    scSaving.value = false
  }
}

// ── 全局搜索 ──
const searchOpen = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
const searchDone = ref(false)
const searchInputRef = ref(null)

function openSearch() {
  searchOpen.value = true
  searchKeyword.value = ''
  searchResults.value = []
  searchDone.value = false
  setTimeout(() => searchInputRef.value?.focus?.(), 100)
}

async function doSearch() {
  const q = searchKeyword.value.trim()
  if (!q) return
  try {
    const token = localStorage.getItem('token')
    const { data } = await axios.get('/api/search/', { params: { q }, headers: { Authorization: `Bearer ${token}` } })
    searchResults.value = data.results || []
  } catch {
    searchResults.value = []
  }
  searchDone.value = true
}

function goSearchResult(item) {
  searchOpen.value = false
  router.push(item.url)
}

// Cmd+K / Ctrl+K 快捷键
import { onMounted, onUnmounted, nextTick } from 'vue'

function onKeyDown(e) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    openSearch()
  }
}

onMounted(() => {
  window.addEventListener('resize', onResize)
  onResize()
  window.addEventListener('keydown', onKeyDown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('resize', onResize)
})
</script>

<style>
/* ── 侧边栏 ── */
.sidebar {
  background: var(--bg-sidebar) !important;
  box-shadow: 2px 0 8px rgba(0,0,0,.15);
  position: relative;
  height: 100vh;
  overflow-y: auto;
  overflow-x: hidden;
  z-index: 10;
  flex-shrink: 0;
}
.sidebar .ant-layout-sider-children {
  display: flex;
  flex-direction: column;
  min-height: 100%;
}
.sidebar-menu {
  flex: 1;
  border-inline-end: none !important;
  background: transparent !important;
  padding: 8px 0;
}
.sidebar-menu .ant-menu-item,
.sidebar-menu .ant-menu-submenu-title {
  margin: 2px 8px !important;
  border-radius: var(--radius-md) !important;
  height: 40px !important;
  line-height: 40px !important;
}
.sidebar-menu .ant-menu-item-selected {
  background: rgba(99, 102, 241, 0.35) !important;
  box-shadow: inset 3px 0 0 #6366f1;
}
.sidebar-menu .ant-menu-item-selected:hover {
  background: rgba(99, 102, 241, 0.45) !important;
}
.sidebar-menu .ant-menu-item-selected .ant-menu-title-content,
.sidebar-menu .ant-menu-item-selected .anticon {
  color: #fff !important;
  font-weight: 600 !important;
}
.sidebar-menu .ant-menu-sub {
  background: transparent !important;
}
.sidebar-menu .ant-menu-item:hover {
  background: rgba(255, 255, 255, 0.06) !important;
}

/* 侧边栏空白区 */
.sidebar-blank {
  flex: 1;
  cursor: pointer;
}

/* Logo */
.logo {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 0 16px;
  background: rgba(0,0,0,0.15);
  border-bottom: 1px solid rgba(255,255,255,.08);
}
.logo-icon {
  width: 36px;
  height: 36px;
  border-radius: 8px;
  background: linear-gradient(135deg, #7C3AED, #6D28D9);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  font-weight: 800;
  letter-spacing: -0.5px;
  flex-shrink: 0;
  box-shadow: 0 2px 6px rgba(124, 58, 237, 0.4);
}
.logo-text {
  font-size: var(--font-xl);
  font-weight: 700;
  color: var(--text-white);
  letter-spacing: -0.5px;
  white-space: nowrap;
}
.logo-action-btn {
  color: rgba(255,255,255,0.5) !important;
  font-size: 12px;
  width: 22px;
  height: 22px;
  min-width: 22px;
  padding: 0 !important;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  flex-shrink: 0;
  margin-left: -4px;
}
.logo-action-btn:hover {
  color: rgba(255,255,255,0.85) !important;
  background: rgba(255,255,255,0.1) !important;
}

/* Header */
.app-header {
  background: var(--bg-header) !important;
  padding: 0 24px !important;
  display: flex;
  align-items: center;
  box-shadow: var(--shadow-sm);
  height: 56px !important;
  line-height: 56px !important;
  position: sticky;
  top: 0;
  z-index: 9;
}
.collapse-btn {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  color: var(--text-secondary);
}

/* 覆盖 Ant Design Vue 布局组件默认值 */
:root {
  --layout-footer-padding: 4px 24px;
  --layout-footer-background: transparent;
}

/* Ant Design Layout Footer 强制压缩 */
.ant-layout-footer.app-footer,
.ant-layout-footer[class="app-footer"] {
  padding: 4px 24px !important;
  background: transparent !important;
  line-height: 1.2 !important;
  min-height: 0 !important;
}

.collapse-btn:hover {
  color: var(--primary) !important;
  background: var(--bg-hover) !important;
}
.page-title {
  margin: 0 !important;
  font-size: var(--font-lg) !important;
  color: var(--text-primary) !important;
  font-weight: 600 !important;
  margin-left: 8px !important;
  flex-shrink: 0;
}

/* 滚动公告栏 */
.header-marquee {
  flex: 1;
  margin: 0 16px;
  overflow: hidden;
  white-space: nowrap;
  position: relative;
  cursor: pointer;
  border-radius: var(--radius-sm);
  padding: 0 8px;
}
.marquee-empty {
  display: flex;
  align-items: center;
  cursor: pointer;
}
.marquee-placeholder {
  color: var(--text-quaternary);
  font-size: var(--font-xs);
  border: 1px dashed var(--border-light);
  border-radius: var(--radius-sm);
  padding: 2px 12px;
  user-select: none;
}
.marquee-track {
  display: inline-block;
  font-size: var(--font-sm);
  color: var(--primary);
  font-weight: 500;
  padding-right: 40px;
}
.marquee-scroll {
  animation: marquee-left 18s linear infinite;
}
.marquee-empty:hover {
  background: var(--bg-hover);
}
@keyframes marquee-left {
  0% { transform: translateX(100%); }
  100% { transform: translateX(-100%); }
}
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}
.user-btn {
  color: var(--text-secondary) !important;
  font-size: 13px;
  border-radius: 8px !important;
  height: 36px !important;
  padding: 0 12px !important;
}
.user-btn:hover {
  color: var(--primary) !important;
  background: var(--bg-hover) !important;
}
.user-name {
  margin-left: 4px;
}
.today-date {
  color: var(--text-tertiary);
  font-size: var(--font-sm);
  margin-left: 4px;
}

/* Content */
.main-layout {
  flex: 1;
  overflow-x: hidden;
  min-width: 0;
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.app-content {
  margin: 20px 24px !important;
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

/* Footer */
.app-footer {
  flex-shrink: 0;
  text-align: center;
  color: var(--text-tertiary);
  font-size: var(--font-xs);
  line-height: 1.2 !important;
  padding: 4px 24px;
  min-height: 0 !important;
}

/* ── 全局搜索 ── */
.search-btn {
  color: var(--text-tertiary) !important;
  font-size: 16px;
}
.search-btn:hover {
  color: var(--primary) !important;
  background: var(--primary-bg) !important;
}
.search-input-wrap {
  display: flex;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid var(--border);
  gap: 8px;
}
.search-input-wrap .search-input-icon {
  color: var(--text-tertiary);
  font-size: 16px;
  flex-shrink: 0;
}
.search-input-wrap .ant-input {
  flex: 1;
  box-shadow: none !important;
}
.search-input-wrap .ant-tag {
  flex-shrink: 0;
  font-size: 11px;
  line-height: 18px;
  padding: 0 6px;
}
.search-results {
  max-height: 400px;
  overflow-y: auto;
}
.search-result-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.15s;
}
.search-result-item:hover {
  background: var(--primary-bg);
}
.search-result-icon {
  font-size: 22px;
  flex-shrink: 0;
  width: 32px;
  text-align: center;
}
.search-result-body {
  flex: 1;
  min-width: 0;
}
.search-result-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-result-sub {
  font-size: 12px;
  color: var(--text-tertiary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.search-result-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
  flex-shrink: 0;
}
.search-result-date {
  font-size: 11px;
  color: var(--text-quaternary);
}
.search-empty,
.search-hint {
  padding: 32px 16px;
  text-align: center;
}

/* ══════════════════════════════════════════
   移动端响应式（< 768px）
══════════════════════════════════════════ */

/* 移动端遮罩 */
.mobile-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  z-index: 99;
}

/* 移动端侧边栏：默认完全隐藏（宽度 0，无宽度占位） */
.sidebar-mobile {
  position: fixed !important;
  top: 0;
  left: 0;
  height: 100vh;
  z-index: 100;
  transform: translateX(-100%);
  transition: transform 0.25s ease;
  /* 覆盖模式：不占文档流宽度 */
  min-width: 0 !important;
  max-width: 0 !important;
  width: 0 !important;
  flex: none !important;
}
/* 移动端侧边栏展开 */
.sidebar-mobile.sidebar-mobile-open {
  transform: translateX(0);
  width: 230px !important;
  max-width: 230px !important;
}

@media (max-width: 767px) {
  /* header 收紧 */
  .app-header {
    padding: 0 12px !important;
  }
  .page-title {
    font-size: 15px !important;
    margin-left: 4px !important;
  }
  /* 公告栏小屏隐藏 */
  .header-marquee {
    display: none !important;
  }
  /* 日期小屏隐藏 */
  .today-date {
    display: none !important;
  }
  /* 内容区左右边距收紧 */
  .app-content {
    margin: 12px 10px !important;
  }
  /* 页脚压缩 */
  .app-footer {
    font-size: 11px !important;
    padding: 2px 10px !important;
  }
}
</style>
