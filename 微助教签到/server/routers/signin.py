"""
批量签到与全协议自动化签到路由
"""
import asyncio
import time
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from auth import verify_api_key
from services.yyb_service import yyb_service
from services.teachermate import (
    do_signin,
    do_normal_signin,
    do_gps_signin,
    get_active_signs,
    listen_faye_qr_and_sign,
    PRE_CODES,
    TEACHERMATE_APP_ID,
)
from models.database import log_signin, get_signin_history, get_all_account_exts

router = APIRouter(prefix="/api/signin", tags=["signin"], dependencies=[Depends(verify_api_key)])

_NICKNAME_CACHE: dict[str, str] = {}
_NICKNAME_CACHE_AT: float = 0


async def get_fast_nickname_map() -> dict[str, str]:
    """快速获取昵称字典（1分钟内存缓存，杜绝签到后阻塞调用 yyb-go API）"""
    global _NICKNAME_CACHE, _NICKNAME_CACHE_AT
    now = time.time()
    if _NICKNAME_CACHE and (now - _NICKNAME_CACHE_AT < 60):
        return _NICKNAME_CACHE
    try:
        yyb_accounts = await yyb_service.get_accounts()
        _NICKNAME_CACHE = {a.get("openid", ""): a.get("nickname", "未知") for a in yyb_accounts if a.get("openid")}
        _NICKNAME_CACHE_AT = now
    except Exception:
        pass
    return _NICKNAME_CACHE


async def resolve_target_refs(account_refs: list[str]) -> list[str]:
    """解析目标账号 openid 列表"""
    if "all" in account_refs or not account_refs:
        name_map = await get_fast_nickname_map()
        refs = list(name_map.keys())
    else:
        refs = account_refs
    return list(dict.fromkeys(ref for ref in refs if ref))


class PrepareRequest(BaseModel):
    account_refs: list[str] = Field(default_factory=lambda: ["all"])
    force: bool = False


@router.post("/prepare")
async def prepare_signin(req: PrepareRequest):
    """确保所有账号的微信 Code 100% 获取完毕并放入内存，确保扫码后一秒内完成签到"""
    refs = await resolve_target_refs(req.account_refs)
    if not refs:
        return {"success": False, "message": "无可用账号", "ready": 0, "total": 0, "codes": {}}

    now = time.time()

    async def fetch_single_code(ref: str):
        try:
            cached = PRE_CODES.get(ref)
            if not req.force and cached and (now - cached.get("timestamp", 0) < 120) and cached.get("code"):
                return ref, cached["code"], None
            code = await yyb_service.get_code(ref, TEACHERMATE_APP_ID)
            PRE_CODES[ref] = {
                "code": code,
                "timestamp": time.time(),
                "error": None
            }
            return ref, code, None
        except Exception as e:
            err_msg = str(e)
            if "expired" in err_msg or "re-scan" in err_msg or "409" in err_msg:
                err_msg = "账号登录已过期，需重新扫码"
                try:
                    from models.database import mark_account_needs_rescan
                    await mark_account_needs_rescan(ref, True)
                except Exception:
                    pass
            print(f"[Prepare] ⚠️ 账号 {ref[:8]}... 预热 Code 失败: {err_msg}")
            PRE_CODES[ref] = {
                "code": None,
                "timestamp": time.time(),
                "error": err_msg
            }
            return ref, None, err_msg

    async def warm_http_connection():
        try:
            from services.teachermate import get_signin_http_client, TEACHERMATE_SIGNIN_HOST
            client = get_signin_http_client()
            await client.get(f"{TEACHERMATE_SIGNIN_HOST}/favicon.ico")
        except Exception:
            pass

    tasks = [fetch_single_code(ref) for ref in refs] + [warm_http_connection()]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    ready_codes = {}
    ready = 0
    for r in results:
        if isinstance(r, tuple) and r[1]:
            ready_codes[r[0]] = r[1]
            ready += 1

    failed = len(refs) - ready

    return {
        "success": True,
        "message": f"已就绪 {ready}/{len(refs)} 个账号凭证" if failed == 0 else f"{ready} 个就绪，{failed} 个账号已失效",
        "ready": ready,
        "failed": failed,
        "total": len(refs),
        "codes": ready_codes
    }


