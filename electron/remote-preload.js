const { contextBridge, ipcRenderer } = require('electron')

function invokeFromErrorPage(channel) {
  if (window.location.protocol !== 'file:') {
    return Promise.reject(new Error('该操作仅允许在连接错误页执行'))
  }
  return ipcRenderer.invoke(channel)
}

contextBridge.exposeInMainWorld('electronAPI', {
  isElectron: true,
  apiBaseUrl: '/api',
  getConnectionMode: () => ipcRenderer.invoke('get-connection-mode'),
  retryConnect: () => invokeFromErrorPage('retry-connect'),
  switchToLocal: () => invokeFromErrorPage('switch-to-local'),
  openSettings: () => invokeFromErrorPage('open-settings'),
})
