#!/usr/bin/env pwsh
# ============================================================
# 天商便捷助手 - 从 Windows 上传代码到 Ubuntu 服务器
# 需要: ssh, scp (Windows 10+ 自带)
# ============================================================

$SERVER = "150.109.94.62"
$SERVER_USER = "ubuntu"
$DEPLOY_DIR = "/home/ubuntu/tjcu-helper"
$LOCAL_BASE = "d:\ANDRIOD\天商便捷助手"

Write-Host "==== [1/4] 创建服务器目录结构 ====" -ForegroundColor Cyan
ssh "${SERVER_USER}@${SERVER}" "mkdir -p ${DEPLOY_DIR}/yyb_go ${DEPLOY_DIR}/server ${DEPLOY_DIR}/logs"

Write-Host ""
Write-Host "==== [2/4] 上传 yyb-go 可执行文件与资源 ====" -ForegroundColor Cyan
# 直接上传你编译好的 Ubuntu 二进制文件和资源包
scp "yyb_go\yyb-go" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/yyb_go/"
scp -r "yyb_go\resource" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/yyb_go/"

Write-Host ""
Write-Host "==== [3/4] 上传 Python 后端 ====" -ForegroundColor Cyan
scp -r "server\models" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"
scp -r "server\routers" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"
scp -r "server\services" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"
scp "server\main.py" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"
scp "server\config.py" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"
scp "server\auth.py" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"
scp "server\requirements.txt" "${SERVER_USER}@${SERVER}:${DEPLOY_DIR}/server/"

Write-Host ""
Write-Host "==== [4/4] 上传并执行部署脚本 ====" -ForegroundColor Cyan
scp "deploy\setup_server.sh" "${SERVER_USER}@${SERVER}:/tmp/setup_server.sh"
ssh "${SERVER_USER}@${SERVER}" "chmod +x /tmp/setup_server.sh && sudo bash /tmp/setup_server.sh"

Write-Host ""
Write-Host "==== 上传完毕！正在启动服务 ====" -ForegroundColor Green
ssh "${SERVER_USER}@${SERVER}" @"
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart all
sleep 2
sudo supervisorctl status
"@

Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Deploy complete!" -ForegroundColor Green
Write-Host "  App server URL: http://150.109.94.62" -ForegroundColor Yellow
Write-Host "  API Key: tjcu-helper-2026" -ForegroundColor Yellow
Write-Host "======================================" -ForegroundColor Green