# ── 1. 活跃签到全并发探测接口 ──

@router.get("/active")
async def check_active_signs(ref: str = None, refs: str = None):
    """
    全并发查询活跃签到活动：
    支持单个 ref、逗号分隔的 refs、或自动探测所有有效候选账号。
    全部账号并行并发发送探测请求，0 秒等待，聚合全部活跃签到！
    """
    if refs:
        target_refs = [r.strip() for r in refs.split(",") if r.strip()]
    elif ref:
        target_refs = [ref.strip()]
    else:
        from routers.quiz import get_candidate_probe_refs
        target_refs = await get_candidate_probe_refs()

    if not target_refs:
        return {"has_active": False, "active_signs": [], "message": "无可用探针账号"}

    # 全并发并行向微助教发起探测
    tasks = [get_active_signs(r) for r in target_refs]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_signs = []
    seen_sign_keys = set()

    for r, res in zip(target_refs, raw_results):
        if isinstance(res, list):
            for sign in res:
                if isinstance(sign, dict):
                    key = (sign.get("courseId"), sign.get("signId"))
                    if key not in seen_sign_keys and sign.get("courseId") and sign.get("signId"):
                        seen_sign_keys.add(key)
                        all_signs.append(sign)

    has_active = len(all_signs) > 0

    # 提取所有探测账号的有效微助教 Session，直接下发给手机本地直连打卡
    from services.teachermate import get_tm_session
    sessions_map = {}
    for r in target_refs:
        sess = get_tm_session(r)
        if sess.is_valid:
            sessions_map[r] = {
                "session": sess.session_cookie,
                "session_sig": sess.session_sig
            }

    return {
        "has_active": has_active,
        "count": len(all_signs),
        "active_signs": all_signs,
        "latest": all_signs[0] if has_active else None,
        "sessions": sessions_map
    }


# ── 2. 普通一键签到（全并发执行） ──

class NormalSigninRequest(BaseModel):
    course_id: int
    sign_id: int
    account_refs: list[str] = Field(default_factory=lambda: ["all"])


@router.post("/normal")
async def batch_normal_signin(req: NormalSigninRequest):
    """批量执行普通签到（无需定位与二维码，全并发秒级打卡）"""
    refs = await resolve_target_refs(req.account_refs)
    if not refs:
        return {"results": [], "total": 0, "success_count": 0, "message": "没有可用账号"}

    # 第一阶段：并发确保所有账号微助教会话已处于有效状态，消除登录时差
    from services.teachermate import get_tm_session
    await asyncio.gather(*[get_tm_session(ref).ensure_session() for ref in refs], return_exceptions=True)

    # 第二阶段：全并发瞬间向微助教服务器发送打卡请求
    tasks = [do_normal_signin(ref, req.course_id, req.sign_id) for ref in refs]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    nickname_map = await get_fast_nickname_map()

    final_results = []
    success_count = 0
    for ref, res in zip(refs, raw_results):
        if isinstance(res, BaseException):
            item = {"ref": ref, "success": False, "message": str(res)}
        else:
            item = res
        item["nickname"] = nickname_map.get(ref, "未知")
        final_results.append(item)
        if item.get("success"):
            success_count += 1
        await log_signin(ref, f"normal:{req.course_id}:{req.sign_id}", item.get("success", False), item.get("message", ""))

    return {
        "results": final_results,
        "total": len(final_results),
        "success_count": success_count,
        "course_id": req.course_id,
        "sign_id": req.sign_id,
        "mode": "normal"
    }


# ── 3. GPS 定位签到（全并发执行） ──

class GPSSigninRequest(BaseModel):
    course_id: int
    sign_id: int
    lat: str = "39.18252"
    lon: str = "117.11943"
    account_refs: list[str] = Field(default_factory=lambda: ["all"])


