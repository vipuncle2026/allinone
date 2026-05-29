const { app, BrowserWindow, Tray, Menu, dialog, shell, ipcMain } = require('electron')
const path = require('path')
const { spawn } = require('child_process')
const http = require('http')
const net = require('net')

// ── 配置 ──────────────────────────────────────────────────────────
const API_PORT = 8000
const HEALTH_TIMEOUT = 15000  // 等待后端就绪的最长时间（毫秒）
const HEALTH_INTERVAL = 500   // 健康检查间隔

let mainWindow = null
let tray = null
let apiProcess = null
let actualPort = API_PORT

// ── 工具函数 ──────────────────────────────────────────────────────

/** 获取应用数据目录（~/Library/Application Support/AllInOne/） */
function getAppDataDir() {
  return path.join(app.getPath('userData'), 'data')
}

/** 检查端口是否被占用 */
function isPortInUse(port) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', () => resolve(true))
    server.once('listening', () => { server.close(); resolve(false) })
    server.listen(port, '127.0.0.1')
  })
}

/** 找一个空闲端口 */
async function findFreePort(startPort) {
  if (!(await isPortInUse(startPort))) return startPort
  for (let p = startPort + 1; p < startPort + 100; p++) {
    if (!(await isPortInUse(p))) return p
  }
  return null
}

/** 等待后端健康检查通过 */
function waitForHealth(port) {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + HEALTH_TIMEOUT
    const check = () => {
      http.get(`http://127.0.0.1:${port}/health`, (res) => {
        let data = ''
        res.on('data', (chunk) => { data += chunk })
        res.on('end', () => {
          try {
            const json = JSON.parse(data)
            if (json.status === 'healthy') {
              resolve()
            } else {
              retryOrReject()
            }
          } catch {
            retryOrReject()
          }
        })
      }).on('error', retryOrReject)

      function retryOrReject() {
        if (Date.now() < deadline) {
          setTimeout(check, HEALTH_INTERVAL)
        } else {
          reject(new Error(`后端启动超时（${HEALTH_TIMEOUT / 1000}秒），请检查日志`))
        }
      }
    }
    check()
  })
}

/** 检查指定端口的 HTTP 服务是否是健康的 All-in-One 后端 */
function checkExistingBackend(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
      let data = ''
      res.on('data', (chunk) => { data += chunk })
      res.on('end', () => {
        try {
          const json = JSON.parse(data)
          resolve(json.status === 'healthy')
        } catch {
          resolve(false)
        }
      })
    })
    req.on('error', () => resolve(false))
    req.setTimeout(2000, () => { req.destroy(); resolve(false) })
  })
}

