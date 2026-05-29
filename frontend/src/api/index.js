import axios from 'axios'

// Electron 桌面端走直连后端，Web 端走相对路径（依赖 Nginx 代理）
const baseURL = window.electronAPI?.isElectron
  ? window.electronAPI.apiBaseUrl
  : '/api'

const http = axios.create({
  baseURL,
  timeout: 30000,
})

// ─── sessionStorage 简单缓存（5 分钟 TTL） ────────────────────
const CACHE_TTL_MS = 5 * 60 * 1000  // 5 分钟

/**
 * 带缓存的 GET 请求
 * @param {string} url  - 接口路径
 * @param {object} params - 查询参数（会序列化为缓存 key 的一部分）
 * @returns Promise<AxiosResponse>
 */
function cachedGet(url, params = {}) {
  const cacheKey = 'aio_cache:' + url + '?' + new URLSearchParams(params).toString()
  try {
    const cached = sessionStorage.getItem(cacheKey)
    if (cached) {
      const { data, ts } = JSON.parse(cached)
      if (Date.now() - ts < CACHE_TTL_MS) {
        // 缓存命中，包装成类 axios 响应对象返回
        return Promise.resolve({ data, _fromCache: true })
      }
    }
  } catch (_) { /* sessionStorage 不可用时退化为直接请求 */ }

  return http.get(url, { params }).then((res) => {
    try {
      sessionStorage.setItem(cacheKey, JSON.stringify({ data: res.data, ts: Date.now() }))
    } catch (_) { /* storage 满了就不缓存 */ }
    return res
  })
}

/**
 * 手动清除指定前缀的缓存（写操作后调用，使相关缓存失效）
 * @param {string} prefix - URL 前缀，例如 '/dashboard' 或 '/fund'
 */
export function invalidateCache(prefix) {
  const keysToDelete = []
  for (let i = 0; i < sessionStorage.length; i++) {
    const k = sessionStorage.key(i)
    if (k && k.startsWith('aio_cache:' + prefix)) {
      keysToDelete.push(k)
    }
  }
  keysToDelete.forEach((k) => sessionStorage.removeItem(k))
}

// ─── Token 自动附加 ─────────────────────────────────────────
http.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// ─── 401 自动跳转登录 ───────────────────────────────────────
// 登录成功后 3 秒内忽略 401（防止旧缓存/并发请求的竞态跳转）
let _loginTimestamp = 0
export function markJustLoggedIn() { _loginTimestamp = Date.now() }

let _401AlertShown = false
let _appRouter = null

/** App.vue 初始化时注入 router 实例 */
export function setAppRouter(router) { _appRouter = router }

http.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      // 刚登录 3 秒内不处理 401，避免旧请求竞态跳转
      if (Date.now() - _loginTimestamp < 3000) {
        return Promise.reject(err)
      }
      console.warn('[401] 触发跳转，请求:', err.config?.url)
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      if (window.location.pathname !== '/login') {
        if (!_401AlertShown) {
          _401AlertShown = true
          const doRedirect = () => {
            _401AlertShown = false
            if (_appRouter) {
              _appRouter.push('/login')
            } else {
              window.location.href = '/login'
            }
          }
          setTimeout(doRedirect, 100)
        }
      }
    }
    return Promise.reject(err)
  }
)

// ─── 骑行 API ─────────────────────────────────────────────────