@router.post("/gps")
async def batch_gps_signin(req: GPSSigninRequest):
    """批量执行带随机散布扰动的 GPS 定位签到（全并发秒级打卡）"""
    refs = await resolve_target_refs(req.account_refs)
    if not refs:
        return {"results": [], "total": 0, "success_count": 0, "message": "没有可用账号"}

    # 第一阶段：并发确保所有账号微助教会话已处于有效状态，消除登录时差
    from services.teachermate import get_tm_session
    await asyncio.gather(*[get_tm_session(ref).ensure_session() for ref in refs], return_exceptions=True)

    # 第二阶段：全并发瞬间向微助教服务器发送打卡请求
    tasks = [do_gps_signin(ref, req.course_id, req.sign_id, req.lat, req.lon) for ref in refs]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    nickname_map = await get_fast_nickname_map()

    final_results = []
    success_count = 0
    for ref, res in zip(refs, raw_results):
        if isinstance(res, BaseException):
            item = {"ref": ref, "success": False, "message": str(res)}
        else:
            item = res
        item["nickname"] = nickname_map.get(ref, "未知")
        final_results.append(item)
        if item.get("success"):
            success_count += 1
        await log_signin(ref, f"gps:{req.course_id}:{req.sign_id}", item.get("success", False), item.get("message", ""))

    return {
        "results": final_results,
        "total": len(final_results),
        "success_count": success_count,
        "course_id": req.course_id,
        "sign_id": req.sign_id,
        "base_lat": req.lat,
        "base_lon": req.lon,
        "mode": "gps"
    }


# ── 4. 扫码签到（手动扫码与 WSS 动态监听） ──

class SigninRequest(BaseModel):
    extra: str                          # 签到二维码中的 extra hash
    account_refs: list[str] = Field(default_factory=lambda: ["all"])


@router.post("")
async def batch_signin(req: SigninRequest):
    """手动扫码/相册选图批量签到"""
    refs = await resolve_target_refs(req.account_refs)
    if not refs:
        return {"results": [], "total": 0, "success_count": 0, "message": "没有可用账号"}

    tasks = [do_signin(ref, req.extra) for ref in refs]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    nickname_map = await get_fast_nickname_map()

    final_results = []
    success_count = 0
    for ref, result in zip(refs, raw_results):
        if isinstance(result, BaseException):
            item = {"ref": ref, "success": False, "message": str(result)}
        else:
            item = result
        item["nickname"] = nickname_map.get(ref, "未知")
        final_results.append(item)
        if item.get("success"):
            success_count += 1
        await log_signin(item["ref"], req.extra, item.get("success", False), item.get("message", ""))

    return {
        "results": final_results,
        "total": len(final_results),
        "success_count": success_count,
        "mode": "qr_manual"
    }


class BatchLogRequest(BaseModel):
    results: list[dict]
    extra: str


@router.post("/batch-log")
async def batch_log_signin_results(req: BatchLogRequest):
    """客户端本地直连极速打卡完成后，异步同步打卡日志到服务端"""
    for r in req.results:
        ref = r.get("ref", "")
        success = bool(r.get("success", False))
        message = r.get("message", "")
        if ref:
            await log_signin(ref, req.extra, success, message)
    return {"ok": True}


class AutoQRRequest(BaseModel):
    course_id: int
    sign_id: int
    timeout_sec: int = 35
    account_refs: list[str] = Field(default_factory=lambda: ["all"])


@router.post("/auto-qr")
async def auto_qr_listen_and_sign(req: AutoQRRequest):
    """Faye WSS 实时监听动态二维码并秒级并发打卡"""
    refs = await resolve_target_refs(req.account_refs)
    if not refs:
        return {"success": False, "message": "没有可用账号"}

    result = await listen_faye_qr_and_sign(req.course_id, req.sign_id, refs, req.timeout_sec)
    if result.get("success") and "results" in result:
        yyb_accounts = await yyb_service.get_accounts()
        nickname_map = {a.get("openid", ""): a.get("nickname", "未知") for a in yyb_accounts}
        for r in result["results"]:
            r["nickname"] = nickname_map.get(r["ref"], "未知")
            await log_signin(r["ref"], result.get("extra", f"qr:{req.course_id}:{req.sign_id}"), r.get("success", False), r.get("message", ""))

    return result


