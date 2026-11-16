const { app, BrowserWindow, Tray, Menu, dialog, shell, ipcMain } = require('electron')
const path = require('path')
const fs = require('fs')
const { spawn } = require('child_process')
const http = require('http')
const https = require('https')
const net = require('net')

// ── 配置 ──────────────────────────────────────────────────────────
const API_PORT = 8000
const HEALTH_TIMEOUT = 15000  // 等待后端就绪的最长时间（毫秒）
const HEALTH_INTERVAL = 500   // 健康检查间隔

let mainWindow = null
let tray = null
let settingsWindow = null
let apiProcess = null
let actualPort = API_PORT
let config = {}

// ── 连接配置（config.json）────────────────────────────────────────

function configPath() {
  return path.join(app.getPath('userData'), 'config.json')
}

function loadConfig() {
  try {
    return JSON.parse(fs.readFileSync(configPath(), 'utf8')) || {}
  } catch {
    return {}
  }
}

function saveConfig(patch) {
  const next = Object.assign({}, loadConfig(), patch)
  try {
    fs.mkdirSync(path.dirname(configPath()), { recursive: true })
    fs.writeFileSync(configPath(), JSON.stringify(next, null, 2), 'utf8')
  } catch (e) {
    console.error('[CFG] 保存配置失败:', e.message)
  }
  config = next
  return next
}

/** 远程模式：配置了服务器地址就不启动本地后端 */
function isRemoteMode() {
  return !!(config.serverUrl && String(config.serverUrl).trim())
}

