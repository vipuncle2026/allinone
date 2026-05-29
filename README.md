# All-in-One 个人管理系统

一个开箱即用的本地综合管理平台，涵盖**骑行、跑步、徒步、旅行、财务、基金、车辆、物品**八大模块，数据完全私有，支持 Docker 一键部署。

> **快速导航**：本地开发 · Docker 部署 · 功能介绍 · 项目结构 · 环境变量

---

## 🚀 快速启动

### 本地开发（macOS / Linux / Windows）

```bash
# 克隆后，进入项目目录
cd allinone

# 一键启动（自动安装依赖、启动前后端）
bash start.sh
```

访问 http://localhost:5173，默认管理员账号：`admin` / `admin123`

---

### Docker 部署（推荐）

```bash
# 方式一：直接启动
docker compose up -d

# 方式二：指定端口（宿主机 80 被占用时）
PORT=8080 docker compose up -d
```

访问 http://localhost:8080（Mac/Windows）或 http://<NAS_IP>:8080（NAS）

---

## ✨ 功能介绍

### 📊 看板
- ⌘K 全局快捷搜索，跨模块全文检索
- 近期动态时间线（骑行/跑步/徒步/旅行）
- 本年运动月历热力图

### 🚴 骑行管理
- GPX / FIT 文件一键导入（支持 Garmin Semicircles 坐标）
- 轨迹地图渲染（Leaflet + 高德瓦片，GCJ-02 坐标系）
- FIT 文件高级指标：NP 标准化功率 / TSS 训练压力 / IF 强度因子
- 车辆管理（多车支持）+ 维护记录
- 年度/月度统计图表

### 🏃 跑步管理
- GPX / FIT / TCX 三格式支持
- 轨迹地图 + 配速/心率/海拔曲线
- 成就系统（首次达成 / PB / 最长距离等）
- 年度统计 + 个人纪录追踪

### 🥾 徒步管理
- GPX / FIT / TCX 三格式支持
- 轨迹地图渲染
- 成就系统

### ✈️ 旅行管理
- 旅行计划 CRUD + 时间轴视图
- 费用/里程记录，JSON / CSV 批量导入导出
- 统计报表

### 💰 财务管理
- 多账户管理（现金/银行卡/支付宝/微信等）
- 收支记录（支持分类、标签、备注）
- 资产快照（按月自动记录）
- 统计报表（收支趋势、分类占比）

### 📈 基金管理
- 60+ 预置场外基金库
- 自选基金 + 分组管理
- 实时估值抓取（天天基金 API，异步并发）
- 持仓分析（成本/收益率/分红再投）

### 🚗 车辆管理
- 机动车信息管理
- 加油/充电记录
- 费用记录（保险/保养/停车等）
- 统计图表 + xlsx 导入导出

### 📦 物品管理
- 重要物品登记（名称/品牌/购买日期/价值）
- 9 分类支持（电子产品/家具/证件/首饰等）
- 照片上传

### 🔐 认证与备份
- SHA-256 加盐哈希 + 内存 Token + 24h 滑动窗口
- 安全码重置密码
- JSON / ZIP 完整备份 + 一键恢复
- 数据初始化（清空业务数据，保留账号）

---

## 🐳 部署指南

### 环境要求

| 环境 | 最低配置 | 推荐配置 |
|------|----------|----------|
| 本地桌面 | 2 核 CPU / 4GB 内存 | 4 核 / 8GB |
| NAS（fnOS /群晖） | 2 核 / 2GB | 4 核 / 4GB |

### fnOS（飞牛 NAS）部署

```bash
# 1. 在 fnOS 文件管理器中创建目录
/mnt/user/appdata/allinone/data

# 2. SSH 登录 fnOS，在目录内克隆项目
git clone https://your-repo/allinone.git
cd allinone

# 3. 修改 docker-compose.yml 中的端口（如 80 被占用）
# 编辑：ports: "8080:80"

# 4. 启动
docker compose up -d

# 5. 查看日志排错（如遇问题）
docker compose logs -f
```

> **私有仓库认证**（如使用 fnOS 私有镜像仓库）：
> ```bash
> docker login docker.fnnas.com
> # 输入 fnOS 用户名和密码
> ```

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8080` | 宿主机映射端口 |
| `TZ` | `Asia/Shanghai` | 时区 |
| `DB_PATH` | `/app/data/allinone.db` | 数据库路径（容器内） |

### 数据持久化

```
allinone/
├── data/              ← 数据库文件（allinone.db）
├── uploads/           ← 运动文件（GPX/FIT/TCX）
│   ├── cycling/
│   ├── hiking/
│   └── running/
└── backups/           ← 备份文件存放（可选）
```

> ⚠️ **重要**：首次启动前确保 `data/` 目录存在（Docker 不会自动创建含文件的目录）。

---

## 🛠 本地开发指南

### 1. 前置依赖

- Python 3.12+
- Node.js 20+
- npm 或 pnpm

### 2. 后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动（热重载）
uvicorn main:app --reload --port 8000

# 重置管理员密码
python reset_password.py
```

### 3. 前端

```bash
cd frontend

npm install
npm run dev
```

### 4. 目录结构

```
allinone/
├── backend/
│   ├── main.py              # FastAPI 入口
│   ├── database.py          # SQLAlchemy 配置 + 自动迁移
│   ├── models/              # 数据模型（12 个模块）
│   ├── routers/             # API 路由（14 个）
│   ├── services/
│   │   ├── gpx_parser.py    # GPX 解析
│   │   ├── fit_parser.py    # FIT 解析（含 NP/TSS/IF）
│   │   └── tcx_parser.py    # TCX 解析
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/           # 页面（按模块组织）
│   │   │   ├── dashboard/   # 看板
│   │   │   ├── cycling/     # 骑行
│   │   │   ├── running/     # 跑步
│   │   │   ├── hiking/       # 徒步
│   │   │   ├── travel/       # 旅行
│   │   │   ├── finance/      # 财务
│   │   │   ├── fund/         # 基金
│   │   │   ├── vehicle/      # 车辆
│   │   │   ├── item/         # 物品
│   │   │   └── backup/      # 备份中心
│   │   ├── api/             # 接口封装
│   │   └── router/          # Vue Router 配置
│   ├── Dockerfile
│   ├── nginx.conf           # Nginx 反向代理配置
│   └── vite.config.js
├── docs/                    # 文档
├── docker-compose.yml
├── start.sh                 # 本地一键启动
└── stop.sh                  # 停止服务
```

---

## 📝 数据库

- **引擎**：SQLite 3（单文件，无外部依赖）
- **表数量**：18 张（所有模块共用一个数据库）
- **迁移方式**：轻量自动迁移（`_auto_migrate`），无需 Alembic 手动操作
- **位置**：容器内 `/app/data/allinone.db`，映射到宿主机 `data/`

---

## 🔧 技术选型

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3 + Vite 5 |
| UI 组件库 | Ant Design Vue 4 |
| 地图 | Leaflet + 高德地图瓦片 |
| 后端框架 | FastAPI + SQLAlchemy |
| 坐标系 | WGS-84 ↔ GCJ-02 双向转换 |
| 运动格式 | gpxpy / fitparse / tcxparser |
| 容器化 | Docker + Docker Compose |
| 反向代理 | Nginx（前端 + API 统一入口） |

---

## 🤝 贡献与反馈

欢迎提交 Issue 或 Pull Request。

---

## 📄 许可证

MIT License
