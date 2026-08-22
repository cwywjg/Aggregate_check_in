# 雨课堂服务 PM2 部署说明

目标目录固定为：

```text
/home/ubuntu/ykt_server
```

## 1. 系统依赖

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nodejs npm unzip
sudo npm install -g pm2
```

如果以前启用过 systemd 版本，先停掉，不能让 systemd 和 PM2 同时占用 5000：

```bash
sudo systemctl disable --now ykt-api ykt-ws ykt-monitor 2>/dev/null || true
```

## 2. 上传文件

```bash
sudo mkdir -p /home/ubuntu/ykt_server
sudo chown -R ubuntu:ubuntu /home/ubuntu/ykt_server
```

将服务压缩包上传到 `/home/ubuntu/ykt_server`，然后：

```bash
sudo -iu ubuntu
cd /home/ubuntu/ykt_server
unzip -o ykt-server-pm2-v2.6.1.zip
bash deploy/install_pm2.sh
```

## 3. 文件配置

唯一主要配置文件：

```text
/home/ubuntu/ykt_server/ykt.env
```

修改：

```bash
nano /home/ubuntu/ykt_server/ykt.env
```

管理员密码：

```ini
YKT_ADMIN_KEY=CWYWJG
YKT_API_BASE=https://changjiang.yuketang.cn
YKT_WS_URL=wss://changjiang.yuketang.cn/wsapp/
```

如果要同时预存 Gemini、OpenAI、NVIDIA、SiliconFlow 多套配置，推荐让统一覆盖项保持为空：

```ini
AI_API_KEY=
AI_BASE_URL=
AI_MODELS=
```

然后分别填写 `GEMINI_*`、`OPENAI_*`、`NVIDIA_*`、`SILICONFLOW_*`。

### 推荐：Gemma + Qwen 双模型一分钟保险链

```ini
AI_PROVIDER=nvidia
AI_API_KEY=
AI_BASE_URL=
AI_MODELS=
AI_ROUTES=nvidia|google/gemma-4-31b-it;siliconflow|Qwen/Qwen3.5-27B

NVIDIA_API_KEY=你的_NVIDIA_Key
SILICONFLOW_API_KEY=你的_SiliconFlow_Key

AI_THINKING_FIRST=1
AI_THINKING_TIMEOUT=25
AI_THINKING_HEDGE_DELAY=3
AI_THINKING_MAX_TOKENS=4096
AI_ROUTE_TIMEOUT=8
AI_ROUTE_CYCLES=2
AI_TOTAL_TIMEOUT=54
AI_MAX_RETRIES=0

YKT_SUBMIT_PREFERRED_DELAY=20
YKT_AI_THINKING_CUTOFF=25
YKT_SUBMIT_HARD_LIMIT=60
YKT_SUBMIT_RESERVE=6
YKT_AI_TIMEOUT=55
```

实际流程：

1. 题目下发后立即启动 NVIDIA Thinking。
2. 3 秒仍未完成，自动并发启动 SiliconFlow Thinking，规避 NVIDIA 排队。
3. 任一 Thinking 在第 25 秒前完成则采用其答案；20 秒前完成会等到第 20 秒提交。
4. 第 25 秒仍无结果，同时启动 SiliconFlow Fast 和 NVIDIA Fast；一致时直接采用，
   不一致时采用主路由 NVIDIA。
5. 如果只有备用 Fast 路由成功而 NVIDIA 仍在排队，先保存备用答案并重试一次
   NVIDIA；仍不可用才采用备用答案。
6. 得到合法答案立即批量提交；整个任务以题目下发后 60 秒为硬上限，并为
   HTTP 批量提交预留 6 秒。

### Gemma-4 三小时连通性检测

`ykt-monitor` 启动后会立即用 NVIDIA `google/gemma-4-31b-it` 发送一次
`你好`，之后每 3 小时重复一次。这个探针只测 Gemma-4，不会由 Qwen
兜底，因此能够真实反映默认模型是否可用。

```ini
YKT_AI_HEALTH_INTERVAL=10800
YKT_AI_HEALTH_TIMEOUT=30
YKT_AI_HEALTH_HISTORY_LIMIT=100
```

结果保存在：

```text
/home/ubuntu/ykt_server/data/ai_health.json
```

前端 AI 答题日志页会从 `/api/ai/history` 读取最新记录。检测正常时显示绿色
`成功`，并显示检测时间和耗时。也可以单独查询：

```bash
curl -H 'Authorization: 你的专属密钥' \
  http://127.0.0.1:5000/api/ai/health