export const cyclingApi = {
  /** 上传 GPX/FIT 文件解析（返回预览数据） */
  upload(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/cycling/upload', form)
  },

  /** 保存活动 */
  saveActivity(data) {
    return http.post('/cycling/activities', data)
  },

  /** 活动列表 */
  listActivities(params = {}) {
    return http.get('/cycling/activities', { params })
  },

  /** 活动详情 */
  getActivity(id) {
    return http.get(`/cycling/activities/${id}`)
  },

  /** 更新活动 */
  updateActivity(id, data) {
    return http.put(`/cycling/activities/${id}`, data)
  },

  /** 删除活动 */
  deleteActivity(id) {
    return http.delete(`/cycling/activities/${id}`)
  },

  /** 统计数据 */
  getStats() {
    return http.get('/cycling/activities/stats')
  },

  /** 运动成就 */
  getAchievements() {
    return http.get('/cycling/activities/achievements')
  },

  /** 车辆列表 */
  listBikes() {
    return http.get('/cycling/bikes')
  },

  /** 创建车辆 */
  createBike(data) {
    return http.post('/cycling/bikes', data)
  },

  /** 更新车辆 */
  updateBike(id, data) {
    return http.put(`/cycling/bikes/${id}`, data)
  },

  /** 删除车辆 */
  deleteBike(id) {
    return http.delete(`/cycling/bikes/${id}`)
  },

  /** 车辆维护记录 */
  listMaintenance(bikeId) {
    return http.get(`/cycling/bikes/${bikeId}/maintenance`)
  },

  /** 新增维护记录 */
  createMaintenance(data) {
    return http.post('/cycling/maintenance', data)
  },

  /** 删除维护记录 */
  deleteMaintenance(id) {
    return http.delete(`/cycling/maintenance/${id}`)
  },

  /** 导出 JSON 备份 */
  exportBackup() {
    return http.get('/cycling/export/backup', { responseType: 'blob' })
  },

  /** 导入 JSON 备份 */
  importBackup(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/cycling/import/backup', form)
  },

  /** 导出 CSV */
  exportCsv() {
    return http.get('/cycling/export/csv', { responseType: 'blob' })
  },

  /** 年度骑行总结 */
  getYearSummary(year) {
    return http.get('/cycling/activities/year-summary', { params: year ? { year } : {} })
  },
  /** 获取骑行默认参数（默认FTP） */
  getDefaults() {
    return http.get('/settings/cycling/defaults')
  },
  /** 保存骑行默认参数 */
  saveDefaults(data) {
    return http.put('/settings/cycling/defaults', data)
  },
}

// ─── Dashboard API ────────────────────────────────────────────

export const dashboardApi = {
  /** 跨模块近期动态时间线（5 分钟缓存） */
  getTimeline(limit = 20) {
    return cachedGet('/dashboard/timeline', { limit })
  },
  /** 本年运动月历热力（骑行+徒步按月，5 分钟缓存） */
  getActivityCalendar(year) {
    return cachedGet('/dashboard/activity-calendar', year ? { year } : {})
  },
  /** 今日/本周运动摘要（5 分钟缓存） */
  getSummary() {
    return cachedGet('/dashboard/summary', {})
  },
}

// ─── 基金 API ─────────────────────────────────────────────────

