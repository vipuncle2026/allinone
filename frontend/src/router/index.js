import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginPage.vue'),
    meta: { public: true },
  },
  {
    path: '/',
    redirect: '/dashboard'
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/dashboard/Dashboard.vue')
  },
  // 骑行模块（运动管理子模块）
  {
    path: '/sports/cycling',
    redirect: '/sports/cycling/list'
  },
  {
    path: '/sports/cycling/list',
    name: 'cycling-list',
    component: () => import('@/views/cycling/CyclingList.vue')
  },
  {
    path: '/sports/cycling/bikes',
    name: 'cycling-bikes',
    component: () => import('@/views/cycling/BikeManager.vue')
  },
  {
    path: '/sports/cycling/stats',
    name: 'cycling-stats',
    component: () => import('@/views/cycling/CyclingStats.vue')
  },
  {
    path: '/sports/cycling/settings',
    name: 'cycling-settings',
    component: () => import('@/views/cycling/CyclingSettings.vue')
  },
  {
    path: '/sports/cycling/:id',
    name: 'cycling-detail',
    component: () => import('@/views/cycling/CyclingDetail.vue')
  },
  // 基金模块
  {
    path: '/fund/list',
    name: 'fund-list',
    component: () => import('@/views/fund/FundList.vue')
  },
  {
    path: '/fund/holding',
    name: 'fund-holdings',
    component: () => import('@/views/fund/FundHolding.vue')
  },
  {
    path: '/fund/snapshot',
    name: 'fund-snapshot',
    component: () => import('@/views/fund/FundSnapshot.vue')
  },
  // 财务模块
  {
    path: '/finance',
    redirect: '/finance/accounts'
  },
  {
    path: '/finance/accounts',
    name: 'finance-accounts-list',
    component: () => import('@/views/finance/AccountList.vue')
  },
  {
    path: '/finance/records',
    name: 'finance-records',
    component: () => import('@/views/finance/TransactionList.vue')
  },
  {
    path: '/finance/snapshots',
    name: 'finance-snapshots',
    component: () => import('@/views/finance/FinanceSnapshot.vue')
  },
  {
    path: '/finance/stats',
    name: 'finance-stats',
    component: () => import('@/views/finance/FinanceStats.vue')
  },
  {
    path: '/finance/bills',
    name: 'finance-bills',
    component: () => import('@/views/finance/BillImport.vue')
  },
  {
    path: '/finance/category-rules',
    name: 'finance-category-rules',
    component: () => import('@/views/finance/CategoryRule.vue')
  },
  // 徒步模块（运动管理子模块）
  {
    path: '/sports/hiking',
    redirect: '/sports/hiking/list'
  },
  {
    path: '/sports/hiking/list',
    name: 'hiking-list',
    component: () => import('@/views/hiking/HikingList.vue')
  },
  {
    path: '/sports/hiking/upload',
    name: 'hiking-upload',
    component: () => import('@/views/hiking/HikingUpload.vue')
  },
  {
    path: '/sports/hiking/detail/:id',
    name: 'hiking-detail',
    component: () => import('@/views/hiking/HikingDetail.vue')
  },
  {
    path: '/sports/hiking/stats',
    name: 'hiking-stats',
    component: () => import('@/views/hiking/HikingStats.vue')
  },
  // 跑步模块（运动管理子模块）
  {
    path: '/sports/running',
    redirect: '/sports/running/list'
  },
  {
    path: '/sports/running/list',
    name: 'running-list',
    component: () => import('@/views/running/RunningList.vue')
  },
  {
    path: '/sports/running/upload',
    name: 'running-upload',
    component: () => import('@/views/running/RunningUpload.vue')
  },
  {
    path: '/sports/running/stats',
    name: 'running-stats',
    component: () => import('@/views/running/RunningStats.vue')
  },
  {
    path: '/sports/running/:id',
    name: 'running-detail',
    component: () => import('@/views/running/RunningDetail.vue')
  },
  // 运动成就
  {
    path: '/sports/achievements',
    name: 'sports-achievements',
    component: () => import('@/views/sports/Achievements.vue')
  },
  // 车辆管理模块
  {
    path: '/vehicle',
    redirect: '/vehicle/list'
  },
  {
    path: '/vehicle/list',
    name: 'vehicle-list',
    component: () => import('@/views/vehicle/VehicleList.vue')
  },
  {
    path: '/vehicle/fuel',
    name: 'vehicle-fuel',
    component: () => import('@/views/vehicle/VehicleFuel.vue')
  },
  {
    path: '/vehicle/stats',
    name: 'vehicle-stats',
    component: () => import('@/views/vehicle/VehicleStats.vue')
  },
  // 旅行管理模块
  {
    path: '/travel',
    name: 'travel-home',
    component: () => import('@/views/travel/TravelHome.vue')
  },
  {
    path: '/travel/detail/:id',
    name: 'travel-detail',
    component: () => import('@/views/travel/TravelDetail.vue')
  },
  {
    path: '/travel/stats',
    name: 'travel-stats',
    component: () => import('@/views/travel/TravelStats.vue')
  },
  // 备份中心
  {
    path: '/backup',
    name: 'backup-center',
    component: () => import('@/views/backup/BackupCenter.vue')
  },
  // 物品管理
  {
    path: '/item',
    name: 'item-list',
    component: () => import('@/views/item/ItemList.vue')
  },
]

const router = createRouter({
  history: createWebHistory('/'),
  routes
})

// ─── 全局路由守卫：未登录跳转登录页 ────────────────────────
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')

  // 公开页面直接放行
  if (to.meta.public) {
    if (to.name === 'login' && token) {
      next({ path: '/dashboard' })
    } else {
      next()
    }
    return
  }

  // 没有 token 直接跳登录
  if (!token) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }

  // 有 token 直接放行
  next()
})

export default router
