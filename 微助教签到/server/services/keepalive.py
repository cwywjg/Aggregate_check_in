"""
后台保活引擎。

三层策略：定时轮换 YYB OAuth 凭证、周期性实测 MMTLS/getCode 链路、按服务端
Cookie 到期时间刷新微助教 Session。所有环节仍保留业务请求时的按需自愈。
"""
import asyncio
import time
import random
import traceback

from services.yyb_service import yyb_service
from services.teachermate import get_tm_session
from models.database import (
    get_all_account_exts, get_account_ext,
    update_keepalive_status, update_probe_status, upsert_account_ext,
)


# YYB access_token 抓包/接口返回 expires_in=7200，提前半小时轮换。
YYB_REFRESH_INTERVAL = 90 * 60
YYB_RETRY_INTERVAL = 5 * 60
TM_SESSION_REFRESH_INTERVAL = 60 * 60
TM_SESSION_REFRESH_AHEAD = 2 * 3600
STARTUP_DELAY = 1
MAX_FAIL_BEFORE_EXPIRED = 3
MAX_REFRESH_CONCURRENCY = 4

_state = {
    "started_at": None,
    "yyb": {},
    "mmtls": {},
    "teachermate": {},
}


def _record_state(name: str, **values):
    _state[name] = {**_state.get(name, {}), **values}


def get_keepalive_snapshot() -> dict:
    return {
        "started_at": _state["started_at"],
        "yyb": dict(_state["yyb"]),
        "mmtls": dict(_state["mmtls"]),
        "teachermate": dict(_state["teachermate"]),
    }


def _parse_refresh_status(result: dict, ref: str) -> str:
    data = result.get("data") if isinstance(result, dict) else None
    if isinstance(data, dict):
        return str(data.get("status", "unknown"))
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and (item.get("openid") == ref or len(data) == 1):
                return str(item.get("status", "unknown"))
    return "unknown"


async def _keepalive_single_account(acc: dict) -> dict:
    ref = acc.get("openid", "")
    nickname = acc.get("nickname") or (ref[:10] if ref else "?")
    if not ref:
        return {"ref": "", "success": False, "message": "missing ref"}

    ext = await get_account_ext(ref)
    if not ext:
        await upsert_account_ext(ref)
        ext = await get_account_ext(ref) or {}

    try:
        result = await yyb_service.refresh_account(ref)
        status = _parse_refresh_status(result, ref)
        if status == "alive":
            await update_keepalive_status(ref, "alive")
            print(f"[Keepalive/YYB] ✓ {nickname} 凭证轮换成功")
            return {"ref": ref, "success": True, "message": "alive"}

        fail_count = (ext.get("keepalive_fail_count", 0) or 0) + 1
        new_status = "expired" if fail_count >= MAX_FAIL_BEFORE_EXPIRED else "degraded"
        await update_keepalive_status(ref, new_status, fail_count)
        print(f"[Keepalive/YYB] ✗ {nickname} status={status}, fail_count={fail_count}")
        return {"ref": ref, "success": False, "message": status}
    except Exception as exc:
        fail_count = (ext.get("keepalive_fail_count", 0) or 0) + 1
        new_status = "expired" if fail_count >= MAX_FAIL_BEFORE_EXPIRED else "degraded"
        await update_keepalive_status(ref, new_status, fail_count)
        print(f"[Keepalive/YYB] ✗ {nickname} 刷新异常 (fail_count={fail_count}): {exc}")
        return {"ref": ref, "success": False, "message": str(exc)[:160]}


async def refresh_yyb_accounts_once(accounts: list[dict] | None = None) -> list[dict]:
    started = int(time.time())
    accounts = accounts if accounts is not None else await yyb_service.get_accounts()
    semaphore = asyncio.Semaphore(MAX_REFRESH_CONCURRENCY)

    async def run(acc):
        async with semaphore:
            return await _keepalive_single_account(acc)

    results = await asyncio.gather(*(run(acc) for acc in accounts), return_exceptions=True)
    normalized = [
        result if isinstance(result, dict) else {
            "ref": "", "success": False, "message": str(result)[:160],
        }
        for result in results
    ]
    success = sum(1 for result in normalized if result.get("success"))
    _record_state(
        "yyb", last_started_at=started, last_finished_at=int(time.time()),
        total=len(normalized), success=success, failed=len(normalized) - success,
    )
    print(f"[Keepalive/YYB] === 本轮完毕: {success}/{len(normalized)} 存活 ===")
    return normalized