export const fundApi = {
  /** 查询基金信息（添加前预览） */
  search(code) {
    return http.get(`/fund/search/${code}`)
  },

  /** 添加自选（可同时设置持仓） */
  add(code, groupId = 'default', shares = 0, costNav = 0) {
    return http.post('/fund/add', { code, group_id: groupId, shares, cost_nav: costNav })
  },

  /** 移出自选 */
  remove(code) {
    return http.delete(`/fund/${code}`)
  },

  /** 刷新所有估值（刷新后清除相关缓存） */
  refresh() {
    return http.post('/fund/refresh').then((res) => {
      invalidateCache('/fund')
      invalidateCache('/dashboard')
      return res
    })
  },

  /** 基金列表（5 分钟缓存，刷新估值后会失效） */
  list(groupId = 'all') {
    return cachedGet('/fund/list', { group_id: groupId })
  },

  /** 基金详情 */
  detail(code) {
    return http.get(`/fund/detail/${code}`)
  },

  /** 更新持仓 */
  updateHolding(code, shares, costNav, type) {
    const payload = { shares, cost_nav: costNav }
    if (type) payload.type = type
    return http.put(`/fund/${code}/holding`, payload)
  },

  /** 修改分组 */
  changeGroup(code, groupId) {
    return http.put(`/fund/${code}/group`, { group_id: groupId })
  },

  /** 持仓汇总（5 分钟缓存） */
  holdingSummary() {
    return cachedGet('/fund/holding/summary', {})
  },

  /** 分组列表 */
  listGroups() {
    return http.get('/fund/groups')
  },

  /** 创建分组 */
  createGroup(name, color = '#6b7280') {
    return http.post('/fund/groups', { name, color })
  },

  /** 编辑分组 */
  updateGroup(groupId, name, color) {
    return http.put(`/fund/groups/${groupId}`, { name, color })
  },

  /** 删除分组 */
  deleteGroup(groupId) {
    return http.delete(`/fund/groups/${groupId}`)
  },

  /** 导出 */
  exportData() {
    return http.get('/fund/export')
  },

  /** 导入 */
  importData(funds) {
    return http.post('/fund/import', funds)
  },

  /** 手动触发今日持仓快照 */
  takeSnapshot() {
    return http.post('/fund/snapshot/take')
  },

  /** 获取持仓快照列表（days=0 表示全部） */
  snapshotList(days = 30) {
    return http.get('/fund/snapshot/list', { params: { days } })
  },

  /** 删除某天快照 */
  deleteSnapshot(date) {
    return http.delete(`/fund/snapshot/${date}`)
  },
}

// ─── 财务管理 API ─────────────────────────────────────────

export const financeApi = {
  getConfig() {
    return http.get('/finance/config')
  },

  listAccounts() {
    return http.get('/finance/accounts')
  },

  createAccount(data) {
    return http.post('/finance/accounts', data)
  },

  updateAccount(id, data) {
    return http.put(`/finance/accounts/${id}`, data)
  },

  deleteAccount(id) {
    return http.delete(`/finance/accounts/${id}`)
  },

  listTransactions(params = {}) {
    return http.get('/finance/transactions', { params })
  },

  createTransaction(data) {
    return http.post('/finance/transactions', data)
  },

  updateTransaction(id, data) {
    return http.put(`/finance/transactions/${id}`, data)
  },

  deleteTransaction(id) {
    return http.delete(`/finance/transactions/${id}`)
  },

  getStats() {
    return http.get('/finance/stats')
  },

  getMonthlyStats(year) {
    return http.get('/finance/stats/monthly', { params: { year } })
  },

  getCategoryStats(params = {}) {
    return http.get('/finance/stats/category', { params })
  },

  getSnapshotStats() {
    return http.get('/finance/snapshots/stats')
  },

  listSnapshots(days = 365, page = 1, limit = 25) {
    return http.get('/finance/snapshots', { params: { days, page, limit } })
  },

  createSnapshot() {
    return http.post('/finance/snapshots')
  },

  deleteSnapshot(id) {
    return http.delete(`/finance/snapshots/${id}`)
  },

  exportBackup() {
    return http.get('/finance/export/backup')
  },

  importBackup(data) {
    return http.post('/finance/import/backup', data)
  },

  exportCsv(type) {
    return http.get('/finance/export/csv', { params: { type }, responseType: 'blob' })
  },

  // 账单导入
  parseBill(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/finance/bills/parse', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    })
  },

  confirmBillImport(cacheKey, records) {
    return http.post('/finance/bills/import', { filename: cacheKey, records })
  },

  listBillImports() {
    return http.get('/finance/bills/imports')
  },

  deleteBillImport(id) {
    return http.delete(`/finance/bills/imports/${id}`)
  },

  // 分类规则
  listCategoryRules() {
    return http.get('/finance/category-rules')
  },

  createCategoryRule(data) {
    return http.post('/finance/category-rules', data)
  },

  updateCategoryRule(id, data) {
    return http.put(`/finance/category-rules/${id}`, data)
  },

  deleteCategoryRule(id) {
    return http.delete(`/finance/category-rules/${id}`)
  },

  reapplyCategoryRules() {
    return http.post('/finance/category-rules/reapply')
  },

  // 分类管理
  updateCategories(data) {
    return http.put('/finance/config/categories', data)
  },
  renameCategory(data) {
    return http.put('/finance/config/categories/rename', data)
  },
  deleteCategory(data) {
    return http.put('/finance/config/categories/delete', data)
  },

  // 统计增强
  getPlatformStats(params = {}) {
    return http.get('/finance/stats/platform', { params })
  },

  getTopMerchants(params = {}) {
    return http.get('/finance/stats/top-merchants', { params })
  },

  getTransferStats(params = {}) {
    return http.get('/finance/stats/transfer', { params })
  },

  getMonthlyCompare(params = {}) {
    return http.get('/finance/stats/monthly-compare', { params })
  },
}

