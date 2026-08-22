"""
账号管理 + 凭证同步路由
"""
import json
from fastapi import APIRouter, Depends, Query
from auth import verify_api_key
from services.yyb_service import yyb_service
from services.teachermate import remove_tm_session
from models.database import (
    upsert_account_ext, get_all_account_exts, set_master_account,
    delete_account_ext, get_account_ext, get_all_keepalive_status,
    reset_keepalive_for_ref
)

router = APIRouter(prefix="/api/accounts", tags=["accounts"], dependencies=[Depends(verify_api_key)])
avatar_router = APIRouter(prefix="/api/accounts", tags=["accounts"])


@router.get("/sync")
async def sync_accounts():
    """同步全量账号 — App 启动时调用，返回所有账号+凭证+保活状态"""
    # 从 yyb-go 拿底层账号列表
    yyb_accounts = await yyb_service.get_accounts()
    # 从本地数据库拿扩展信息
    ext_list = await get_all_account_exts()
    ext_map = {e["ref"]: e for e in ext_list}

    accounts = []
    for acc in yyb_accounts:
        ref = acc.get("openid", "")
        ext = ext_map.get(ref, {})

        # 确保扩展记录存在
        if ref and ref not in ext_map:
            await upsert_account_ext(ref)
            ext = {"keepalive_status": "unknown", "last_keepalive_at": None, "keepalive_fail_count": 0}

        # 判断是否需要重扫：yyb_go 报告 expired 即刻标记
        yyb_status = acc.get("status", "unknown")
        yyb_alive = yyb_status == "alive"
        keepalive_status = ext.get("keepalive_status", "unknown")
        needs_rescan = (yyb_status == "expired") or (keepalive_status == "expired")

        accounts.append({
            "ref": ref,
            "nickname": acc.get("nickname"),
            "avatar_url": f"/api/accounts/{ref}/avatar",
            "is_master": bool(ext.get("is_master", 0)),
            "is_alive": yyb_alive,
            "keepalive_status": keepalive_status,
            "last_keepalive_at": ext.get("last_keepalive_at"),
            "last_probe_at": ext.get("last_probe_at"),
            "last_probe_status": ext.get("last_probe_status", "unknown"),
            "keepalive_fail_count": ext.get("keepalive_fail_count", 0),
            "needs_rescan": needs_rescan,
            "credentials": {
                "openid": ref,
                "uin": acc.get("uin"),
            },
            "updated_at": ext.get("updated_at"),
        })

    return {"accounts": accounts}


@router.get("/health")
async def accounts_health():
    """轻量级健康检查端点 — 仅返回保活状态，供 App 后台轮询"""
    statuses = await get_all_keepalive_status()

    # 同时从 yyb-go 获取实时 alive 状态
    try:
        yyb_accounts = await yyb_service.get_accounts()
        yyb_status_map = {a.get("openid", ""): a.get("status", "unknown") for a in yyb_accounts}
    except Exception:
        yyb_status_map = {}

    result = []
    for s in statuses:
        ref = s.get("ref", "")
        yyb_status = yyb_status_map.get(ref, "unknown")
        yyb_alive = yyb_status == "alive"
        keepalive_status = s.get("keepalive_status", "unknown")
        needs_rescan = (yyb_status == "expired") or (keepalive_status == "expired")

        result.append({
            "ref": ref,
            "is_master": bool(s.get("is_master", 0)),
            "is_alive": yyb_alive,
            "keepalive_status": keepalive_status,
            "last_keepalive_at": s.get("last_keepalive_at"),
            "last_probe_at": s.get("last_probe_at"),
            "last_probe_status": s.get("last_probe_status", "unknown"),
            "keepalive_fail_count": s.get("keepalive_fail_count", 0),
            "needs_rescan": needs_rescan,
        })

    return {"accounts": result}


@router.post("/probe")
async def trigger_probe_now():
    """手动/客户端即刻触发一次独立小程序 Code 有效性实测检验"""
    from services.keepalive import probe_mmtls_once
    snapshot = await probe_mmtls_once()
    return {"message": "全量有效性实测检验完成", "snapshot": snapshot}