# ── 5. 全自动守护一站式探测与自动签到 ──

class AutoDetectRequest(BaseModel):
    lat: str = "39.18252"
    lon: str = "117.11943"
    account_refs: list[str] = Field(default_factory=lambda: ["all"])


@router.post("/auto-detect-and-sign")
async def auto_detect_and_sign(req: AutoDetectRequest):
    """
    全自动守护探测器：
    1. 探测当前是否有活跃签到；
    2. 若有，自动判别签到类型（普通 / GPS / 动态二维码）；
    3. 全自动匹配执行对应模式打卡并返回结果。
    """
    refs = await resolve_target_refs(req.account_refs)
    if not refs:
        return {"has_active": False, "executed": False, "message": "没有可用账号"}

    # 1. 全并发探测所有账号的活跃签到
    tasks = [get_active_signs(ref) for ref in refs]
    raw_results = await asyncio.gather(*tasks, return_exceptions=True)

    all_signs = []
    seen_sign_keys = set()
    for ref, res in zip(refs, raw_results):
        if isinstance(res, list):
            for sign in res:
                if isinstance(sign, dict):
                    key = (sign.get("courseId"), sign.get("signId"))
                    if key not in seen_sign_keys and sign.get("courseId") and sign.get("signId"):
                        seen_sign_keys.add(key)
                        all_signs.append(sign)

    if not all_signs:
        return {
            "has_active": False,
            "executed": False,
            "message": "当前未探测到活跃签到活动"
        }

    sign_item = all_signs[0]
    course_id = sign_item.get("courseId")
    sign_id = sign_item.get("signId")
    is_gps = sign_item.get("isGPS", 0)
    is_qr = sign_item.get("isQR", 0)
    course_name = sign_item.get("name", "微助教课程签到")

    if not course_id or not sign_id:
        return {"has_active": True, "executed": False, "message": "探测到签到但缺少 courseId/signId"}

    # 2. 判型并执行
    if is_gps == 0 and is_qr == 0:
        # 普通签到
        normal_res = await batch_normal_signin(NormalSigninRequest(
            course_id=course_id,
            sign_id=sign_id,
            account_refs=refs
        ))
        normal_res["has_active"] = True
        normal_res["executed"] = True
        normal_res["course_name"] = course_name
        normal_res["message"] = f"已自动完成【普通签到】: {course_name}"
        return normal_res

    elif is_gps == 1:
        # GPS 定位签到
        gps_res = await batch_gps_signin(GPSSigninRequest(
            course_id=course_id,
            sign_id=sign_id,
            lat=req.lat,
            lon=req.lon,
            account_refs=refs
        ))
        gps_res["has_active"] = True
        gps_res["executed"] = True
        gps_res["course_name"] = course_name
        gps_res["message"] = f"已自动完成【GPS定位签到】: {course_name}"
        return gps_res

    elif is_qr == 1:
        # 动态二维码签到：尝试 WSS 实时监听 15 秒
        ws_res = await auto_qr_listen_and_sign(AutoQRRequest(
            course_id=course_id,
            sign_id=sign_id,
            timeout_sec=15,
            account_refs=refs
        ))
        ws_res["has_active"] = True
        ws_res["course_id"] = course_id
        ws_res["sign_id"] = sign_id
        ws_res["course_name"] = course_name
        ws_res["is_qr"] = 1
        if ws_res.get("success"):
            ws_res["executed"] = True
            ws_res["need_manual_scan"] = False
            ws_res["message"] = f"已通过 WSS 自动截获动态码并完成签到: {course_name}"
        else:
            ws_res["executed"] = False
            ws_res["need_manual_scan"] = True
            ws_res["message"] = f"检测到二维码签到【{course_name}】，15秒内未在频道捕获到动态码，请立即手动扫码！"
        return ws_res

    return {
        "has_active": True,
        "executed": False,
        "course_name": course_name,
        "message": f"未知的签到类型 (isGPS={is_gps}, isQR={is_qr})"
    }


@router.get("/history")
async def signin_history(limit: int = 50):
    """获取签到历史"""
    logs = await get_signin_history(limit)
    return {"logs": logs}