// ─── 旅行管理 API ─────────────────────────────────────────

export const travelApi = {
  getConfig() {
    return http.get('/travel/config')
  },

  getCategoryStats() {
    return http.get('/travel/category-stats')
  },

  getYearlyStats() {
    return http.get('/travel/yearly-stats')
  },

  listTrips() {
    return http.get('/travel/trips')
  },

  getTrip(id) {
    return http.get(`/travel/trips/${id}`)
  },

  createTrip(data) {
    return http.post('/travel/trips', data)
  },

  updateTrip(id, data) {
    return http.put(`/travel/trips/${id}`, data)
  },

  deleteTrip(id) {
    return http.delete(`/travel/trips/${id}`)
  },

  listExpenses(tripId, params = {}) {
    return http.get(`/travel/trips/${tripId}/expenses`, { params })
  },

  createExpense(data) {
    return http.post('/travel/expenses', data)
  },

  updateExpense(id, data) {
    return http.put(`/travel/expenses/${id}`, data)
  },

  deleteExpense(id) {
    return http.delete(`/travel/expenses/${id}`)
  },

  listMileages(tripId) {
    return http.get(`/travel/trips/${tripId}/mileages`)
  },

  createMileage(data) {
    return http.post('/travel/mileages', data)
  },

  updateMileage(id, data) {
    return http.put(`/travel/mileages/${id}`, data)
  },

  deleteMileage(id) {
    return http.delete(`/travel/mileages/${id}`)
  },

  getStats(tripId) {
    return http.get(`/travel/trips/${tripId}/stats`)
  },

  exportCsv(tripId) {
    return http.get(`/travel/trips/${tripId}/export/csv`, { responseType: 'blob' })
  },

  importCsv(tripId, data) {
    return http.post(`/travel/trips/${tripId}/import/csv`, data)
  },

  /** 导出单个旅行为 JSON */
  exportTripJson(tripId) {
    return http.get(`/travel/trips/${tripId}/export/json`, { responseType: 'blob' })
  },

  /** 导出全部旅行为 JSON */
  exportAllJson() {
    return http.get('/travel/export-all/json', { responseType: 'blob' })
  },

  /** 导入旅行 JSON */
  importTripJson(data) {
    return http.post('/travel/import/json', data)
  },
}

// ─── 统一备份 API ─────────────────────────────────────────

