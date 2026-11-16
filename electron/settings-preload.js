const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('settingsAPI', {
  /** 读取当前连接配置 */
  get: () => ipcRenderer.invoke('get-connection-settings'),

  /** 保存服务器地址（空字符串 = 本地模式），保存后自动重启 */
  save: (serverUrl) => ipcRenderer.invoke('save-connection-settings', { serverUrl }),

  /** 测试地址连通性 */
  test: (serverUrl) => ipcRenderer.invoke('test-connection', serverUrl),
})