/** 规范化用户输入的地址（补 http://、去尾部斜杠/误填的 /api） */
function normalizeUrl(raw) {
  let u = String(raw || '').trim()
  if (!u) return ''
  // 只输了 IP/域名:端口 时补协议
  if (!/^https?:\/\//i.test(u)) u = 'http://' + u
  // 去掉尾部斜杠
  u = u.replace(/\/+$/, '')
  // 用户可能误填了 /api 结尾（前端自己会拼 /api）
  u = u.replace(/\/api$/i, '')
  return u
}

/** 取地址的 scheme://host:port，用于提示 */
function describeUrl(url) {
  try {
    const u = new URL(url)
    const port = u.port || (u.protocol === 'https:' ? '443' : '80')
    return `${u.protocol}//${u.hostname}:${port}`
  } catch {
    return url
  }
}

/** 探测单个路径，返回解析后的 JSON（失败返回 null） */
function probePath(url, pathName, timeout) {
  return new Promise((resolve) => {
    let target
    try {
      target = new URL(pathName, url)
    } catch {
      return resolve(null)
    }
    const lib = target.protocol === 'https:' ? https : http
    const opts = { timeout }
    // NAS 自签证书很常见，探测阶段放过证书校验
    if (target.protocol === 'https:') opts.rejectUnauthorized = false
    const req = lib.get(target, opts, (res) => {
      let data = ''
      res.setEncoding('utf8')
      res.on('data', (c) => { data += c })
      res.on('end', () => {
        try {
          resolve(JSON.parse(data))
        } catch {
          resolve(null)
        }
      })
    })
    req.on('error', () => resolve(null))
    req.on('timeout', () => { req.destroy(); resolve(null) })
  })
}

/** 探测目标服务器是否是可用的 All-in-One 后端（依次尝试 /health、/api/health） */
async function detectServer(url, timeout = 3000) {
  for (const p of ['/health', '/api/health']) {
    const json = await probePath(url, p, timeout)
    if (json && (json.status === 'healthy' || json.status === 'ok')) {
      return { ok: true, path: p }
    }
  }
  return { ok: false, path: null }
}

/** 探测目标服务器是否是可用的 All-in-One 后端 */
async function checkServer(url, timeout = 3000) {
  const r = await detectServer(url, timeout)
  return r.ok
}

/** 检查根路径是否返回 HTML 页面（区分前端 nginx 与纯后端 API） */
function rootIsHtml(url, timeout = 3000) {
  return new Promise((resolve) => {
    let target
    try {
      target = new URL('/', url)
    } catch {
      return resolve(false)
    }
    const lib = target.protocol === 'https:' ? https : http
    const opts = { timeout }
    if (target.protocol === 'https:') opts.rejectUnauthorized = false
    const req = lib.get(target, opts, (res) => {
      const ct = String(res.headers['content-type'] || '')
      res.resume()
      resolve(ct.includes('text/html'))
    })
    req.on('error', () => resolve(false))
    req.on('timeout', () => { req.destroy(); resolve(false) })
  })
}

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

/** 根据模式加载页面内容 */
async function loadContent(win) {
  const isDev = !app.isPackaged

  // 远程模式：直连 NAS / 服务器，本地不启动后端
  if (isRemoteMode()) {
    const url = config.serverUrl
    console.log(`[APP] 远程模式，连接 ${url}`)
    const ok = await checkServer(url)
    if (!ok) return showConnectError(url, '无法连接到服务器')
    // 探活通过但根路径不是 HTML：说明填的是后端 API 端口，页面无法显示
    if (!(await rootIsHtml(url))) {
      return showConnectError(url, '该地址是后端 API 服务，页面无法显示。请填写 frontend/nginx 服务映射的端口')
    }
    win.loadURL(url)
    return
  }

  // 开发模式加载 Vite dev server
  if (isDev) {
    win.loadURL('http://localhost:5173')
    return
  }

  // 生产模式：前端静态文件由本地后端 serve
  win.loadURL(`http://127.0.0.1:${actualPort}`)
}

/** 显示连接失败页 */
function showConnectError(url, detail) {
  if (!mainWindow || mainWindow.isDestroyed()) return
  mainWindow.loadFile(path.join(__dirname, 'error.html'), {
    query: {
      url: url || '',
      detail: detail || '',
    },
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

  // 本地模式清缓存，防止加载旧版本 chunk；远程模式交给服务端 ETag 校验
  if (!isRemoteMode()) {
    mainWindow.webContents.session.clearCache(() => {
      console.log('[APP] 已清除 HTTP 缓存')
    })
  }

  loadContent(mainWindow)

  // 主框架加载失败 → 连接失败页（错误页自身用 file:// 加载，不会递归）
  mainWindow.webContents.on('did-fail-load', (_e, errorCode, errorDesc, validatedURL, isMainFrame) => {
    if (!isMainFrame) return
    if (!validatedURL || validatedURL.startsWith('file://')) return
    if (errorCode === -3) return  // ABORTED：主动中断（如重试换页），忽略
    console.warn(`[APP] 加载失败 ${validatedURL}: ${errorDesc} (${errorCode})`)
    showConnectError(validatedURL, errorDesc)
  })

  // 渲染进程日志 / 截图（排障用：AL_DEBUG=1 启动）
  if (process.env.AL_DEBUG) {
    mainWindow.webContents.on('console-message', (_e, level, msg, line, src) => {
      console.log(`[RENDERER:${level}] ${msg}  (${src}:${line})`)
    })
    // 记录所有 API 请求结果（含失败）
    mainWindow.webContents.session.webRequest.onCompleted({ urls: ['*://*/*api/*', '*://*/*health*'] }, (d) => {
      console.log(`[NET] ${d.statusCode} ${d.method} ${d.url}`)
    })
    mainWindow.webContents.session.webRequest.onErrorOccurred({ urls: ['*://*/*api/*'] }, (d) => {
      console.log(`[NET-ERR] ${d.error} ${d.method} ${d.url}`)
    })
    // 排障：AL_TOKEN 提供有效 token 时自动注入 localStorage（绕过登录页）
    let injected = false
    mainWindow.webContents.on('did-finish-load', async () => {
      const tk = process.env.AL_TOKEN
      if (tk && !injected && !mainWindow.webContents.getURL().startsWith('file://')) {
        injected = true
        await mainWindow.webContents.executeJavaScript(
          `localStorage.setItem('token','${tk}'); localStorage.setItem('user','{"id":1,"username":"admin"}'); location.href='/dashboard'`
        )
        console.log('[DEBUG] 已注入 token 并跳转 /dashboard')
      }
    })
    let shots = 0
    const timer = setInterval(async () => {
      if (mainWindow && !mainWindow.isDestroyed() && shots < 5) {
        shots++
        try {
          const img = await mainWindow.webContents.capturePage()
          fs.writeFileSync(`/tmp/al-page-${shots}.png`, img.toPNG())
          console.log(`[DEBUG] 截图${shots}: ${mainWindow.webContents.getURL()}`)
        } catch {}
      } else clearInterval(timer)
    }, 5000)
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

// ── 连接设置窗口 ──────────────────────────────────────────────────

function openSettingsWindow() {
  if (settingsWindow && !settingsWindow.isDestroyed()) {
    settingsWindow.focus()
    return
  }
  settingsWindow = new BrowserWindow({
    width: 560,
    height: 460,
    resizable: false,
    minimizable: false,
    maximizable: false,
    title: '连接设置',
    parent: mainWindow || undefined,
    show: false,
    webPreferences: {
      preload: path.join(__dirname, 'settings-preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  settingsWindow.setMenuBarVisibility(false)
  settingsWindow.loadFile(path.join(__dirname, 'settings.html'))
  settingsWindow.once('ready-to-show', () => settingsWindow.show())
  settingsWindow.on('closed', () => { settingsWindow = null })
}

/** 重启应用（切换模式后生效） */
function relaunchApp() {
  if (apiProcess) {
    try { apiProcess.kill('SIGTERM') } catch { /* ignore */ }
    apiProcess = null
  }
  app.relaunch()
  tray = null
  app.exit(0)
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
    isRemoteMode()
      ? { label: `服务器: ${config.serverUrl}`, enabled: false }
      : { label: `本地服务端口: ${actualPort}`, enabled: false },
    {
      label: '连接设置…',
      click: openSettingsWindow,
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
        {
          label: '连接设置…',
          accelerator: 'CmdOrCtrl+,',
          click: openSettingsWindow,
        },
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

// 连接设置：读取当前配置
ipcMain.handle('get-connection-settings', () => ({
  serverUrl: config.serverUrl || '',
  mode: isRemoteMode() ? 'remote' : 'local',
  localPort: actualPort,
}))

// 连接设置：保存并重启生效
ipcMain.handle('save-connection-settings', (_e, payload) => {
  const url = normalizeUrl(payload && payload.serverUrl)
  saveConfig({ serverUrl: url })
  if (settingsWindow && !settingsWindow.isDestroyed()) settingsWindow.close()
  setTimeout(() => relaunchApp(), 200)
  return { ok: true, serverUrl: url }
})

// 连接设置：测试连通性
ipcMain.handle('test-connection', async (_e, raw) => {
  const url = normalizeUrl(raw)
  if (!url) return { ok: false, message: '请输入服务器地址' }
  const r = await detectServer(url, 6000)
  if (!r.ok) {
    return {
      ok: false,
      url,
      message: `连不上 ${describeUrl(url)}，请确认端口、容器是否运行、以及防火墙`,
    }
  }
  // 探活通过但根路径不是 HTML → 大概率填了后端 API 端口
  if (!(await rootIsHtml(url, 6000))) {
    return {
      ok: false,
      url,
      message: '地址能连通，但这是后端 API 服务，页面无法显示。请填写 frontend/nginx 容器映射的端口',
    }
  }
  return { ok: true, message: `连接成功：${describeUrl(url)}（${r.path}）`, url }
})

// 连接失败页：重试
ipcMain.handle('retry-connect', async () => {
  if (!mainWindow || mainWindow.isDestroyed()) return { ok: false }
  if (isRemoteMode()) {
    const ok = await checkServer(config.serverUrl)
    if (ok) {
      mainWindow.loadURL(config.serverUrl)
      return { ok: true }
    }
    return { ok: false }
  }
  mainWindow.loadURL(`http://127.0.0.1:${actualPort}`)
  return { ok: true }
})

// 连接失败页：切回本地模式
ipcMain.handle('switch-to-local', () => {
  saveConfig({ serverUrl: '' })
  setTimeout(() => relaunchApp(), 200)
  return { ok: true }
})

// 打开连接设置窗口
ipcMain.handle('open-settings', () => {
  openSettingsWindow()
  return { ok: true }
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

    // 读取连接配置
    config = loadConfig()

    // 设置中文菜单
    setAppMenu()

    // 远程模式：不启动本地后端，直接连接服务器
    if (isRemoteMode()) {
      console.log(`[APP] 远程模式: ${config.serverUrl}`)
      createWindow()
      createTray()
      console.log('[APP] 启动完成（远程模式）')
      return
    }

    console.log(`[APP] 数据目录: ${getAppDataDir()}`)

    // 本地模式：启动或连接 Python 后端
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
