"""Concurrent account validity monitor.

The monitor records three states: valid, expired and unknown.  Transient
network/WAF responses do not flip a healthy account to expired.
"""

from __future__ import annotations

import html
import logging
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

import requests

from ai_solver import check_ai_connectivity
from safe_json_store import ACCOUNTS_STORE, AI_HEALTH_STORE, data_path


PUSH_PLUS_TOKEN = os.environ.get("PUSH_PLUS_TOKEN", "").strip()
PUSH_PLUS_URL = os.environ.get("PUSH_PLUS_URL", "https://www.pushplus.plus/send").strip()
ACCOUNTS_FILE = str(data_path("accounts.json"))
MONITOR_CONCURRENCY = max(1, min(64, int(os.environ.get("YKT_BATCH_CONCURRENCY", "16"))))
REQUEST_TIMEOUT = max(3.0, float(os.environ.get("YKT_REQUEST_TIMEOUT", "12")))
ACCOUNT_MONITOR_INTERVAL = max(300, int(os.environ.get("YKT_MONITOR_INTERVAL", "21600")))
AI_HEALTH_INTERVAL = max(300, int(os.environ.get("YKT_AI_HEALTH_INTERVAL", "10800")))
AI_HEALTH_TIMEOUT = max(5.0, float(os.environ.get("YKT_AI_HEALTH_TIMEOUT", "30")))
AI_HEALTH_HISTORY_LIMIT = max(
    10,
    min(500, int(os.environ.get("YKT_AI_HEALTH_HISTORY_LIMIT", "100"))),
)
AI_HEALTH_PROVIDER = "nvidia"
AI_HEALTH_MODEL = "google/gemma-4-31b-it"
AI_HEALTH_PROMPT = "你好"
AUTH_PATTERN = re.compile(
    r"登录|登陆|失效|过期|认证|未授权|unauthori[sz]ed|forbidden|session|credential|token|login",
    re.I,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ykt-monitor")


def send_wechat_alert(title: str, content: str) -> bool:
    if not PUSH_PLUS_TOKEN:
        logger.debug("PUSH_PLUS_TOKEN 未配置，跳过推送：%s", title)
        return False
    try:
        response = requests.post(
            PUSH_PLUS_URL,
            json={
                "token": PUSH_PLUS_TOKEN,
                "title": title,
                "content": content,
                "template": "html",
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        payload = response.json()
        if int(payload.get("code", 0)) not in {0, 200}:
            raise RuntimeError(payload.get("msg") or payload)
        logger.info("PushPlus 推送成功：%s", title)
        return True
    except Exception as exc:
        logger.error("PushPlus 推送失败：%s", exc)
        return False


def _account_key(account: dict) -> tuple[str, str]:
    return (
        str(account.get("group_key") or ""),
        str(account.get("phone") or account.get("uid") or account.get("id") or ""),
    )


def _probe_account(account: dict) -> dict:
    cookie = str(account.get("cookie") or "")
    if not cookie:
        return {"state": "expired", "reason": "cookie_missing"}
    csrf_match = re.search(r"csrftoken=([^;\s]+)", cookie)
    device = account.get("device") if isinstance(account.get("device"), dict) else {}
    headers = {
        "cookie": cookie,
        "x-csrftoken": csrf_match.group(1) if csrf_match else "",
        "user-agent": device.get("user-agent", "okhttp/4.12.0 Android"),
        "x-client": "app",
        "xtbz": "ykt",
    }
    if account.get("uid"):
        headers["x-uid"] = str(account["uid"])

    candidate_urls = [
        "https://changjiang.yuketang.cn/v/course_meta/user_info",
        "https://www.yuketang.cn/v/course_meta/user_info",
        "https://changjiang.yuketang.cn/v2/api/web/userinfo",
        "https://www.yuketang.cn/v2/api/web/userinfo",
        "https://changjiang.yuketang.cn/api/v3/user/basic-info",
        "https://www.yuketang.cn/api/v3/user/basic-info",
    ]
    last_reason = "network"
    for url in candidate_urls:
        try:
            response = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        except requests.RequestException as exc:
            last_reason = f"network:{exc.__class__.__name__}"
            continue
        if response.status_code in {401, 403}:
            return {"state": "expired", "reason": f"http_{response.status_code}"}
        if response.status_code < 200 or response.status_code >= 300:
            last_reason = f"http_{response.status_code}"
            continue
        try:
            data = response.json()
        except ValueError:
            text = response.text[:4000]
            if AUTH_PATTERN.search(text):
                return {"state": "expired", "reason": "login_page"}
            last_reason = "non_json"
            continue
        if not isinstance(data, dict):
            last_reason = "invalid_json_shape"
            continue
        code = data.get("code")
        try:
            code_num = int(code) if code is not None else 0
        except (TypeError, ValueError):
            code_num = 0
        success = data.get("success")
        data_body = data.get("data")
        message = str(data.get("msg") or data.get("message") or data.get("detail") or "")

        # 只要 code 为 0 或 success 为 True，并且包含有效数据
        if (success is True or code_num == 0 or code in {0, "0", "success"}) and data_body is not None:
            if isinstance(data_body, dict):
                profile = data_body.get("user_profile") or data_body.get("userInfo") or data_body.get("user") or data_body
                if isinstance(profile, dict) and any(
                    profile.get(field) for field in ("user_id", "uid", "nickname", "name", "id", "phone", "userId", "username")
                ):
                    return {"state": "valid", "reason": "profile_ok"}
                if data_body:
                    return {"state": "valid", "reason": "data_ok"}
            elif isinstance(data_body, (list, str, int, bool)):
                return {"state": "valid", "reason": "data_ok"}

        # 明确的鉴权失败
        if success is False or code_num in {401, 403, 1001, 1002, 10001, 10002} or AUTH_PATTERN.search(message):
            return {"state": "expired", "reason": f"api_{code or 'auth'}"}
        last_reason = f"unrecognized_code_{code}"
    return {"state": "unknown", "reason": last_reason}


def build_combined_inspection_html(
    account_summary: dict,
    expired_accounts: list[str],
    ai_probes: list[dict],
) -> str:
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    total = account_summary.get("total", 0)
    valid = account_summary.get("valid", 0)
    expired = account_summary.get("expired", 0)
    unknown = account_summary.get("unknown", 0)

    ai_cards_html = ""
    for probe in ai_probes:
        name = html.escape(str(probe.get("displayName") or probe.get("model") or "AI 模型"))
        tone = probe.get("tone") or "blue"
        tag_bg = "rgba(191,90,242,0.12)" if tone == "purple" else "rgba(10,132,255,0.12)"
        tag_color = "#8944AB" if tone == "purple" else "#0064D2"
        tag_border = "rgba(191,90,242,0.3)" if tone == "purple" else "rgba(10,132,255,0.3)"

        is_ok = probe.get("success") is True
        status_bg = "#E5F9ED" if is_ok else "#FFEBEB"
        status_color = "#248A3D" if is_ok else "#D70015"
        status_border = "rgba(52,199,89,0.35)" if is_ok else "rgba(255,59,48,0.35)"
        status_text = "✓ 连通正常" if is_ok else "✕ 连接异常"
        elapsed_val = probe.get("elapsedSeconds")
        elapsed_text = f"{float(elapsed_val):.2f}s" if (is_ok and elapsed_val is not None) else (probe.get("error") or "超时")

        ai_cards_html += f"""
        <div style="box-sizing:border-box;display:flex;align-items:center;justify-content:space-between;padding:10px 12px;background:#F9F9FB;border:1px solid #E5E5EA;border-radius:10px;margin-bottom:8px;">
          <div style="display:flex;align-items:center;gap:8px;">
            <span style="display:inline-block;padding:3px 8px;border-radius:6px;font-size:11px;font-weight:800;background:{tag_bg};color:{tag_color};border:1px solid {tag_border};">{name}</span>
            <span style="font-size:11.5px;color:#636366;font-family:monospace;">{html.escape(str(probe.get('model', '')))}</span>
          </div>
          <div style="display:flex;align-items:center;gap:6px;">
            <span style="font-size:11px;font-weight:700;color:{status_color};background:{status_bg};padding:3px 8px;border-radius:6px;border:1px solid {status_border};">{status_text}</span>
            <span style="font-size:11px;color:#8E8E93;font-weight:600;">{elapsed_text}</span>
          </div>
        </div>"""

    expired_section_html = ""
    if expired_accounts:
        names_joined = "、".join(html.escape(name) for name in expired_accounts)
        expired_section_html = f"""
        <div style="margin-top:10px;margin-bottom:14px;padding:12px 14px;background:#FFF0EF;border:1px solid rgba(255,59,48,0.3);border-radius:12px;">
          <div style="font-size:12px;font-weight:800;color:#D70015;margin-bottom:4px;">⚠️ 发现 {len(expired_accounts)} 个账号凭证失效</div>
          <div style="font-size:11.5px;color:#3A3A3C;line-height:1.6;">失效列表：{names_joined}</div>
          <div style="font-size:10.5px;color:#8E8E93;margin-top:4px;">请打开小程序重新登录或同步有效 Cookie。</div>
        </div>"""

    return f"""<div style="max-width:540px;margin:0 auto;background:#FFFFFF;border-radius:18px;overflow:hidden;box-shadow:0 8px 30px rgba(0,0,0,0.08);border:1px solid #E5E5EA;font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Helvetica Neue',Arial,sans-serif;">
  <div style="background:linear-gradient(135deg,#0A84FF,#0056B3);padding:20px 20px;color:#FFFFFF;">
    <div style="font-size:11px;font-weight:700;letter-spacing:1px;opacity:0.85;margin-bottom:4px;">☁️ 雨课堂云端自动托管</div>
    <div style="font-size:20px;font-weight:850;letter-spacing:-0.4px;">系统综合巡检报告</div>
    <div style="font-size:11.5px;opacity:0.85;margin-top:5px;">巡检时间：{now_str}</div>
  </div>

  <div style="padding:18px 16px;">
    <!-- 模块一：账号状态 -->
    <div style="font-size:13px;font-weight:850;color:#1C1C1E;margin-bottom:10px;display:flex;align-items:center;gap:6px;">
      <span>📱</span> 账号健康状态
    </div>
    <table style="width:100%;border-collapse:separate;border-spacing:8px;margin-bottom:8px;">
      <tr>
        <td style="width:25%;background:#F2F2F7;border-radius:12px;padding:10px 4px;text-align:center;">
          <div style="font-size:10.5px;color:#8E8E93;font-weight:700;">总账号</div>
          <div style="font-size:20px;font-weight:850;color:#1C1C1E;margin-top:2px;">{total}</div>
        </td>
        <td style="width:25%;background:#E5F9ED;border:1px solid rgba(52,199,89,0.3);border-radius:12px;padding:10px 4px;text-align:center;">
          <div style="font-size:10.5px;color:#248A3D;font-weight:700;">正常有效</div>
          <div style="font-size:20px;font-weight:850;color:#34C759;margin-top:2px;">{valid}</div>
        </td>
        <td style="width:25%;background:{'#FFEBEB' if expired else '#F2F2F7'};border:{'1px solid rgba(255,59,48,0.3)' if expired else 'none'};border-radius:12px;padding:10px 4px;text-align:center;">
          <div style="font-size:10.5px;color:{'#D70015' if expired else '#8E8E93'};font-weight:700;">已失效</div>
          <div style="font-size:20px;font-weight:850;color:{'#FF3B30' if expired else '#8E8E93'};margin-top:2px;">{expired}</div>
        </td>
        <td style="width:25%;background:{'#FFF8ED' if unknown else '#F2F2F7'};border:{'1px solid rgba(255,149,0,0.3)' if unknown else 'none'};border-radius:12px;padding:10px 4px;text-align:center;">
          <div style="font-size:10.5px;color:{'#D97706' if unknown else '#8E8E93'};font-weight:700;">待复核</div>
          <div style="font-size:20px;font-weight:850;color:{'#FF9500' if unknown else '#8E8E93'};margin-top:2px;">{unknown}</div>
        </td>
      </tr>
    </table>

    {expired_section_html}

    <!-- 模块二：AI 连通性 -->
    <div style="font-size:13px;font-weight:850;color:#1C1C1E;margin:14px 0 10px;display:flex;align-items:center;gap:6px;">
      <span>🧠</span> 三路由 AI 解题引擎连通性
    </div>
    {ai_cards_html}

    <!-- 路由策略提示卡 -->
    <div style="margin-top:10px;padding:8px 12px;background:#F5F7FA;border-radius:9px;border:1px dashed #D1D1D6;font-size:11px;color:#636366;line-height:1.5;">
      💡 <b>当前生效调度</b>：Gemma-4 与 Qwen3.8 同步答题仲裁（35s 交卷），25s 未答自动切 Qwen3.5 保底（40s 交卷）。
    </div>

    <!-- 底部版权/版本信息 -->
    <div style="margin-top:16px;padding-top:12px;border-top:1px solid #F0F0F2;display:flex;justify-content:space-between;align-items:center;font-size:10.5px;color:#8E8E93;">
      <span>雨课堂云端引擎 v2.6.1</span>
      <span>自动化无人值守模式</span>
    </div>
  </div>
</div>"""


def check_accounts(notify: bool = True) -> dict:
    accounts = ACCOUNTS_STORE.read()
    if not accounts:
        logger.info("账号库为空，跳过巡检")
        return {"total": 0, "valid": 0, "expired": 0, "unknown": 0}

    results: dict[tuple[str, str], dict] = {}
    with ThreadPoolExecutor(max_workers=min(MONITOR_CONCURRENCY, len(accounts))) as executor:
        futures = {executor.submit(_probe_account, account): _account_key(account) for account in accounts}
        for future in as_completed(futures):
            key = futures[future]
            try:
                results[key] = future.result()
            except Exception as exc:
                logger.exception("账号探针异常：%s", key)
                results[key] = {"state": "unknown", "reason": str(exc)}

    checked_at = int(time.time() * 1000)

    def mutate(current_accounts: list):
        for account in current_accounts:
            result = results.get(_account_key(account))
            if not result:
                continue
            state = result["state"]
            account["validityState"] = state
            account["validitySource"] = "server-monitor"
            account["validityCheckedAt"] = checked_at
            if state == "valid":
                account["expired"] = False
                account["validityFailureCount"] = 0
            elif state == "expired":
                account["expired"] = True
                account["validityFailureCount"] = int(account.get("validityFailureCount") or 0) + 1

    ACCOUNTS_STORE.update(mutate)

    summary = {
        "total": len(accounts),
        "valid": sum(1 for item in results.values() if item["state"] == "valid"),
        "expired": sum(1 for item in results.values() if item["state"] == "expired"),
        "unknown": sum(1 for item in results.values() if item["state"] == "unknown"),
    }
    expired_names = [
        str(account.get("remark") or account.get("name") or account.get("phone") or "未命名账号")
        for account in accounts
        if results.get(_account_key(account), {}).get("state") == "expired"
    ]
    if notify:
        ai_state = AI_HEALTH_STORE.read() or {}
        ai_probes = ai_state.get("probes") if isinstance(ai_state.get("probes"), list) else []
        if not ai_probes:
            check_ai_health()
            ai_state = AI_HEALTH_STORE.read() or {}
            ai_probes = ai_state.get("probes") if isinstance(ai_state.get("probes"), list) else []
        html_report = build_combined_inspection_html(summary, expired_names, ai_probes)
        send_wechat_alert("雨课堂云端综合巡检", html_report)
    logger.info("账号巡检汇总：%s", summary)
    return summary


AI_HEALTH_PROBES = [
    {
        "provider": os.environ.get("AI_HEALTH_PROVIDER_1", "nvidia").strip(),
        "model": os.environ.get("AI_HEALTH_MODEL_1", "google/gemma-4-31b-it").strip(),
        "displayName": "Gemma-4",
        "tone": "blue",
    },
    {
        "provider": os.environ.get("AI_HEALTH_PROVIDER_2", "cloudflare").strip(),
        "model": os.environ.get("AI_HEALTH_MODEL_2", "@cf/qwen/qwen3.8-27b").strip(),
        "displayName": "Qwen3.8",
        "tone": "purple",
    },
]


def check_ai_health() -> dict:
    """Probe Gemma-4 and Qwen3.8 and persist rolling health history."""

    records = []
    for probe in AI_HEALTH_PROBES:
        rec = check_ai_connectivity(
            provider=probe["provider"],
            model=probe["model"],
            prompt=AI_HEALTH_PROMPT,
            timeout_seconds=AI_HEALTH_TIMEOUT,
            display_name=probe["displayName"],
            tone=probe["tone"],
        )
        rec["tone"] = probe["tone"]
        rec["nextCheckAt"] = int(rec["checkedAt"]) + AI_HEALTH_INTERVAL * 1000
        records.append(rec)

    primary_rec = records[0] if records else {}

    def mutate(current: dict):
        history = current.get("history")
        if not isinstance(history, list):
            history = []
        current["latest"] = primary_rec
        current["probes"] = records
        current["history"] = [*records, *history][:AI_HEALTH_HISTORY_LIMIT]
        current["intervalSeconds"] = AI_HEALTH_INTERVAL
        current["provider"] = primary_rec.get("provider") or "nvidia"
        current["model"] = primary_rec.get("model") or "google/gemma-4-31b-it"

    AI_HEALTH_STORE.update(mutate)
    for rec in records:
        result_text = "成功" if rec["success"] else "失败"
        logger.info(
            "%s 连通性检测%s，耗时 %.3fs%s",
            rec["displayName"],
            result_text,
            rec["elapsedSeconds"],
            "" if rec["success"] else f"，错误：{rec['error']}",
        )
    return primary_rec


def run_combined_inspection(notify: bool = True) -> tuple[dict, dict]:
    """Execute complete system inspection: accounts + dual AI probes."""
    ai_latest = check_ai_health()
    ai_state = AI_HEALTH_STORE.read() or {}
    ai_probes = ai_state.get("probes") if isinstance(ai_state.get("probes"), list) else [ai_latest]

    accounts = ACCOUNTS_STORE.read()
    results: dict[tuple[str, str], dict] = {}
    if accounts:
        with ThreadPoolExecutor(max_workers=min(MONITOR_CONCURRENCY, len(accounts))) as executor:
            futures = {executor.submit(_probe_account, account): _account_key(account) for account in accounts}
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results[key] = future.result()
                except Exception as exc:
                    results[key] = {"state": "unknown", "reason": str(exc)}
        checked_at = int(time.time() * 1000)

        def mutate(current_accounts: list):
            for account in current_accounts:
                result = results.get(_account_key(account))
                if not result:
                    continue
                state = result["state"]
                account["validityState"] = state
                account["validitySource"] = "server-monitor"
                account["validityCheckedAt"] = checked_at
                if state == "valid":
                    account["expired"] = False
                    account["validityFailureCount"] = 0
                elif state == "expired":
                    account["expired"] = True
                    account["validityFailureCount"] = int(account.get("validityFailureCount") or 0) + 1

        ACCOUNTS_STORE.update(mutate)

    account_summary = {
        "total": len(accounts),
        "valid": sum(1 for item in results.values() if item["state"] == "valid"),
        "expired": sum(1 for item in results.values() if item["state"] == "expired"),
        "unknown": sum(1 for item in results.values() if item["state"] == "unknown"),
    }
    expired_names = [
        str(account.get("remark") or account.get("name") or account.get("phone") or "未命名账号")
        for account in accounts
        if results.get(_account_key(account), {}).get("state") == "expired"
    ]

    if notify:
        html_report = build_combined_inspection_html(account_summary, expired_names, ai_probes)
        send_wechat_alert("雨课堂云端综合巡检", html_report)
    logger.info("综合巡检完成：账号=%s，AI探针数=%s", account_summary, len(ai_probes))
    return account_summary, ai_latest


def _periodic_loop(name: str, interval_seconds: int, callback) -> None:
    """Run one monitor independently at a stable start-to-start interval."""

    while True:
        cycle_started = time.monotonic()
        try:
            callback()
        except Exception:
            logger.exception("%s异常", name)
        elapsed = time.monotonic() - cycle_started
        time.sleep(max(1.0, interval_seconds - elapsed))


if __name__ == "__main__":
    logger.info(
        "监控引擎启动：账号与综合巡检=%ss，双模型(Gemma-4/Qwen3.8)连通性检测=%ss",
        ACCOUNT_MONITOR_INTERVAL,
        AI_HEALTH_INTERVAL,
    )
    threading.Thread(
        target=_periodic_loop,
        args=("双模型连通性检测", AI_HEALTH_INTERVAL, check_ai_health),
        name="ai-health-monitor",
        daemon=True,
    ).start()
    _periodic_loop("综合巡检", ACCOUNT_MONITOR_INTERVAL, run_combined_inspection)
