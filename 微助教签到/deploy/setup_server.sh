#!/bin/bash
# ============================================================
# 天商便捷助手 - Ubuntu 服务器一键部署脚本
# 服务器: 150.109.94.62
# 包含: yyb-go (Go编译+运行) + Python FastAPI 后端
# ============================================================
set -e

SERVER_IP="150.109.94.62"
DEPLOY_DIR="/home/ubuntu/tjcu-helper"
YYB_PORT="8999"
API_PORT="17521"
API_KEY="tjcu-helper-2026"

echo "==== [1/6] 更新系统 & 安装基础依赖 ===="
apt-get update -qq
apt-get install -y wget curl git python3 python3-pip python3-venv \
    build-essential sqlite3 supervisor nginx ufw --no-install-recommends

echo "==== [2/6] 使用已验证的 Linux 预编译协议引擎 ===="
# deploy.zip 中的 yyb-go 由当前源码交叉编译，包含 24 小时 SessionTTL。

echo "==== [3/6] 创建目录结构 ===="
mkdir -p ${DEPLOY_DIR}/{yyb_go,server,logs}
mkdir -p ${DEPLOY_DIR}/yyb_go/resource/{db,avatars,qr,static,templates}

echo "==== [4/6] 准备预编译的 yyb-go ===="
if [ -f "${DEPLOY_DIR}/yyb_go/yyb-go" ]; then
    chmod +x ${DEPLOY_DIR}/yyb_go/yyb-go
    echo "yyb-go 执行权限已设置"
else
    echo "[ERROR] 未在 ${DEPLOY_DIR}/yyb_go/ 下找到预编译的 yyb-go 文件，请检查上传！"
    exit 1
fi

echo "==== [5/6] 安装 Python 依赖 ===="
if [ -d "${DEPLOY_DIR}/server" ]; then
    python3 -m venv ${DEPLOY_DIR}/venv
    ${DEPLOY_DIR}/venv/bin/pip install -q -r ${DEPLOY_DIR}/server/requirements.txt
    echo "Python 依赖安装完成"
fi

echo "==== [6/6] 配置 Supervisor 进程守护 ===="
cat > /etc/supervisor/conf.d/tjcu-yyb.conf << EOF
[program:tjcu-yyb]
command=${DEPLOY_DIR}/yyb_go/yyb-go -host 127.0.0.1 -port ${YYB_PORT} -resource-root ${DEPLOY_DIR}/yyb_go/resource
directory=${DEPLOY_DIR}/yyb_go
autostart=true
autorestart=true
startsecs=3
startretries=5
stderr_logfile=${DEPLOY_DIR}/logs/yyb-go.err.log
stdout_logfile=${DEPLOY_DIR}/logs/yyb-go.out.log
user=root
EOF

cat > /etc/supervisor/conf.d/tjcu-api.conf << EOF
[program:tjcu-api]
command=${DEPLOY_DIR}/venv/bin/uvicorn main:app --host 127.0.0.1 --port ${API_PORT} --workers 1
directory=${DEPLOY_DIR}/server
autostart=true
autorestart=true
startsecs=5
startretries=5
stderr_logfile=${DEPLOY_DIR}/logs/api.err.log
stdout_logfile=${DEPLOY_DIR}/logs/api.out.log
environment=API_KEY="${API_KEY}",YYB_GO_URL="http://127.0.0.1:${YYB_PORT}",DB_PATH="${DEPLOY_DIR}/server/data.db"
user=root
EOF

echo "==== 配置 Nginx 反向代理 ===="
cat > /etc/nginx/sites-available/tjcu-helper << EOF
server {
    listen 80;
    server_name 150.109.94.62;

    # Python FastAPI 后端
    location /api/ {
        proxy_pass http://127.0.0.1:${API_PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 60s;
        client_max_body_size 20m;
    }

    location /health {
        proxy_pass http://127.0.0.1:${API_PORT};
        proxy_set_header Host \$host;
    }

    # 健康检查
    location / {
        return 200 '{"service":"tjcu-helper","status":"ok"}';
        add_header Content-Type application/json;
    }
}
EOF

ln -sf /etc/nginx/sites-available/tjcu-helper /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

echo "==== 配置防火墙 ===="
ufw allow 22/tcp    # SSH
ufw allow 80/tcp    # Nginx (App 连接此端口)
# yyb-go (8999) 和 API (17521) 只监听 127.0.0.1，不对外暴露
ufw --force enable

echo ""
echo "================================================"
echo "  部署脚本执行完毕！"
echo "  下一步：上传代码后执行 supervisorctl reread && supervisorctl update && supervisorctl start all"
echo "  App 端服务器地址：http://150.109.94.62"
echo "================================================"
