const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  /** 是否在 Electron 环境中运行 */
  isElectron: true,

  /** API 基础路径（相对路径，开发模式走 Vite proxy，生产模式走后端 serve） */
  apiBaseUrl: '/api',

  /** 获取后端实际端口 */
  getApiPort: () => ipcRenderer.invoke('get-api-port'),

  /** 用系统浏览器打开外部链接 */
  openExternal: (url) => ipcRenderer.invoke('open-external', url),

  /** 连接失败页：重试连接当前服务器 */
  retryConnect: () => ipcRenderer.invoke('retry-connect'),

  /** 连接失败页：切回本地模式（自带后端） */
  switchToLocal: () => ipcRenderer.invoke('switch-to-local'),

  /** 连接失败页：打开连接设置 */
  openSettings: () => ipcRenderer.invoke('open-settings'),
})
