"""
微助教签到与答题服务 - 后端配置模块
===========================================
支持通过系统环境变量或 .env 文件覆盖配置，生产环境请设置自定义 API_KEY。
"""
import os

# ============================ 依赖服务与网络地址 ============================
# yyb-go 微信协议底层服务地址（同机部署默认 127.0.0.1:8999）
YYB_GO_URL = os.getenv("YYB_GO_URL", "http://127.0.0.1:8999")

# 微助教官方核心接口域名与微信小程序 AppID
TEACHERMATE_BASE = "https://v18.teachermate.cn"
TEACHERMATE_WECHAT_API = f"{TEACHERMATE_BASE}/wechat-api"
TEACHERMATE_APP_ID = "wxa153455f3ef1d9f9"

# 签到回调与重定向主机地址
TEACHERMATE_SIGNIN_HOST = "https://www.teachermate.com.cn"

# ============================ 安全鉴权与存储 ============================
# API 接口鉴权密钥（生产部署时请通过环境变量 API_KEY 注入强密码）
API_KEY = os.getenv("API_KEY", "your-secure-api-key-here")

# SQLite 数据库持久化文件路径
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "data.db"))

# 服务监听端口
PORT = int(os.getenv("PORT", "17521"))
