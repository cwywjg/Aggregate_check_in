"""
天商便捷助手 - FastAPI 后端入口
"""
import asyncio
import uvicorn
from contextlib import suppress
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import PORT
from models.database import init_db, close_db
from routers import accounts, signin, quiz, upload
from services.keepalive import start_keepalive


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化数据库 + 启动保活引擎"""
    await init_db()
    print("[OK] Database initialized")
    
    # 启动后台保活引擎（永不阻塞，在后台运行）
    keepalive_task = asyncio.create_task(start_keepalive())
    print("[OK] Keepalive engine scheduled")
    
    yield
    
    # 关闭时取消保活任务 + 关闭数据库
    keepalive_task.cancel()
    with suppress(asyncio.CancelledError):
        await keepalive_task
    from routers.quiz import BACKGROUND_TASKS
    for task in list(BACKGROUND_TASKS):
        task.cancel()
    if BACKGROUND_TASKS:
        await asyncio.gather(*BACKGROUND_TASKS, return_exceptions=True)
    from services.yyb_service import yyb_service
    await yyb_service.close()
    await close_db()
    print("[BYE] Server shutdown")


app = FastAPI(
    title="天商便捷助手 API",
    description="微助教签到 + 答题自动化后端服务",
    version="2.1.0",
    lifespan=lifespan,
)

# CORS 配置（允许 App 跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import os
from fastapi.responses import HTMLResponse

# 注册路由
app.include_router(accounts.router)
app.include_router(accounts.avatar_router)
app.include_router(signin.router)
app.include_router(quiz.router)
app.include_router(upload.router)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/070419", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin070419", response_class=HTMLResponse, include_in_schema=False)
@app.get("/admin/070419", response_class=HTMLResponse, include_in_schema=False)
async def admin_dashboard():
    """Web 版服务器账号管理控制台入口（需带 070419 专属安全后缀）"""
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file):
        try:
            with open(index_file, "r", encoding="utf-8") as f:
                content = f.read()
            return HTMLResponse(content=content)
        except Exception as e:
            return HTMLResponse(content=f"<h3>加载管理页面失败: {e}</h3>", status_code=500)
    return HTMLResponse(content="<h3>天商便捷助手 API 服务运行中 (未找到 static/index.html)</h3>")


@app.get("/", include_in_schema=False)
@app.get("/admin", include_in_schema=False)
async def root_ping():
    """普通根路径屏蔽，返回基础状态"""
    return {
        "service": "天商便捷助手 API",
        "status": "running",
        "version": "2.1.0"
    }


@app.get("/health")
async def health():
    """健康检查 + 保活引擎状态（强健容错）"""
    try:
        from services.keepalive import get_keepalive_snapshot
        snapshot = get_keepalive_snapshot()
    except Exception:
        snapshot = {}

    from services.yyb_service import yyb_service
    try:
        yyb_response = await yyb_service.health()
        yyb_data = yyb_response.get("data", yyb_response) if isinstance(yyb_response, dict) else {}
        yyb_status = {
            "online": bool(yyb_data.get("ok")),
            "session_ttl_seconds": yyb_data.get("session_ttl_seconds"),
        }
    except Exception as exc:
        yyb_status = {"online": False, "message": str(exc)[:120]}

    return {
        "ok": True,
        "service": "天商便捷助手",
        "version": "2.1.0",
        "keepalive": {
            "enabled": True,
            "runtime": snapshot,
        },
        "yyb_engine": yyb_status,
    }



if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=False)