```

### Gemini

```ini
AI_PROVIDER=gemini
AI_API_KEY=你的_Gemini_Key
AI_BASE_URL=
AI_MODELS=gemini-2.5-flash,gemini-2.0-flash
```

### OpenAI

```ini
AI_PROVIDER=openai
AI_API_KEY=你的_OpenAI_Key
AI_BASE_URL=https://api.openai.com/v1
AI_MODELS=gpt-4o
```

### NVIDIA NIM

NVIDIA NIM 使用 OpenAI-compatible 接口，不需要额外 Python SDK：

```ini
AI_PROVIDER=nvidia
AI_API_KEY=你的_NVIDIA_Key
AI_BASE_URL=https://integrate.api.nvidia.com/v1
AI_MODELS=google/gemma-4-31b-it
AI_ENABLE_THINKING=0
AI_TEMPERATURE=0.1
AI_TOP_P=0.95
AI_MAX_TOKENS=1024
```

`google/gemma-4-31b-it` 支持图片。课堂答题推荐关闭 thinking：本项目的
6 张图片题实测中，正常请求约 3.3–5.4 秒；开启 thinking 的平均耗时约
18.8 秒，不适合短倒计时抢答。

### SiliconFlow / Qwen3.5

项目已内置 SiliconFlow 渠道和 `Qwen/Qwen3.5-27B` 多模态消息格式：

```ini
AI_PROVIDER=siliconflow
AI_API_KEY=
AI_BASE_URL=
AI_MODELS=

SILICONFLOW_API_KEY=你的新_SiliconFlow_Key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODELS=Qwen/Qwen3.5-27B
SILICONFLOW_JSON_MODE=auto
SILICONFLOW_ENABLE_THINKING=0
SILICONFLOW_IMAGE_DETAIL=low
```

课堂短倒计时推荐 `SILICONFLOW_ENABLE_THINKING=0`。本项目六张图片题快速模式
实测平均约 2.38 秒，5/6 正确；thinking 模式明显更慢，而且需要显著提高
`AI_MAX_TOKENS` 才能保证生成最终 JSON。

### 其他 OpenAI-compatible 服务

```ini
AI_PROVIDER=compatible
AI_API_KEY=供应商密钥
AI_BASE_URL=https://供应商地址/v1
AI_MODELS=模型名
```

切换配置后：

```bash
cd /home/ubuntu/ykt_server
pm2 restart ecosystem.config.cjs --update-env
```

## 4. 开机启动

下面命令只执行一次：

```bash
sudo env PATH=$PATH:/usr/bin pm2 startup systemd -u ubuntu --hp /home/ubuntu
sudo -iu ubuntu pm2 save
```

## 5. 管理命令

```bash
pm2 status
pm2 logs
pm2 logs ykt-api
pm2 logs ykt-ws
pm2 logs ykt-monitor
pm2 restart ecosystem.config.cjs --update-env
pm2 save
```

服务状态：

```bash
curl http://127.0.0.1:5000/api/status
curl http://服务器IP:5000/api/status
pm2 status
pm2 logs --lines 100
```

服务器安全组和 UFW 需要开放 TCP 5000：

```bash
sudo ufw allow 5000/tcp
```

## 6. 目录结构

```text
/home/ubuntu/ykt_server/
├── api_server.py
├── ykt_ws_engine.py
├── ykt_monitor.py
├── ai_solver.py
├── safe_json_store.py
├── requirements.txt
├── ecosystem.config.cjs
├── ykt.env
├── venv/
├── data/
│   └── ai_health.json
├── logs/
│   └── monitor.out.log
└── deploy/
```

长期备份重点是：

```text
/home/ubuntu/ykt_server/ykt.env
/home/ubuntu/ykt_server/data/
```

## 7. v2.6.1 上线前自检

```bash
cd /home/ubuntu/ykt_server
venv/bin/python -m py_compile \
  api_server.py ai_solver.py ykt_ws_engine.py ykt_monitor.py safe_json_store.py

curl -s http://127.0.0.1:5000/api/status
curl -s -H 'Authorization: CWYWJG' \
  http://127.0.0.1:5000/api/admin/verify
```

`/api/status` 的 `data.version` 必须是 `2.6.1`。首次配置 AI Key 后执行：

```bash
curl -s -H 'Authorization: 你的专属密钥' \
  http://127.0.0.1:5000/api/ai/health
```

本项目按要求继续使用 HTTP IP 地址；这意味着同一路径上的网络设备能看到
`Authorization` 和同步账号数据。至少应只开放固定来源 IP，或通过安全组/VPN
限制 TCP 5000 的访问范围。
