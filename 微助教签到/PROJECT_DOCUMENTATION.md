# 天商便捷助手（TJCU Helper）全架构与生产部署说明文档

> **版本**：v2.1.0-Enterprise  
> **适用平台**：Android / iOS (Uni-App) + Linux (Ubuntu 20.04/22.04/24.04 LTS)  
> **核心特性**：微助教全协议极速并发签到、多题型智能答题、三层主动保活引擎、Web 专属管理控制台、远程动态配置竞速拉取。

---

## 目录
1. [系统整体架构与技术栈](#1-系统整体架构与技术栈)
2. [核心业务模块与全流程细节](#2-核心业务模块与全流程细节)
   - [2.1 签到引擎（全协议并发与微扰动）](#21-签到引擎全协议并发与微扰动)
   - [2.2 答题系统（多账号隔离与智能作答）](#22-答题系统多账号隔离与智能作答)
   - [2.3 三层纵深主动保活引擎](#23-三层纵深主动保活引擎)
   - [2.4 Web 版服务器账号管理控制台](#24-web-版服务器账号管理控制台)
   - [2.5 远端配置多源竞速拉取](#25-远端配置多源竞速拉取)
3. [项目工程目录结构说明](#3-项目工程目录结构说明)
4. [生产环境完美部署指南（Linux Ubuntu）](#4-生产环境完美部署指南linux-ubuntu)
   - [4.1 基础环境与依赖安装](#41-基础环境与依赖安装)
   - [4.2 yyb-go 微信协议引擎配置与部署](#42-yyb-go-微信协议引擎配置与部署)
   - [4.3 Python 后端 API 部署](#43-python-后端-api-部署)
   - [4.4 Supervisor 生产守护进程配置](#44-supervisor-生产守护进程配置)
   - [4.5 Nginx 反向代理与 SSL 配置（可选）](#45-nginx-反向代理与-ssl-配置可选)
   - [4.6 云服务器防火墙与安全组设置](#46-云服务器防火墙与安全组设置)
5. [日常运维与故障排查速查表](#5-日常运维与故障排查速查表)

---

## 1. 系统整体架构与技术栈

```mermaid
graph TD
    A["Uni-App 客户端 (App)"] -->|HTTP API (REST)| B["FastAPI 业务后端 (:17521)"]
    A -->|安全鉴权后缀 /070419| D["Web 账号管理控制台"]
    B -->|微信小程序 Code 申请| C["yyb-go 协议引擎 (:8999)"]
    B -->|OAuth / Session 接口| E["微助教官方服务器 (teachermate.cn)"]
    B -->|Faye WSS 广播监听| F["微助教 WebSocket (teachermate.com.cn/faye)"]
    B -->|数据持久化| G["SQLite3 本地数据库 (data.db)"]
    A -->|多源竞速拉取| H["GitCode / AtomGit 动态配置 (config.json)"]
```

### 技术栈选型
| 分层 | 技术选型 | 核心作用 |
|---|---|---|
| **移动客户端** | Vue.js 2 / Uni-App | 跨平台 Android / iOS 原生打包，现代卡片 UI，全手势交互 |
| **调度后端** | Python 3.10+ / FastAPI / Uvicorn | 异步高并发网络调度、签到/答题业务路由、Web 控制台渲染 |
| **微信协议层** | yyb-go (Golang 编译) | 微信 MMTLS 底层通信、长效 Token 维护、免扫码获取小程序 Code |
| **数据存储** | SQLite3 + aiosqlite | 账号凭证、微助教会话、作答记录、签到日志持久化 |
| **网络通信** | httpx (异步连接池) + websockets | 高并发 HTTP 连接复用与 Faye WSS 动态截码 |

---

## 2. 核心业务模块与全流程细节

### 2.1 签到引擎（全协议并发与微扰动）

系统支持微助教目前所有的签到考核形式，并已实现 **100% 纯无锁极速全并发**：

```
[签到请求] ──► [并发确保 Session / 预热 Code] ──► [并发 HTTP 瞬间打卡] ──► [0.2s 极速解析 302 头] ──► [记录入库并回显]
```

1. **普通一键签到 (`/api/signin/normal`)**：
   - 教师发起无定位、无二维码的普通签到；
   - 第一阶段并发确保所有账号微助教会话已处于有效状态；
   - 第二阶段在同一个高并发 HTTPClient 连接池中瞬间向微助教接口发送打卡请求。
2. **GPS 定位签到 (`/api/signin/gps`)**：
   - 解决多账号同 IP、同经纬度聚集被风控的问题；
   - 引入 **5~10 米真实物理微扰动算法（Physics Jitter）**，在基准坐标周围随机施加独立微偏差，既保证全员通过地理围栏校验，又实现账号间坐标物理独立。
3. **极速扫码签到 (`/api/signin`)**：
   - **Code 鲜活预热**：点击扫码按钮时，后台预先并发为所有账号获取出炉 1~2 秒内的全新微信 Code（`force: true`）；
   - **302 Location 毫秒直捕**：扫码瞬间直连微助教 `s_qr_sign` 接口，关闭重定向，直接在 HTTP 302 Location 头中解析排名，杜绝加载渲染 SPA 网页，实现 **0.1~0.2 秒级打卡**。
4. **Faye WSS 动态二维码秒级监听 (`/api/signin/auto-qr`)**：
   - 针对课堂上 3~5 秒一变的动态二维码；
   - 直连 `wss://www.teachermate.com.cn/faye`，订阅课程频道；
   - 后台提前并发预热 Code，一旦 WebSocket 收到动态码推送事件，0 毫秒延迟触发全员并发打卡。
5. **全自动守护探测器 (`/api/signin/auto-detect-and-sign`)**：
   - 开启守护模式后，后台以 5 秒周期全并发探测所有账号的活跃签到；
   - 自动识别签到类型并自适应执行普通 / GPS / 动态码签到。

---

### 2.2 答题系统（多账号隔离与智能作答）

1. **全题型支持**：
   - **单选题 / 多选题 / 判断题**：自动解析选项内容，根据微助教官方协议封装为标准 JSON 载荷；
   - **填空题**：支持多空独立输入与已提交答案逐空对比；
   - **主观题**：支持富文本、文字作答、多张图片上传与音频文件提交。
2. **多账号作答记录绝对数据隔离**：
   - 严格禁止历史作答缓存跨账号污染未作答账号；
   - 账号的 `isAnswered`（是否已作答）和 `serverAnswer`（已提交作答）**100% 真实反映微助教官方返回的该账号自身状态**。
3. **已关闭题目支持补交**：
   - 移除了题目已关闭时的提交拦截，仅对“已提交过的题目”进行防篡改锁定；未作答题目即使已关闭仍可补交作答。
4. **标准答案纯真回显**：
   - 100% 严格只提取微助教官方在题目详情中明确标注的正确选项（`isCorrect: 1` / `isRight: 1` / `correct: true`）；
   - 若教师未公布答案，准确展示为“暂未公布”，绝不将其他账号的自选答案冒充为正确答案。

---

### 2.3 三层纵深主动保活引擎

系统采用三层定时轮换与现场并发自愈机制，实现免重复扫码与长期高可用：

```
┌─────────────────────────────────────────────────────────────┐
│                 三层后台主动保活引擎 (Keepalive)              │
├─────────────────────────────────────────────────────────────┤
│ Layer 1: 微信底层 Token 轮换 (每 90 分钟轮换，提前 30min 换新)   │
│ Layer 2: 微信小程序 Code 链路心跳实测 (20~30 分钟随机抖动探测) │
│ Layer 3: 微助教 Session Cookie 周期性刷新 (每 60 分钟巡检)      │
└─────────────────────────────────────────────────────────────┘
```

* **Layer 1（YYB 凭证轮换）**：微信 access_token 7200 秒到期前，每 90 分钟自动轮换，失败触发 5 分钟短退避复查；
* **Layer 2（小程序 Code 实测）**：开机立即实测，每 20~30 分钟随机抖动向微信端发起独立小程序 Code 申请，保持 MMTLS 长连接畅通；
* **Layer 3（微助教 Cookie 刷新）**：每 60 分钟巡检，当剩余有效期不足 2 小时时静默重新 OAuth 换票，维持 24 小时有效 Cookie。

---

### 2.4 Web 版服务器账号管理控制台

针对服务器运维与多账号管理，系统内置了现代响应式 Web 控制台：

* **安全鉴权入口**：`http://<服务器IP>:17521/070419` 或 `/admin070419`（普通根路径自动屏蔽隐藏）；
* **微信扫码添加新账号**：自动调用底层引擎生成 Base64 二维码，1.5 秒智能轮询授权状态，扫码成功后自动入库并生效；
* **彻底删除服务器端账号**：提供防误触二次确认弹窗，一键同步从 yyb-go 微信引擎、SQLite 数据库及本地磁盘头像缓存中物理彻底清除；
* **主账号切换 & 全量实测**：支持随时切换默认答题主账号，一键触发全员小程序 Code 连通性测试。

---

### 2.5 远端配置多源竞速拉取

App 客户端配置采用**多源全并发并行竞速（Racing Mode）**：
* 同时向 GitCode Raw、GitCode API、AtomGit Raw 等多个灾备镜像源发起并发拉取；
* 附带毫秒级时间戳参数（`?_t=Date.now()`）彻底穿透 CDN 缓存；
* 哪个镜像源最快返回合法 JSON，**0.1 秒内立即完成解析生效**，彻底解决配置同步延迟。

---

## 3. 项目工程目录结构说明

```
天商便捷助手/
├── app/                           # Uni-App 前端源码
│   ├── api/                       # HTTP 请求封装与远端配置拉取
│   │   └── request.js             # 竞速拉取 + 自动带 Key 请求拦截
│   ├── pages/                     # 前端页面
│   │   ├── index/index.vue        # 首页 (账号列表、打卡操作、全自动守护)
│   │   ├── quiz/courses.vue       # 课程列表与答题账号切换
│   │   ├── quiz/questions.vue     # 题目列表 (吸顶筛选栏与分页)
│   │   └── quiz/detail.vue        # 题目详情 (全题型交互与补交)
│   ├── store/index.js             # Vuex 全局状态管理
│   ├── App.vue                    # 应用生命周期与心跳轮询
│   ├── main.js                    # Uni-App 入口
│   └── manifest.json              # App 打包与权限配置
│
├── server/                        # FastAPI 业务调度后端
│   ├── main.py                    # 服务入口、路由挂载、Web 控制台入口
│   ├── config.py                  # 端口、API_KEY、数据库路径配置
│   ├── auth.py                    # X-API-Key 鉴权中间件
│   ├── data.db                    # SQLite 本地数据库 (自动生成)
│   ├── static/                    # Web 管理端静态页面
│   │   └── index.html             # 现代化 Web 控制台 SPA 页面
│   ├── models/                    # 数据库层
│   │   └── database.py            # SQLite 建表、凭证存储、日志记录
│   ├── routers/                   # 业务路由
│   │   ├── accounts.py            # 账号同步、扫码登录、物理删除
│   │   ├── signin.py              # 全并发签到、GPS扰动、WSS动态码、守护探测
│   │   ├── quiz.py                # 课程题目、答题提交、多账号隔离
│   │   └── upload.py              # 图片与音频上传代理
│   └── services/                  # 底层通信与业务引擎
│       ├── teachermate.py         # 微助教 Session 管理、纯无锁并发打卡
│       ├── yyb_service.py         # yyb-go HTTP API 高并发客户端
│       └── keepalive.py           # 三层主动保活引擎
│
└── PROJECT_DOCUMENTATION.md       # 本说明文档
```

---

## 4. 生产环境完美部署指南（Linux Ubuntu）

以下操作在 **Ubuntu 20.04 / 22.04 / 24.04 LTS** 服务器上经过完整验证。

### 4.1 基础环境与依赖安装

```bash
# 1. 更新系统包列表
sudo apt update && sudo apt upgrade -y

# 2. 安装 Python3、pip、虚拟环境及基础运维工具
sudo apt install -y python3 python3-pip python3-venv supervisor nginx curl lsof net-tools git
```

---

### 4.2 yyb-go 微信协议引擎配置与部署

```bash
# 1. 创建项目根目录
mkdir -p /home/ubuntu/tjcu-helper
cd /home/ubuntu/tjcu-helper

# 2. 将 yyb-go 可执行程序放置在目录中并赋予执行权限
chmod +x /home/ubuntu/tjcu-helper/yyb-go

# 3. 验证 yyb-go 是否能正常运行
/home/ubuntu/tjcu-helper/yyb-go -h
```

---

### 4.3 Python 后端 API 部署

```bash
# 1. 进入后端代码目录
cd /home/ubuntu/tjcu-helper/server

# 2. 创建并激活 Python 独立虚拟环境
python3 -m venv /home/ubuntu/tjcu-helper/venv
source /home/ubuntu/tjcu-helper/venv/bin/uvicorn

# 3. 安装所需 Python 核心依赖包
/home/ubuntu/tjcu-helper/venv/bin/pip install --upgrade pip
/home/ubuntu/tjcu-helper/venv/bin/pip install fastapi uvicorn httpx aiosqlite pydantic websockets python-multipart
```

---

### 4.4 Supervisor 生产守护进程配置

使用 Supervisor 托管两个核心服务，确保开机自启、崩溃自动拉起。

#### 1. 配置 `yyb-go` 微信引擎 (`/etc/supervisor/conf.d/tjcu-yyb.conf`)
```ini
[program:tjcu-yyb]
command=/home/ubuntu/tjcu-helper/yyb-go -port 8999
directory=/home/ubuntu/tjcu-helper
autostart=true
autorestart=true
startsecs=3
startretries=10
stderr_logfile=/home/ubuntu/tjcu-helper/logs/yyb.err.log
stdout_logfile=/home/ubuntu/tjcu-helper/logs/yyb.out.log
user=root
```

#### 2. 配置 `tjcu-api` 业务后端 (`/etc/supervisor/conf.d/tjcu-api.conf`)
```ini
[program:tjcu-api]
command=/home/ubuntu/tjcu-helper/venv/bin/uvicorn main:app --host 0.0.0.0 --port 17521 --workers 1
directory=/home/ubuntu/tjcu-helper/server
autostart=true
autorestart=true
startsecs=5
startretries=10
stderr_logfile=/home/ubuntu/tjcu-helper/logs/api.err.log
stdout_logfile=/home/ubuntu/tjcu-helper/logs/api.out.log
environment=API_KEY="tjcu-helper-2026",YYB_GO_URL="http://127.0.0.1:8999",DB_PATH="/home/ubuntu/tjcu-helper/server/data.db"
user=root
```

#### 3. 创建日志目录并启动服务
```bash
# 创建日志文件夹
mkdir -p /home/ubuntu/tjcu-helper/logs

# 加载 Supervisor 配置并启动
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart all

# 查看运行状态
sudo supervisorctl status
```

---

### 4.5 Nginx 反向代理与 SSL 配置（可选）

如果您希望绑定域名并通过 `80 / 443 (HTTPS)` 访问，可配置 Nginx：

在 `/etc/nginx/sites-available/tjcu.conf` 中添加：
```nginx
server {
    listen 80;
    server_name your-domain.com; # 替换为您自己的域名或服务器IP

    # 客户端最大请求体（支持图片/音频上传）
    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:17521;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # 支持 WebSocket 协议升级
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

启用配置并重载 Nginx：
```bash
sudo ln -sf /etc/nginx/sites-available/tjcu.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

---

### 4.6 云服务器防火墙与安全组设置

在腾讯云 / 阿里云 / 华为云控制台的 **安全组（Security Group）** 中放行以下端口入方向规则：

| 端口 | 协议 | 授权对象 | 说明 |
|---|---|---|---|
| **17521** | TCP | `0.0.0.0/0` | 后端 API 与 Web 管理控制台直连端口 |
| **80** | TCP | `0.0.0.0/0` | HTTP 端口（若配置 Nginx） |
| **443** | TCP | `0.0.0.0/0` | HTTPS 端口（若配置 SSL 证书） |

---

## 5. 日常运维与故障排查速查表

### 常用运维命令
```bash
# 1. 查看所有后台进程状态
sudo supervisorctl status

# 2. 重启微助教后端 API
sudo supervisorctl restart tjcu-api

# 3. 重启微信协议底层引擎
sudo supervisorctl restart tjcu-yyb

# 4. 查看后端实时运行日志
tail -n 100 -f /home/ubuntu/tjcu-helper/logs/api.out.log

# 5. 查看后端错误日志
tail -n 100 -f /home/ubuntu/tjcu-helper/logs/api.err.log

# 6. 检查端口监听情况
netstat -tulpn | grep 17521
```

### 访问与使用入口速览
* **Web 服务器账号管理控制台**：
  👉 `http://<服务器IP>:17521/070419` 或 `http://<服务器IP>:17521/admin070419`
* **后端健康检查接口**：
  👉 `http://<服务器IP>:17521/health`
* **API Key**：
  默认值为 `tjcu-helper-2026`（可在 `config.py` 或 Supervisor `environment` 中自定义）。
