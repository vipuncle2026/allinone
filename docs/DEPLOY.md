# All-in-One 部署指南

本文档覆盖三种部署场景：**本地桌面开发**、**Docker 一键部署**、**飞牛 NAS（fnOS）生产部署**。

---

## 目录

- [前置准备](#前置准备)
- [场景一：本地开发](#场景一本地开发)
- [场景二：Docker 桌面部署](#场景二docker-桌面部署)
- [场景三：fnOS NAS 部署](#场景三fnos-nas-部署)
- [数据备份与迁移](#数据备份与迁移)
- [常见问题](#常见问题)

---

## 前置准备

### 硬件要求

| 场景 | CPU | 内存 | 磁盘 |
|------|-----|------|------|
| 本地开发 | 2 核 | 4 GB | 2 GB |
| Docker 桌面 | 2 核 | 4 GB | 5 GB |
| fnOS NAS | 2 核 | 2 GB | 10 GB |

### 软件依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| Docker | ≥ 20.10 | [官网下载](https://www.docker.com/get-started) |
| Docker Compose | ≥ 2.0 | Docker Desktop 自带 |
| Git | 任意 | 用于拉取代码 |

---

## 场景一：本地开发

适用于在 macOS / Windows / Linux 上修改代码、热重载调试。

### 1. 拉取代码

```bash
git clone https://your-repo/allinone.git
cd allinone
```

### 2. 启动后端

```bash
cd backend

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate     # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动后端（热重载模式）
uvicorn main:app --reload --port 8000
```

> 后端启动后自动创建 `allinone.db`，无需手动初始化数据库。

### 3. 启动前端

```bash
# 新开一个终端
cd frontend
npm install
npm run dev
```

### 4. 访问

- 前端：http://localhost:5173
- 后端 API：http://localhost:8000
- API 文档：http://localhost:8000/docs

### 5. 初始账号

```
用户名：admin
密码：admin123
```

> ⚠️ 首次登录后请立即修改密码。

### 6. 一键启动/停止

```bash
# 启动（自动检测端口冲突）
bash start.sh

# 停止
bash stop.sh
```

---

## 场景二：Docker 桌面部署

适用于在本地机器用 Docker 运行，不修改代码，专注使用。

### 1. 拉取代码

```bash
git clone https://your-repo/allinone.git
cd allinone
```

### 2. 创建数据目录

```bash
# 重要：容器需要预建目录
mkdir -p data uploads/cycling uploads/hiking uploads/running
```

### 3. 构建并启动

```bash
# 第一次运行会自动构建镜像（耗时 3-5 分钟）
docker compose up -d

# 查看构建和运行状态
docker compose ps
```

### 4. 访问

- 默认端口：http://localhost:8080
- 更换端口：编辑 `docker-compose.yml` 中的 `ports: "8080:80"`

### 5. 查看日志

```bash
# 实时日志
docker compose logs -f

# 只看后端日志
docker compose logs -f backend

# 只看前端日志
docker compose logs -f frontend
```

### 6. 停止服务

```bash
docker compose down
```

---

## 场景三：fnOS NAS 部署

适用于将服务部署在内网 NAS 上，局域网内多设备访问。

### 1. 远程连接 NAS

```bash
ssh admin@<NAS_IP>
```

### 2. 安装 Docker（如未安装）

fnOS 应用中心 → 搜索 "Docker" → 安装

### 3. 创建数据存储目录

在 fnOS 文件管理器中创建（或 SSH 执行）：

```bash
mkdir -p /mnt/user/appdata/allinone/data
mkdir -p /mnt/user/appdata/allinone/uploads/cycling
mkdir -p /mnt/user/appdata/allinone/uploads/hiking
mkdir -p /mnt/user/appdata/allinone/uploads/running
```

### 4. 拉取或上传代码

```bash
# 方式 A：SSH 中直接 git clone
cd /mnt/user/appdata/allinone
git clone https://your-repo/allinone.git
cd allinone

# 方式 B：在电脑上打包，上传到 NAS 后解压
# scp allinone.tar.gz admin@<NAS_IP>:/mnt/user/appdata/allinone/
```

### 5. 修改端口（如 80 被占用）

编辑 `docker-compose.yml`：

```yaml
services:
  frontend:
    ports:
      - "8080:80"    # ← 改这里，左边改成非占用端口
```

### 6. 启动服务

```bash
cd /mnt/user/appdata/allinone/allinone
docker compose up -d
```

### 7. 局域网访问

- http://`<NAS_IP>`:8080
- 端口可在 fnOS Docker 界面查看映射情况

### 8. 更新版本

```bash
cd /mnt/user/appdata/allinone/allinone
git pull
docker compose down
docker compose up -d --build   # 重新构建并启动
```

> ⚠️ `--build` 会重新构建镜像，请确保 `data/` 目录已挂载，数据不会丢失。

### 9. 使用 fnOS 私有仓库（可选）

如已在 fnOS 推送过镜像：

```bash
# 登录私有仓库
docker login docker.fnnas.com

# 修改 docker-compose.yml 使用私有镜像
# image: docker.fnnas.com/allinone-backend:latest

# 拉取镜像
docker compose pull
```

---

## 数据备份与迁移

### 备份（应用内）

1. 登录系统 → 左侧菜单 → **备份中心**
2. 点击 **完整备份** → 下载 ZIP 文件（含数据库 + 上传文件）
3. 备份文件保存到安全位置

### 备份（手动）

```bash
# 停止服务
docker compose down

# 打包数据目录
tar -czvf allinone_backup_$(date +%Y%m%d).tar.gz data/ uploads/

# 重启服务
docker compose up -d
```

### 恢复

1. 停止服务：`docker compose down`
2. 解压备份文件覆盖 `data/` 和 `uploads/`
3. 重启：`docker compose up -d`

### 迁移到新机器/NAS

1. 在原设备执行**完整备份**
2. 将 ZIP 上传到新设备
3. 在新设备 clone 代码，解压备份覆盖 `data/` 和 `uploads/`
4. 启动服务即可

---

## 常见问题

### Q1：启动后提示 502 Bad Gateway

**原因**：后端启动慢，Nginx 先启动了。

**解决**：
```bash
# 等待 10 秒后重启前端
docker compose restart frontend

# 查看后端是否正常
docker compose logs backend
```

### Q2：端口被占用

**解决**：编辑 `docker-compose.yml`，将 `"8080:80"` 改为其他未占用端口（如 `"3000:80"`）。

```bash
# 查看端口占用
# macOS
lsof -i :8080
# Linux
ss -tlnp | grep 8080
```

### Q3：fnOS 私有仓库拉取镜像 401 认证错误

```bash
# 确认登录了正确的仓库地址
docker login docker.fnnas.com

# 如仍报错，检查 fnOS 仓库设置中的用户名密码是否包含特殊字符
# 特殊字符会导致 Docker 认证失败，尝试更换不含特殊字符的密码
```

### Q4：上传 GPX/FIT 文件失败

**原因**：容器内 `/app/uploads` 目录权限问题。

**解决**：
```bash
# 确保目录属主正确
chmod -R 777 uploads/
```

### Q5：数据初始化后丢失了账号

默认管理员账号：
```
用户名：admin
密码：admin123
```

### Q6：如何修改默认端口？

编辑 `docker-compose.yml`：
```yaml
services:
  frontend:
    ports:
      - "自定义端口:80"   # 左边为宿主机端口
```

### Q7：如何设置开机自启（fnOS）？

fnOS Docker 界面 → 容器列表 → 点击容器 → 开启"开机自启"选项。

### Q8：内网穿透，远程访问 NAS 上的服务？

推荐方案（任选其一）：

| 方案 | 成本 | 难度 |
|------|------|------|
| Cloudflare Tunnel | 免费 | 简单 |
| Tailscale | 免费 | 简单 |
| frp | 免费 | 中等 |

> ⚠️ 暴露到公网前务必修改默认管理员密码。
