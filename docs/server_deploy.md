# Linux 服务器永久生产部署与全套运维实战手册

> **适用操作系统**：Ubuntu 20.04 / 22.04 / 24.04 LTS、Debian 11 / 12、CentOS 7 / 8 / Stream、Rocky Linux 9  
> **适用项目架构**：Uni-App 前端 + Python (FastAPI / Flask) 后端 + Golang 协议服务 + SQLite / Redis 持久化

---

## 目录
- [1. 服务器基础环境准备与系统初始化](#1-服务器基础环境准备与系统初始化)
- [2. Docker 与 Docker-Compose 容器化一键部署](#2-docker-与-docker-compose-容器化一键部署)
- [3. 裸机/原生 Python + Golang 永久常驻部署](#3-裸机原生-python--golang-永久常驻部署)
  - [3.1 Systemd 生产级服务守护](#31-systemd-生产级服务守护)
  - [3.2 Supervisor 进程守护方案](#32-supervisor-进程守护方案)
  - [3.3 PM2 进程守护方案](#33-pm2-进程守护方案)
- [4. Nginx 高性能反向代理与 WebSocket 配置](#4-nginx-高性能反向代理与-websocket-配置)
- [5. 免费自动化 HTTPS 证书配置 (Let's Encrypt / Certbot)](#5-免费自动化-https-证书配置-lets-encrypt--certbot)
- [6. 云服务器安全组与系统防火墙开放端口](#6-云服务器安全组与系统防火墙开放端口)
- [7. 服务实时日志查看与轮转管理](#7-服务实时日志查看与轮转管理)
- [8. 自动化热更新与版本迭代流程](#8-自动化热更新与版本迭代流程)
- [9. 数据库与用户凭证定时冷备份 (Crontab)](#9-数据库与用户凭证定时冷备份-crontab)
- [10. 全链路高频故障排查指令集](#10-全链路高频故障排查指令集)

---

## 1. 服务器基础环境准备与系统初始化

在全新的 Linux 服务器上执行以下指令，配置系统基础工具、Python 运行环境、Node.js 及编译依赖：

```bash
# ==========================================
# 步骤 1.1：更新系统软件源索引并升级已有软件包
# ==========================================
sudo apt update && sudo apt upgrade -y

# ==========================================
# 步骤 1.2：安装基础运维工具、编译依赖与网络诊断工具
# ==========================================
sudo apt install -y \
    curl \
    wget \
    git \
    vim \
    unzip \
    tar \
    lsof \
    net-tools \
    htop \
    tree \
    ca-certificates \
    gnupg \
    lsb-release \
    build-essential \
    libssl-dev \
    libffi-dev \
    sqlite3

# ==========================================
# 步骤 1.3：安装 Python 3.10+、pip 与虚拟环境模块
# ==========================================
sudo apt install -y python3 python3-pip python3-venv

# 验证 Python 版本（要求 >= 3.10）
python3 --version
pip3 --version

# ==========================================
# 步骤 1.4：配置系统时区为 Asia/Shanghai（中国标准时间）
# ==========================================
sudo timedatectl set-timezone Asia/Shanghai
timedatectl
```

---

## 2. Docker 与 Docker-Compose 容器化一键部署

### 2.1 安装 Docker 引擎与 Docker Compose 插件

```bash
# 1. 移除可能冲突的旧版本 Docker 组件
sudo apt remove -y docker docker-engine docker.io containerd runc

# 2. 添加 Docker 官方 GPG 密钥与软件源
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 3. 安装 Docker Engine 与 Docker Compose
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 4. 启动 Docker 并设置开机自启
sudo systemctl enable --now docker

# 5. 将当前用户加入 docker 组（避免每次使用 sudo）
sudo usermod -aG docker $USER
```

### 2.2 生产级 `docker-compose.yml` 编排配置

在项目部署根目录（如 `/opt/protocol_app`）下创建编排文件：

```bash
sudo mkdir -p /opt/protocol_app/data /opt/protocol_app/logs
cd /opt/protocol_app
```

编写 `docker-compose.yml`：

```yaml
version: "3.8"

services:
  # -------------------------------------------------------------
  # 微助教后台服务 (FastAPI)
  # -------------------------------------------------------------
  weizhujiao-api:
    image: python:3.11-slim
    container_name: weizhujiao-api
    restart: always
    working_dir: /app
    volumes:
      - ./微助教签到/server:/app
      - ./data/weizhujiao:/app/data
      - ./logs/weizhujiao:/app/logs
    environment:
      - PORT=17521
      - API_KEY=your-production-secret-key-2026
      - YYB_GO_URL=http://yyb-engine:8999
      - DB_PATH=/app/data/data.db
    command: >
      bash -c "pip install --no-cache-dir -r requirements.txt &&
               uvicorn main:app --host 0.0.0.0 --port 17521 --workers 2"
    ports:
      - "17521:17521"
    depends_on:
      - yyb-engine

  # -------------------------------------------------------------
  # 微信底层 MMTLS 协议引擎 (yyb-go)
  # -------------------------------------------------------------
  yyb-engine:
    image: alpine:latest
    container_name: yyb-engine
    restart: always
    working_dir: /app
    volumes:
      - ./微助教签到/yyb_go:/app
    command: /app/yyb-go -port 8999
    ports:
      - "8999:8999"

  # -------------------------------------------------------------
  # 雨课堂后台服务与 AI 视觉引擎 (Flask/Waitress)
  # -------------------------------------------------------------
  yuketang-api:
    image: python:3.11-slim
    container_name: yuketang-api
    restart: always
    working_dir: /app
    volumes:
      - ./雨课堂签到:/app
      - ./data/yuketang:/app/data
      - ./logs/yuketang:/app/logs
    environment:
      - YKT_PORT=5000
      - YKT_DATA_DIR=/app/data
      - YKT_ADMIN_KEY=your-admin-master-key-2026
      - AI_PROVIDER=siliconflow
      - AI_API_KEY=sk-your-ai-api-key-here
      - AI_BASE_URL=https://api.siliconflow.cn/v1
      - AI_MODELS=Qwen/Qwen2.5-VL-72B-Instruct
    command: >
      bash -c "pip install --no-cache-dir -r requirements.txt &&
               python api_server.py"
    ports:
      - "5000:5000"

  # -------------------------------------------------------------
  # 全局反向代理网关 (Nginx)
  # -------------------------------------------------------------
  nginx-gateway:
    image: nginx:alpine
    container_name: nginx-gateway
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - weizhujiao-api
      - yuketang-api
```

启动与管理 Docker 容器服务：

```bash
# 启动所有后台服务（后台常驻运行）
docker compose up -d

# 查看容器运行状态与健康度
docker compose ps

# 查看综合实时运行日志
docker compose logs -f --tail=100
```

---

## 3. 裸机/原生 Python + Golang 永久常驻部署

若服务器不使用 Docker，推荐使用 **Systemd** 或 **Supervisor** 进行进程常驻管理。

### 3.1 Systemd 生产级服务守护（推荐）

#### ① 配置微助教后端服务 (`/etc/systemd/system/wzj-api.service`)

```ini
[Unit]
Description=TeacherMate Auto Signin and Quiz Backend API
After=network.target yyb-engine.service
Wants=yyb-engine.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/projects/微助教签到/server
EnvironmentFile=/home/ubuntu/projects/微助教签到/server/.env
ExecStart=/home/ubuntu/projects/微助教签到/server/venv/bin/uvicorn main:app --host 0.0.0.0 --port 17521 --workers 2
Restart=always
RestartSec=5s
LimitNOFILE=65535
StandardOutput=append:/var/log/wzj-api.out.log
StandardError=append:/var/log/wzj-api.err.log

[Install]
WantedBy=multi-user.target
```

#### ② 配置微信 MMTLS 引擎 (`/etc/systemd/system/yyb-engine.service`)

```ini
[Unit]
Description=WeChat Protocol Underlying Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/projects/微助教签到
ExecStart=/home/ubuntu/projects/微助教签到/yyb-go -port 8999
Restart=always
RestartSec=3s
LimitNOFILE=65535
StandardOutput=append:/var/log/yyb.out.log
StandardError=append:/var/log/yyb.err.log

[Install]
WantedBy=multi-user.target
```

#### ③ 配置雨课堂后台 API 服务 (`/etc/systemd/system/ykt-api.service`)

```ini
[Unit]
Description=YuKeTang Distributed Auto Signin and AI Engine
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/ubuntu/projects/雨课堂签到
EnvironmentFile=/home/ubuntu/projects/雨课堂签到/deploy/ykt.env
ExecStart=/home/ubuntu/projects/雨课堂签到/venv/bin/python api_server.py
Restart=always
RestartSec=5s
LimitNOFILE=65535
StandardOutput=append:/var/log/ykt-api.out.log
StandardError=append:/var/log/ykt-api.err.log

[Install]
WantedBy=multi-user.target
```

#### 启用并激活 Systemd 服务

```bash
# 1. 重新加载 systemd 守护配置
sudo systemctl daemon-reload

# 2. 设置开机自启
sudo systemctl enable yyb-engine wzj-api ykt-api

# 3. 启动所有服务
sudo systemctl start yyb-engine wzj-api ykt-api

# 4. 查看运行状态
sudo systemctl status yyb-engine wzj-api ykt-api --no-pager
```

---

## 4. Nginx 高性能反向代理与 WebSocket 配置

安装 Nginx 并配置反向代理、WebSocket 长连接支持与客户端大文件上传：

```bash
# 1. 安装 Nginx
sudo apt install -y nginx

# 2. 创建主配置文件
sudo nano /etc/nginx/sites-available/protocol_apps.conf
```

写入以下标准生产 Nginx 配置：

```nginx
# =============================================================
# 上游服务器集群配置
# =============================================================
upstream weizhujiao_backend {
    server 127.0.0.1:17521 max_fails=3 fail_timeout=10s;
    keepalive 32;
}

upstream yuketang_backend {
    server 127.0.0.1:5000 max_fails=3 fail_timeout=10s;
    keepalive 32;
}

server {
    listen 80;
    server_name api.yourdomain.com; # 替换为您自己的真实域名或公网 IP

    # 客户端最大请求体（支持图片/音频作答上传）
    client_max_body_size 50M;

    # 开启 Gzip 极速压缩
    gzip on;
    gzip_min_length 1k;
    gzip_comp_level 6;
    gzip_types text/plain application/javascript application/x-javascript text/css application/xml text/javascript application/json;

    # ---------------------------------------------------------
    # 路由 1：微助教接口与 Web 管理控制台 (/070419)
    # ---------------------------------------------------------
    location / {
        proxy_pass http://weizhujiao_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket 协议升级支持 (Faye 动态码监听与心跳)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 10s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    # ---------------------------------------------------------
    # 路由 2：雨课堂接口与 WebSocket 实时课堂监听
    # ---------------------------------------------------------
    location /ykt/ {
        rewrite ^/ykt/(.*)$ /$1 break;
        proxy_pass http://yuketang_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 10s;
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

启用站点配置并重启 Nginx：

```bash
sudo ln -sf /etc/nginx/sites-available/protocol_apps.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

## 5. 免费自动化 HTTPS 证书配置 (Let's Encrypt / Certbot)

使用 EFF 官方 Certbot 自动化申请 SSL 证书并配置每月自动续期：

```bash
# 1. 安装 snapd 及 certbot
sudo apt install -y snapd
sudo snap install core && sudo snap refresh core
sudo snap install --classic certbot
sudo ln -sf /snap/bin/certbot /usr/bin/certbot

# 2. 一键申请证书并自动修改 Nginx 开启 HTTPS (需提前完成域名 DNS 解析)
sudo certbot --nginx -d api.yourdomain.com --non-interactive --agree-tos -m your-email@example.com --redirect

# 3. 模拟自动续期测试
sudo certbot renew --dry-run
```

---

## 6. 云服务器安全组与系统防火墙开放端口

在腾讯云 / 阿里云 / 华为云 / AWS 等云平台控制台的 **安全组 (Security Group)** 中配置入方向规则，同时在主机防火墙开放端口：

```bash
# ==========================================
# Ubuntu UFW 防火墙配置
# ==========================================
# 1. 允许 SSH 远程连接（防止失联）
sudo ufw allow 22/tcp

# 2. 允许 HTTP 与 HTTPS 访问
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 3. 若直接通过裸端口直连调试（可选）：
sudo ufw allow 17521/tcp comment "微助教 API 端口"
sudo ufw allow 5000/tcp comment "雨课堂 API 端口"

# 4. 启用防火墙
sudo ufw enable
sudo ufw status verbose
```

| 端口 | 协议 | 用途 | 安全策略建议 |
| :--- | :--- | :--- | :--- |
| **22** | TCP | SSH 远程登录 | 仅限个人固定 IP 或密钥认证 |
| **80** | TCP | HTTP 重定向 / 证书校验 | 开放 `0.0.0.0/0` |
| **443** | TCP | HTTPS 生产通信 | 开放 `0.0.0.0/0` |
| **17521** | TCP | 微助教后端直接端口 | 生产环境建议走 Nginx 443，关闭外部直接访问 |
| **5000** | TCP | 雨课堂后端直接端口 | 生产环境建议走 Nginx 443，关闭外部直接访问 |
| **8999** | TCP | yyb-go 微信底层通信 | **严格禁止外部公网访问** (仅限 `127.0.0.1`) |

---

## 7. 服务实时日志查看与轮转管理

### 实时日志跟踪指令

```bash
# 查看微助教 API 实时日志
journalctl -u wzj-api -f -n 100

# 查看雨课堂 API 实时日志
journalctl -u ykt-api -f -n 100

# 查看微信底协议引擎实时日志
journalctl -u yyb-engine -f -n 100

# 查看 Nginx 访问与错误日志
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

### 配置 Logrotate 防止日志打爆磁盘

创建 `/etc/logrotate.d/protocol_apps`：

```ini
/var/log/wzj-api*.log /var/log/ykt-api*.log /var/log/yyb*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 root root
}
```

---

## 8. 自动化热更新与版本迭代流程

编写一键热更新 Shell 脚本 `update.sh`：

```bash
#!/bin/bash
set -e

PROJECT_DIR="/home/ubuntu/projects"
echo "[*] 开始拉取最新代码..."
cd "$PROJECT_DIR"
git pull origin main

echo "[*] 更新微助教后端依赖与热重启..."
cd "$PROJECT_DIR/微助教签到/server"
./venv/bin/pip install -r requirements.txt --quiet
sudo systemctl restart wzj-api

echo "[*] 更新雨课堂后端依赖与热重启..."
cd "$PROJECT_DIR/雨课堂签到"
./venv/bin/pip install -r requirements.txt --quiet
sudo systemctl restart ykt-api

echo "[*] 重启微信底层引擎..."
sudo systemctl restart yyb-engine

echo "[√] 全系统更新完毕，服务状态如下："
sudo systemctl status wzj-api ykt-api yyb-engine --no-pager
```

赋予执行权限：
```bash
chmod +x update.sh
```

---

## 9. 数据库与用户凭证定时冷备份 (Crontab)

为防止意外误删或服务器故障，配置每日凌晨 3:00 自动将 SQLite 数据库与 JSON 凭证加密打包备份：

```bash
# 创建备份脚本
cat << 'EOF' > /home/ubuntu/backup_database.sh
#!/bin/bash
BACKUP_DIR="/home/ubuntu/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p "$BACKUP_DIR"

# 备份 SQLite 数据库文件 (采用在线 .backup 命令，避免读写锁冲突)
sqlite3 /home/ubuntu/projects/微助教签到/server/data.db ".backup '$BACKUP_DIR/wzj_data_${TIMESTAMP}.db'"

# 打包雨课堂 accounts.json 与历史记录
tar -czf "$BACKUP_DIR/ykt_backup_${TIMESTAMP}.tar.gz" \
    -C /home/ubuntu/projects/雨课堂签到 accounts.json ai_history.json

# 仅保留最近 30 天的历史备份
find "$BACKUP_DIR" -type f -mtime +30 -delete
echo "[$(date)] Backup completed: ${TIMESTAMP}" >> "$BACKUP_DIR/backup.log"
EOF

chmod +x /home/ubuntu/backup_database.sh
```

配置 Crontab 计划任务：

```bash
crontab -e
# 添加以下行（每日凌晨 03:00 自动执行）：
0 3 * * * /home/ubuntu/backup_database.sh >/dev/null 2>&1
```

---

## 10. 全链路高频故障排查指令集

| 故障现象 | 排查指令 | 常见根因与解决方法 |
| :--- | :--- | :--- |
| **端口已被占用 (Address already in use)** | `sudo lsof -i :17521` 或 `sudo netstat -tulpn \| grep 17521` | 上一个残留进程未正常退出。使用 `kill -9 <PID>` 强杀后重启。 |
| **微助教扫码 403 / API Key 无效** | `grep "API_KEY" /home/ubuntu/projects/微助教签到/server/.env` | 客户端请求头 `X-API-Key` 与服务端 `.env` 中的 `API_KEY` 不一致。 |
| **微信底层 MMTLS 引擎掉线** | `curl -s http://127.0.0.1:8999/health` | yyb-go 进程被系统 OOM Killer 杀掉。检查系统内存 `free -m` 并增加 Swap 交换分区。 |
| **HTTPS 访问报 502 Bad Gateway** | `sudo nginx -t && tail -n 50 /var/log/nginx/error.log` | Nginx 后端 upstream 目标端口服务未启动，或监听绑定了 `127.0.0.1` 导致 Docker 容器无法访问。 |
| **雨课堂 AI 解题超时 (504 Gateway Timeout)** | `curl -s http://127.0.0.1:5000/api/ai/health` | 目标大模型 API 提供商接口波动或 API Key 额度耗尽，检查 `SILICONFLOW_API_KEY`。 |
| **SQLite 报错 database is locked** | `sudo fuser /home/ubuntu/projects/微助教签到/server/data.db` | 多进程并发写入导致锁竞争，确保启用了 WAL 模式 (`PRAGMA journal_mode=WAL;`)。 |