@router.post("/qr")
async def create_qr():
    """创建扫码登录会话"""
    data = await yyb_service.create_qr_session(as_base64=True)
    return {"session_id": data.get("session_id"), "image_base64": data.get("image_base64")}


@router.get("/qr/{session_id}/poll")
async def poll_qr(session_id: str):
    """轮询扫码状态"""
    data = await yyb_service.poll_qr_session(session_id)
    return {"status": data.get("status")}


@router.post("/qr/{session_id}/confirm")
async def confirm_qr(session_id: str, target_ref: str = Query(default=None)):
    """
    确认扫码并保存账号
    
    target_ref: 可选，定向重扫时传入失效账号的 openid
                用于校验新扫码的微信号是否与目标一致
    """
    try:
        data = await yyb_service.confirm_qr_session(session_id)
    except Exception as e:
        print(f"[Accounts] confirm_qr error: {e}")
        return {"message": f"确认扫码失败：{str(e)}", "success": False}

    ref = data.get("openid", "")

    if not ref:
        return {"message": "扫码确认失败：未获取到账号信息", "success": False}

    # 定向重扫：校验 openid 一致性
    if target_ref:
        if ref != target_ref:
            return {
                "message": f"扫码的微信号与失效账号不一致！请用原来的微信号扫码。",
                "success": False,
                "expected_ref": target_ref[:12] + "...",
                "actual_ref": ref[:12] + "...",
            }
        # openid 一致 → 重置保活状态
        await reset_keepalive_for_ref(ref)
        # 更新扩展记录
        await upsert_account_ext(ref)
        return {
            "ref": ref,
            "nickname": data.get("nickname"),
            "message": "账号凭证已恢复！",
            "success": True,
            "rescan": True,
        }

    # 普通新增流程
    await upsert_account_ext(ref)

    # 如果是第一个账号，自动设为主账号
    all_exts = await get_all_account_exts()
    if len(all_exts) <= 1:
        await set_master_account(ref)

    # 新增的账号直接标记保活成功
    await reset_keepalive_for_ref(ref)

    return {
        "ref": ref,
        "nickname": data.get("nickname"),
        "message": "账号添加成功",
        "success": True,
    }


@router.put("/{ref}/master")
async def set_master(ref: str):
    """设为主账号"""
    await set_master_account(ref)
    return {"message": f"已将 {ref} 设为主账号"}


import os
AVATARS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "avatars")
os.makedirs(AVATARS_DIR, exist_ok=True)


@router.delete("/{ref}")
async def delete_account(ref: str):
    """删除账号"""
    await yyb_service.delete_account(ref)
    await delete_account_ext(ref)
    remove_tm_session(ref)  # 清理内存中的 TM session
    # 清理头像缓存
    avatar_path = os.path.join(AVATARS_DIR, f"{ref}.jpg")
    if os.path.exists(avatar_path):
        try:
            os.remove(avatar_path)
        except Exception:
            pass
    return {"message": "账号已删除"}


@router.post("/refresh")
async def refresh_accounts():
    """刷新所有账号状态"""
    result = await yyb_service.refresh_account()
    return result


@avatar_router.get("/{ref}/avatar")
async def get_avatar(ref: str):
    """代理并磁盘持久缓存头像"""
    import httpx
    from fastapi.responses import Response, FileResponse
    
    cache_file = os.path.join(AVATARS_DIR, f"{ref}.jpg")
    if os.path.exists(cache_file):
        return FileResponse(
            cache_file, 
            media_type="image/jpeg", 
            headers={"Cache-Control": "public, max-age=31536000, immutable"}
        )

    url = yyb_service.get_avatar_url(ref)
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, follow_redirects=True, timeout=10)
            if r.status_code == 200:
                try:
                    with open(cache_file, "wb") as f:
                        f.write(r.content)
                except Exception as save_err:
                    print(f"[Avatar] Save disk cache error: {save_err}")
                return Response(
                    content=r.content, 
                    media_type=r.headers.get("content-type", "image/jpeg"),
                    headers={"Cache-Control": "public, max-age=31536000, immutable"}
                )
        except Exception as e:
            print(f"Failed to proxy avatar: {e}")
    return Response(status_code=404)