async def keepalive_yyb_accounts():
    while True:
        try:
            results = await refresh_yyb_accounts_once()
            failed_refs = {item["ref"] for item in results if item.get("ref") and not item.get("success")}
            if failed_refs:
                # 短退避只复查失败账号，不让一次瞬时网络波动拖到下一轮。
                await asyncio.sleep(YYB_RETRY_INTERVAL)
                accounts = await yyb_service.get_accounts()
                await refresh_yyb_accounts_once([
                    account for account in accounts if account.get("openid") in failed_refs
                ])
        except Exception as exc:
            _record_state("yyb", last_error=str(exc)[:160], last_finished_at=int(time.time()))
            print(f"[Keepalive/YYB] 循环异常: {exc}")
            traceback.print_exc()
        await asyncio.sleep(YYB_REFRESH_INTERVAL)


async def probe_mmtls_once() -> dict:
    """对所有账号立即执行一次独立微信小程序 Code 有效性实测检验"""
    started = int(time.time())
    accounts = await yyb_service.get_accounts()
    success = 0
    failed = 0
    test_appid = "wxe13d2fcd5c54483f"
    for acc in accounts:
        ref = acc.get("openid", "")
        nickname = acc.get("nickname") or (ref[:10] if ref else "?")
        if not ref or acc.get("status") == "expired":
            continue
        try:
            await yyb_service.get_code(ref, test_appid)
            success += 1
            await update_probe_status(ref, "alive")
            print(f"[Keepalive/Probe] ✓ {nickname} 独立小程序有效性实测成功")
        except Exception as exc:
            failed += 1
            await update_probe_status(ref, "failed")
            print(f"[Keepalive/Probe] ✗ {nickname} 实测异常: {exc}")
    snapshot = {
        "last_started_at": started, "last_finished_at": int(time.time()),
        "success": success, "failed": failed,
    }
    _record_state("mmtls", **snapshot)
    return snapshot


async def keepalive_mmtls_heartbeat():
    # 启动即刻执行第一次实测检验，确保开机后第一时间拥有最新检验时间
    while True:
        try:
            await probe_mmtls_once()
        except Exception as exc:
            _record_state("mmtls", last_error=str(exc)[:160], last_finished_at=int(time.time()))
            print(f"[Keepalive/Probe] 循环异常: {exc}")
        # 20 ~ 30 分钟随机抖动探测
        interval = random.randint(20 * 60, 30 * 60)
        print(f"[Keepalive/Probe] 下次有效性实测检验将在 {interval // 60} 分钟后执行...")
        await asyncio.sleep(interval)


async def refresh_tm_sessions_once() -> dict:
    started = int(time.time())
    all_exts = await get_all_account_exts()
    refreshed = 0
    validated = 0
    failed = 0
    for ext in all_exts:
        ref = ext.get("ref", "")
        if not ref:
            continue
        try:
            session = get_tm_session(ref)
            # 先从数据库加载现有 Cookie，避免服务重启后把 expires_at=0 误判为过期。
            await session.ensure_session()
            remaining = session.expires_at - time.time()
            if remaining < TM_SESSION_REFRESH_AHEAD:
                await session.refresh_session(force=True)
                refreshed += 1
                print(f"[Keepalive/TM] ✓ {ref[:12]}... Cookie 已提前续期")
            else:
                validated += 1
        except Exception as exc:
            failed += 1
            print(f"[Keepalive/TM] ✗ {ref[:12]}... 校验/续期异常: {exc}")
    snapshot = {
        "last_started_at": started, "last_finished_at": int(time.time()),
        "total": len(all_exts), "validated": validated,
        "refreshed": refreshed, "failed": failed,
    }
    _record_state("teachermate", **snapshot)
    print(f"[Keepalive/TM] === 本轮完毕: 有效 {validated}, 续期 {refreshed}, 失败 {failed} ===")
    return snapshot


async def keepalive_tm_sessions():
    await asyncio.sleep(5)
    while True:
        try:
            await refresh_tm_sessions_once()
        except Exception as exc:
            _record_state("teachermate", last_error=str(exc)[:160], last_finished_at=int(time.time()))
            print(f"[Keepalive/TM] 循环异常: {exc}")
            traceback.print_exc()
        await asyncio.sleep(TM_SESSION_REFRESH_INTERVAL)


async def start_keepalive():
    print(f"[Keepalive] 保活引擎启动中...")
    await asyncio.sleep(STARTUP_DELAY)
    _state["started_at"] = int(time.time())
    print("[Keepalive] ========== 三层保活引擎已启动 ==========")
    print(f"[Keepalive] YYB 凭证轮换: {YYB_REFRESH_INTERVAL // 60} 分钟")
    print(f"[Keepalive] 独立小程序 Code 实测: 20~30 分钟随机探测 (开机立即首次检验)")
    print(f"[Keepalive] 微助教 Cookie 检查: {TM_SESSION_REFRESH_INTERVAL // 60} 分钟")
    await asyncio.gather(
        keepalive_yyb_accounts(),
        keepalive_mmtls_heartbeat(),
        keepalive_tm_sessions(),
    )