export const backupApi = {
  /** 导出所有模块数据（仅数据） */
  exportAll() {
    return http.get('/backup/export')
  },
  /** 完整备份导出（数据 + 文件，zip格式） */
  exportFull() {
    return http.get('/backup/export/full', { responseType: 'blob' })
  },
  /** 导入备份数据（仅数据） */
  importAll(file) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/backup/import', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  /** 完整恢复（数据 + 文件，zip格式） */
  importFull(file) {
    const formData = new FormData()
    formData.append('file', file)
    return http.post('/backup/import/full', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  /** 获取各表记录数预览 */
  getInfo() {
    return http.get('/backup/info')
  },
  /** 获取操作记录 */
  getLogs(limit = 20) {
    return http.get('/backup/logs', { params: { limit } })
  },
  /** 删除操作记录 */
  deleteLog(logId) {
    return http.delete(`/backup/logs/${logId}`)
  },
  /** 清除全部操作记录 */
  clearLogs() {
    return http.delete('/backup/logs')
  },
  /** 数据初始化：清空所有业务表 */
  resetData() {
    return http.post('/backup/reset')
  },
  /** 清理 uploads/ 中不再被活动记录引用的孤儿文件 */
  cleanupOrphanFiles() {
    return http.post('/backup/cleanup-orphan-files')
  },
}

// ─── 徒步 API ─────────────────────────────────────────────────

export const hikingApi = {
  /** 上传 GPX/FIT 文件解析 */
  upload(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/hiking/upload', form)
  },

  /** 保存活动（文件导入） */
  saveActivity(data) {
    return http.post('/hiking/activities', data)
  },

  /** 手动录入 */
  createManual(data) {
    return http.post('/hiking/activities/manual', data)
  },

  /** 活动列表 */
  listActivities(params = {}) {
    return http.get('/hiking/activities', { params })
  },

  /** 活动详情 */
  getActivity(id) {
    return http.get(`/hiking/activities/${id}`)
  },

  /** 更新活动 */
  updateActivity(id, data) {
    return http.put(`/hiking/activities/${id}`, data)
  },

  /** 删除活动 */
  deleteActivity(id) {
    return http.delete(`/hiking/activities/${id}`)
  },

  /** 统计数据 */
  getStats() {
    return http.get('/hiking/activities/stats')
  },

  /** 年度徒步总结 */
  getYearSummary(year) {
    return http.get('/hiking/activities/year-summary', { params: year ? { year } : {} })
  },

  /** 运动成就 */
  getAchievements() {
    return http.get('/hiking/activities/achievements')
  },

  /** 导出 JSON 备份 */
  exportBackup() {
    return http.get('/hiking/export/json', { responseType: 'blob' })
  },

  /** 导出 CSV */
  exportCsv() {
    return http.get('/hiking/export/csv', { responseType: 'blob' })
  },
}

// ─── 跑步 API ─────────────────────────────────────────────────

export const runningApi = {
  /** 上传 GPX/FIT/TCX 文件解析 */
  upload(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/running/upload', form)
  },

  /** 保存活动（文件导入） */
  saveActivity(data) {
    return http.post('/running/activities', data)
  },

  /** 手动录入 */
  createManual(data) {
    return http.post('/running/activities/manual', data)
  },

  /** 活动列表 */
  listActivities(params = {}) {
    return http.get('/running/activities', { params })
  },

  /** 活动详情 */
  getActivity(id) {
    return http.get(`/running/activities/${id}`)
  },

  /** 更新活动 */
  updateActivity(id, data) {
    return http.put(`/running/activities/${id}`, data)
  },

  /** 删除活动 */
  deleteActivity(id) {
    return http.delete(`/running/activities/${id}`)
  },

  /** 统计数据 */
  getStats() {
    return http.get('/running/activities/stats')
  },

  /** 年度跑步总结 */
  getYearSummary(year) {
    return http.get('/running/activities/year-summary', { params: year ? { year } : {} })
  },

  /** 运动成就 */
  getAchievements() {
    return http.get('/running/activities/achievements')
  },

  /** 导出 JSON 备份 */
  exportBackup() {
    return http.get('/running/export/json', { responseType: 'blob' })
  },

  /** 导出 CSV */
  exportCsv() {
    return http.get('/running/export/csv', { responseType: 'blob' })
  },
}

// ─── 车辆管理 API ─────────────────────────────────────────────

export const vehicleApi = {
  list() { return http.get('/vehicle/list') },
  create(data) { return http.post('/vehicle/create', data) },
  update(id, data) { return http.put(`/vehicle/${id}`, data) },
  delete(id) { return http.delete(`/vehicle/${id}`) },

  listFuel(vehicleId, page = 1, pageSize = 20) {
    return http.get('/vehicle/fuel/list', { params: { vehicle_id: vehicleId, page, page_size: pageSize } })
  },
  createFuel(data) { return http.post('/vehicle/fuel/create', data) },
  updateFuel(id, data) { return http.put(`/vehicle/fuel/${id}`, data) },
  deleteFuel(id) { return http.delete(`/vehicle/fuel/${id}`) },

  listExpense(vehicleId, page = 1, pageSize = 20) {
    return http.get('/vehicle/expense/list', { params: { vehicle_id: vehicleId, page, page_size: pageSize } })
  },
  createExpense(data) { return http.post('/vehicle/expense/create', data) },
  updateExpense(id, data) { return http.put(`/vehicle/expense/${id}`, data) },
  deleteExpense(id) { return http.delete(`/vehicle/expense/${id}`) },

  getStats(vehicleId) { return http.get('/vehicle/stats', { params: { vehicle_id: vehicleId } }) },

  getAnalysis(vehicleId) { return http.get('/vehicle/stats/analysis', { params: { vehicle_id: vehicleId } }) },

  getRecent(limit = 10) { return http.get('/vehicle/recent', { params: { limit } }) },

  importXlsx(vehicleId, file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/vehicle/import/xlsx', form, { params: { vehicle_id: vehicleId } })
  },

  exportXlsx(vehicleId) {
    return http.get('/vehicle/export/xlsx', { params: { vehicle_id: vehicleId }, responseType: 'blob' })
  },
}

// ─── 认证 API ─────────────────────────────────────────────

export const itemApi = {
  /** 物品列表（分页+筛选） */
  list(params = {}) {
    return http.get('/item/list', { params })
  },
  /** 全部物品（不分页） */
  listAll() {
    return http.get('/item/all')
  },
  /** 物品详情 */
  get(id) {
    return http.get(`/item/${id}`)
  },
  /** 创建物品 */
  create(data) {
    return http.post('/item/create', data)
  },
  /** 更新物品 */
  update(id, data) {
    return http.put(`/item/${id}`, data)
  },
  /** 删除物品 */
  delete(id) {
    return http.delete(`/item/${id}`)
  },
  /** 批量更新状态/重要标记 */
  batchUpdate(data) {
    return http.post('/item/batch-update', data)
  },
  /** 批量删除 */
  batchDelete(ids) {
    return http.post('/item/batch-delete', { ids })
  },
  /** 分类配置 */
  getConfig() {
    return http.get('/item/config')
  },
  /** 统计数据 */
  getStats() {
    return http.get('/item/stats')
  },
  /** 上传照片 */
  uploadPhoto(file) {
    const form = new FormData()
    form.append('file', file)
    return http.post('/item/upload-photo', form)
  },
  /** 删除照片 */
  deletePhoto(path) {
    return http.delete('/item/photo', { params: { path } })
  },
  /** 导出 JSON */
  exportJson() {
    return http.get('/item/export/json')
  },
  /** 导入 JSON */
  importJson(data) {
    return http.post('/item/import/json', data)
  },
}

// ─── 认证 API ─────────────────────────────────────────────

export const authApi = {
  login(username, password) {
    return http.post('/auth/login', { username, password })
  },
  logout() {
    return http.post('/auth/logout')
  },
  getMe() {
    return http.get('/auth/me')
  },
  changePassword(oldPassword, newPassword) {
    return http.put('/auth/password', { old_password: oldPassword, new_password: newPassword })
  },
  setSecurityCode(password, securityCode) {
    return http.put('/auth/security-code', { password, security_code: securityCode })
  },
  resetPassword(username, securityCode, newPassword) {
    return http.post('/auth/reset-password', { username, security_code: securityCode, new_password: newPassword })
  },
}

export default http