/** 启动或连接 Python 后端 */
async function ensureApiServer() {
  const isDev = !app.isPackaged

  // 开发模式：先检查默认端口是否已有后端在跑（用户可能已通过 start.sh 启动）
  if (isDev) {
    const existingHealthy = await checkExistingBackend(API_PORT)
    if (existingHealthy) {
      console.log(`[APP] 检测到已有后端运行在 port ${API_PORT}，直接复用`)
      actualPort = API_PORT
      return
    }
  }

  // 生产模式或开发模式没有已有服务：自己启动
  actualPort = await findFreePort(API_PORT)
  if (!actualPort) {
    throw new Error('找不到可用端口（8000-8099 均被占用）')
  }

  const appDataDir = getAppDataDir()
  const backendDir = path.resolve(__dirname, '..')
  let pythonPath, args

  if (isDev) {
    pythonPath = path.join(backendDir, 'backend', 'venv', 'bin', 'python')
    const fs = require('fs')
    if (!fs.existsSync(pythonPath)) {
      pythonPath = 'python3'
    }
    args = ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(actualPort)]
  } else {
    // 生产模式：后端 serve 前端静态文件
    // PyInstaller COLLECT 输出的目录结构：allinone-api/allinone-api (可执行文件) + allinone-api/_internal/
    pythonPath = path.join(process.resourcesPath, 'allinone-api', 'allinone-api')
    args = ['--host', '127.0.0.1', '--port', String(actualPort), '--data-dir', appDataDir]
  }

  const env = Object.assign({}, process.env)
  env.DB_PATH = path.join(appDataDir, 'allinone.db')
  env.UPLOAD_DIR = path.join(appDataDir, 'uploads')
  // 生产模式：告诉后端前端 dist 的路径
  if (!isDev) {
    env.FRONTEND_DIST = path.join(process.resourcesPath, 'frontend-dist')
  }

  apiProcess = spawn(pythonPath, args, {
    cwd: isDev ? path.join(backendDir, 'backend') : undefined,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  apiProcess.stdout.on('data', (data) => {
    console.log(`[API] ${data}`)
  })
  apiProcess.stderr.on('data', (data) => {
    console.warn(`[API:ERR] ${data}`)
  })

  apiProcess.on('error', (err) => {
    console.error('[API] 启动失败:', err.message)
    dialog.showErrorBox('后端启动失败', `无法启动 Python 后端:\n${err.message}`)
  })

  apiProcess.on('close', (code) => {
    console.log(`[API] 进程退出 (code=${code})`)
    apiProcess = null
  })
}

// ── 窗口 ──────────────────────────────────────────────────────────

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 900,
    minHeight: 600,
    title: 'All-in-One',
    icon: path.join(__dirname, 'build', 'icon.png'),
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  // 清除 HTTP 缓存，防止加载旧版本的 JS/CSS chunk
  mainWindow.webContents.session.clearCache(() => {
    console.log('[APP] 已清除 HTTP 缓存')
  })

  // 开发模式加载 Vite dev server
  const isDev = !app.isPackaged
  if (isDev) {
    mainWindow.loadURL(`http://localhost:5173`)
    // mainWindow.webContents.openDevTools()
  } else {
    // 生产模式：前端静态文件由后端 serve
    mainWindow.loadURL(`http://127.0.0.1:${actualPort}`)
  }

  // 关闭窗口 = 隐藏到托盘（而非退出）
  mainWindow.on('close', (e) => {
    if (tray) {
      e.preventDefault()
      mainWindow.hide()
    }
  })

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── 托盘 ──────────────────────────────────────────────────────────

function createTray() {
  // macOS 状态栏图标必须是小尺寸（16x16 / 22x22@2x），使用 tray-icon 而非 256x256 的 icon
  const iconPath = path.join(__dirname, 'build', 'tray-icon.png')
  tray = new Tray(iconPath)
  tray.setToolTip('All-in-One 个人管理系统')

  const contextMenu = Menu.buildFromTemplate([
    {
      label: '显示窗口',
      click: () => {
        if (mainWindow) {
          mainWindow.show()
          mainWindow.focus()
        }
      },
    },
    { type: 'separator' },
    {
      label: `服务端口: ${actualPort}`,
      enabled: false,
    },
    { type: 'separator' },
    {
      label: '退出',
      click: () => {
        tray = null
        if (mainWindow) mainWindow.destroy()
        quitApp()
      },
    },
  ])

  tray.setContextMenu(contextMenu)

  // 点击托盘图标显示窗口
  tray.on('click', () => {
    if (mainWindow) {
      if (mainWindow.isVisible()) {
        mainWindow.focus()
      } else {
        mainWindow.show()
      }
    }
  })
}

// ── 中文菜单 ──────────────────────────────────────────────────────

function setAppMenu() {
  const template = [
    {
      label: 'All-in-One',
      submenu: [
        { label: '关于 All-in-One', role: 'about' },
        { type: 'separator' },
        { label: '隐藏 All-in-One', role: 'hide' },
        { label: '隐藏其他', role: 'hideOthers' },
        { label: '显示全部', role: 'unhide' },
        { type: 'separator' },
        { label: '退出 All-in-One', role: 'quit' },
      ],
    },
    {
      label: '编辑',
      submenu: [
        { label: '撤销', role: 'undo' },
        { label: '重做', role: 'redo' },
        { type: 'separator' },
        { label: '剪切', role: 'cut' },
        { label: '复制', role: 'copy' },
        { label: '粘贴', role: 'paste' },
        { label: '全选', role: 'selectAll' },
      ],
    },
    {
      label: '视图',
      submenu: [
        { label: '重新加载', role: 'reload' },
        { label: '强制重新加载', role: 'forceReload' },
        { type: 'separator' },
        { label: '实际大小', role: 'resetZoom' },
        { label: '放大', role: 'zoomIn' },
        { label: '缩小', role: 'zoomOut' },
        { type: 'separator' },
        { label: '全屏', role: 'togglefullscreen' },
        { type: 'separator' },
        { label: '开发者工具', role: 'toggleDevTools' },
      ],
    },
    {
      label: '窗口',
      submenu: [
        { label: '最小化', role: 'minimize' },
        { label: '缩放', role: 'zoom' },
        { type: 'separator' },
        { label: '前置所有窗口', role: 'front' },
      ],
    },
  ]
  const menu = Menu.buildFromTemplate(template)
  Menu.setApplicationMenu(menu)
}

// ── 退出清理 ──────────────────────────────────────────────────────

function quitApp() {
  if (apiProcess) {
    console.log('[APP] 正在关闭后端进程...')
    apiProcess.kill('SIGTERM')
    // 给 3 秒优雅关闭，之后强杀
    const forceKill = setTimeout(() => {
      if (apiProcess) {
        apiProcess.kill('SIGKILL')
        apiProcess = null
      }
    }, 3000)
    apiProcess.on('close', () => {
      clearTimeout(forceKill)
      apiProcess = null
    })
  }
  app.quit()
}

// ── IPC 处理 ──────────────────────────────────────────────────────

// 渲染进程请求实际端口
ipcMain.handle('get-api-port', () => actualPort)

// 外部链接用系统浏览器打开
ipcMain.handle('open-external', (_event, url) => {
  shell.openExternal(url)
})

// ── 应用生命周期 ──────────────────────────────────────────────────

app.on('window-all-closed', () => {
  // macOS：窗口全部关闭时不退出（保持托盘）
  // 其他平台：没有窗口时退出
  if (process.platform !== 'darwin' && !tray) {
    quitApp()
  }
})

app.on('before-quit', () => {
  // 设置退出标志，允许真正关闭窗口
  tray = null
})

app.on('activate', () => {
  // macOS：点击 dock 图标时恢复窗口
  if (mainWindow) {
    mainWindow.show()
  }
})

app.whenReady().then(async () => {
  try {
    console.log('[APP] 启动 All-in-One 桌面端...')
    console.log(`[APP] 数据目录: ${getAppDataDir()}`)

    // 设置中文菜单
    setAppMenu()

    // 启动或连接 Python 后端
    await ensureApiServer()

    // 如果是自己启动的后端，等待就绪
    if (apiProcess) {
      console.log(`[APP] 等待后端就绪 (port ${actualPort})...`)
      await waitForHealth(actualPort)
      console.log('[APP] 后端已就绪')
    }

    // 创建窗口
    createWindow()

    // 创建托盘
    createTray()

    console.log('[APP] 启动完成')
  } catch (err) {
    console.error('[APP] 启动失败:', err.message)
    dialog.showErrorBox('启动失败', err.message)
    app.quit()
  }
})
