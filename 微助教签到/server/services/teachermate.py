"""
微助教 API 会话管理 + 接口代理
"""
import asyncio
import time
from urllib.parse import urlparse, parse_qs
import httpx
from config import TEACHERMATE_BASE, TEACHERMATE_WECHAT_API, TEACHERMATE_APP_ID, TEACHERMATE_SIGNIN_HOST
from services.yyb_service import yyb_service
from models.database import upsert_account_ext, get_account_ext

WECHAT_USER_AGENT = "Mozilla/5.0 (Linux; Android 10; Mobile) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36 MicroMessenger/8.0.40 NetType/WIFI Language/zh_CN"
SESSION_FALLBACK_TTL = 24 * 3600
SESSION_VALIDITY_SKEW = 5 * 60

class TeacherMateSession:
    """每个微信账号对应一个独立的微助教会话（全无锁并发极速模式）"""

    def __init__(self, ref: str):
        self.ref = ref
        self.session_cookie: str | None = None
        self.session_sig: str | None = None
        self.openid: str | None = None
        self.expires_at: int = 0

    @property
    def is_valid(self) -> bool:
        return (self.session_cookie is not None
                and self.expires_at > time.time() + SESSION_VALIDITY_SKEW)

    @property
    def cookies(self) -> dict:
        return {
            "session": self.session_cookie,
            "session.sig": self.session_sig,
            "grayVersion": "0",
        }

    async def ensure_session(self):
        """确保 session 有效，过期则极速自动续期（纯无锁并发直连）"""
        if self.is_valid:
            return

        # 尝试从数据库加载
        ext = await get_account_ext(self.ref)
        if ext and ext.get("tm_session") and ext.get("tm_session_expires", 0) > time.time():
            self.session_cookie = ext["tm_session"]
            self.session_sig = ext["tm_session_sig"]
            self.openid = ext.get("tm_openid")
            self.expires_at = ext["tm_session_expires"]
            return

        # 需要重新登录
        await self._login_unlocked()

    async def _login_unlocked(self):
        """完整的 OAuth 登录流程"""
        # Step 1: 获取 code
        code = await yyb_service.get_code(self.ref, TEACHERMATE_APP_ID)

        # Step 2: OAuth 回调获取 openid
        async with httpx.AsyncClient(
            headers={"User-Agent": WECHAT_USER_AGENT},
            follow_redirects=False,
            verify=False,
        ) as client:
            resp = await client.get(
                f"{TEACHERMATE_BASE}/api/v1/wechat/r",
                params={"m": "s_answer", "code": code, "state": ""},
                timeout=15,
            )

            if resp.status_code != 302:
                raise Exception(f"OAuth 回调失败, status={resp.status_code}")

            location = resp.headers.get("location", "")
            if "openid=" not in location:
                raise Exception(f"OAuth 回调未返回 openid: {location}")

            openid = location.split("openid=")[-1].split("&")[0]

            # Step 3: 复用 OAuth 客户端访问页面，保留 grayVersion 等中间 Cookie。
            # 用完整 URL 访问（可能是相对路径）
            page_url = location
            if page_url.startswith("/"):
                page_url = f"{TEACHERMATE_BASE}{page_url}"

            resp2 = await client.get(page_url, timeout=15)
            session_cookie = resp2.cookies.get("session")
            session_sig = resp2.cookies.get("session.sig")

            if not session_cookie:
                raise Exception("未获取到 session cookie")

            # 抓包中的 session/session.sig 都是 24 小时 Cookie；优先采用服务端真实 expires。
            cookie_expiries = [
                int(cookie.expires) for cookie in resp2.cookies.jar
                if cookie.name in ("session", "session.sig") and cookie.expires
            ]
            expires_at = min(cookie_expiries) if cookie_expiries else int(time.time()) + SESSION_FALLBACK_TTL

        # 整套流程成功后一次性切换，续期中途失败时继续保留旧 Cookie。
        self.openid = openid
        self.session_cookie = session_cookie
        self.session_sig = session_sig
        self.expires_at = expires_at

        # 持久化到数据库
        await upsert_account_ext(
            self.ref,
            tm_openid=self.openid,
            tm_session=self.session_cookie,
            tm_session_sig=self.session_sig,
            tm_session_expires=self.expires_at,
        )

    async def refresh_session(self, force: bool = False):
        """刷新 Session，极速并发直连"""
        if not force and self.is_valid:
            return
        await self._login_unlocked()

    async def _relogin_if_unchanged(self, expected_cookie: str | None = None):
        """失效即刻刷新登录"""
        await self._login_unlocked()

    async def _request(self, method: str, path: str, params: dict = None, json_data: dict = None) -> dict | list:
        """
        统一请求方法，自动重登重试。
        策略：请求失败（非2xx / 非JSON / 异常）→ 强制重新 OAuth 登录 → 重试一次
        """
        await self.ensure_session()

        for attempt in range(2):  # 最多 2 次：原始请求 + 重试
            request_cookie = self.session_cookie
            headers = {
                "User-Agent": WECHAT_USER_AGENT,
                "openId": self.openid
            }
            try:
                async with httpx.AsyncClient(
                    headers=headers, verify=False,
                    cookies=self.cookies, follow_redirects=False
                ) as client:
                    if method == "GET":
                        r = await client.get(
                            f"{TEACHERMATE_WECHAT_API}{path}",
                            params=params, timeout=15,
                        )
                    else:
                        r = await client.post(
                            f"{TEACHERMATE_WECHAT_API}{path}",
                            json=json_data, timeout=15,
                        )

                # 区分【需要重新登录】和【只需要原样重试】
                need_relogin = False
                need_retry = False

                if r.status_code in (301, 302, 401, 403):
                    need_relogin = True
                elif r.status_code >= 500 or r.status_code == 429:
                    # 500+ 或被限流，只是临时错误，不需要重新登录，只需要退避重试
                    need_retry = True
                elif r.status_code >= 400:
                    # 4xx 客户端错误，重试或重登大概率都没用，直接抛出
                    r.raise_for_status()
                else:
                    # 状态码 2xx，检查响应是否为有效 JSON
                    content_type = r.headers.get("content-type", "")
                    if "json" not in content_type and "text/plain" not in content_type:
                        # 返回了 HTML 页面（通常是登录重定向页），视为 session 失效
                        body_preview = r.text[:200]
                        if "<html" in body_preview.lower() or "<!doctype" in body_preview.lower():
                            need_relogin = True

                if need_relogin and attempt == 0:
                    print(f"[TM] {path} 登录失效 (status={r.status_code}), 正在重新登录...")
                    await self._relogin_if_unchanged(request_cookie)
                    continue  # 重试

                if need_retry and attempt == 0:
                    print(f"[TM] {path} 服务器繁忙 (status={r.status_code}), 1.5s 后原样重试...")
                    await asyncio.sleep(1.5)
                    continue  # 不换 Cookie，原样重试

                if need_relogin:
                    raise Exception(f"TM API {path} 会话刷新后仍失效, status={r.status_code}")
                if need_retry:
                    r.raise_for_status()  # 第二次仍失败，直接抛出异常

                return r.json()

            except (httpx.RequestError, httpx.TimeoutException) as e:
                if attempt == 0:
                    print(f"[TM] {path} 网络/超时异常 ({e}), 1.5s 后重试...")
                    await asyncio.sleep(1.5)
                    continue
                raise

        raise Exception(f"TM API {path} 请求失败，已重试")

    async def api_get(self, path: str, params: dict = None) -> dict | list:
        """GET 请求微助教 API（自动重登重试）"""
        return await self._request("GET", path, params=params)

    async def api_post(self, path: str, json_data: dict = None) -> dict:
        """POST 请求微助教 API（自动重登重试）"""
        return await self._request("POST", path, json_data=json_data)

    # ── 业务方法 ──

    async def get_courses(self) -> list:
        return await self.api_get("/v3/students/courses")

    async def get_chapters(self, course_id: int) -> list:
        return await self.api_get(f"/v3/students/courses/{course_id}/chapters")

    async def get_questions(self, course_id: int, page: int = 0,
                            is_open: int = None, is_answered: int = 2,
                            chapter_id: int = None) -> dict:
        params = {"courseId": course_id, "page": page, "pageSize": 200, "limit": 200}
        if is_open is not None:
            params["isOpen"] = is_open
        if is_answered != 2:
            params["isAnswered"] = is_answered
        if chapter_id:
            params["chapterId"] = chapter_id
        return await self.api_get("/v3/students/questions", params)

    async def get_question_detail(self, question_id: int) -> dict:
        return await self.api_get(f"/v3/students/questions/{question_id}")

    @staticmethod
    def format_submission_answer(question_type: int, answer):
        """按官方前端协议生成 answer；选择题必须提交对象，数字数组会触发 rank 写入异常。"""
        if question_type in (1, 2, 3):
            source = answer if isinstance(answer, list) else [answer]
            formatted = []
            seen = set()
            for item in source:
                if isinstance(item, dict):
                    value = item.get("index", item.get("rank"))
                else:
                    value = item
                try:
                    index = int(value)
                except (TypeError, ValueError):
                    continue
                if index not in seen:
                    formatted.append({"index": index})
                    seen.add(index)
            return formatted
        if question_type == 4:
            source = answer if isinstance(answer, list) else [answer]
            return [str(value or "") for value in source]
        if question_type == 5:
            if isinstance(answer, list):
                return str(answer[0]) if answer else ""
            return str(answer or "")
        return answer

    async def submit_answer(self, course_id: int, question_id: int,
                            answer, files: list = None, audio: list = None,
                            question_type: int | None = None) -> dict:
        wire_answer = (
            self.format_submission_answer(question_type, answer)
            if question_type is not None else answer
        )
        return await self.api_post("/v3/students/answer/question", {
            "courseId": course_id,
            "questionId": question_id,
            "answer": wire_answer,
            "files": files or [],
            "audio": audio or [],
        })

    async def submit_paper(self, course_id: int, paper_id: int,
                           answer: dict, is_once: int = None) -> dict:
        body = {"courseId": course_id, "paperId": paper_id, "answer": answer}
        if is_once is not None:
            body["isOnceAnswer"] = is_once
        return await self.api_post("/v3/students/answer/paper", body)

    async def get_oss_signature(self, content_type: str = "image/png") -> dict:
        return await self.api_get("/v3/oss/signature", {"type": content_type})


# ── 会话缓存（内存） ──

_sessions: dict[str, TeacherMateSession] = {}


def get_tm_session(ref: str) -> TeacherMateSession:
    """获取或创建指定账号的微助教会话"""
    if ref not in _sessions:
        _sessions[ref] = TeacherMateSession(ref)
    return _sessions[ref]


def remove_tm_session(ref: str):
    """删除指定账号的微助教会话（账号删除时调用，清理内存）"""
    _sessions.pop(ref, None)


# 内存缓存，保存预取的 WeChat Code (格式: { ref: {"task": Task, "timestamp": float} })
PRE_CODES = {}

# 全局持久化极速签到 HTTP 客户端（连接池复用，避免每次新建连接与 TLS 握手）
_SIGNIN_CLIENT: httpx.AsyncClient | None = None

def get_signin_http_client() -> httpx.AsyncClient:
    global _SIGNIN_CLIENT
    if _SIGNIN_CLIENT is None or _SIGNIN_CLIENT.is_closed:
        _SIGNIN_CLIENT = httpx.AsyncClient(
            headers={"User-Agent": WECHAT_USER_AGENT},
            follow_redirects=False,
            verify=False,
            timeout=httpx.Timeout(connect=4.0, read=6.0, write=4.0, pool=10.0),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
        )
    return _SIGNIN_CLIENT


# ── 签到（独立流程，不需要 session） ──

async def do_signin(ref: str, extra_hash: str) -> dict:
    """执行单个账号的极速扫码签到（0.2s 级直取 302 重定向头响应，杜绝加载全量 SPA 网页）"""
    import re
    # 提取 32 位及以上十六进制字符串
    match = re.search(r'([a-f0-9]{32,})', extra_hash, re.IGNORECASE)
    if match:
        extra_hash = match.group(1)
        
    signin_start = time.time()
    try:
        # 1. 优先消费预热微信 Code
        now = time.time()
        cached = PRE_CODES.get(ref)
        code_start = time.time()
        code = None
        code_mode = "现场获取"
        
        if cached and (now - cached.get("timestamp", 0) < 240):  # 4分钟内有效
            if cached.get("error"):
                # 预热阶段已明确该账号过期/失效，直接秒退，避免重复等待 3 秒重试
                print(f"[Signin] ⚠️ 账号 {ref[:8]}... 预热已知失效: {cached['error']}")
                return {"ref": ref, "success": False, "message": f"签到失败: {cached['error']}"}
            elif cached.get("code"):
                code = cached["code"]
                code_mode = "命中预热Code"
                PRE_CODES.pop(ref, None)
            elif cached.get("task"):
                try:
                    code_mode = "等待预热任务" if not cached["task"].done() else "命中预热Code"
                    code = await cached["task"]
                    PRE_CODES.pop(ref, None)
                except Exception as e:
                    print(f"[Signin] [!] 预热任务异常: {e}")

        if not code:
            if cached:
                PRE_CODES.pop(ref, None)
            try:
                code = await yyb_service.get_code(ref, TEACHERMATE_APP_ID)
            except Exception as e:
                err_msg = str(e)
                if "expired" in err_msg or "re-scan" in err_msg or "409" in err_msg:
                    err_msg = "账号登录已过期，需重新扫码"
                return {"ref": ref, "success": False, "message": f"签到失败: {err_msg}"}
            
        code_duration = time.time() - code_start
        print(f"[Signin/Time] [CODE] {ref[:8]}... Code获取: {code_duration:.3f}s ({code_mode})")

        # 2. 发起直连请求（关闭自动重定向，直接在 302 阶段秒级捕获 Location 结果）
        client = get_signin_http_client()
        tm_start = time.time()
        
        resp = await client.get(
            f"{TEACHERMATE_SIGNIN_HOST}/api/v1/wechat/r",
            params={
                "isTeacher": "0",
                "m": "s_qr_sign",
                "extra": extra_hash,
                "code": code,
                "state": "",
            }
        )
        
        tm_duration = time.time() - tm_start
        final_url = resp.headers.get("location") or str(resp.url)
        if final_url.startswith("/"):
            final_url = f"{TEACHERMATE_SIGNIN_HOST}{final_url}"

        # 3. 授权失效现场自愈（仅在 Code 过期时触发单次刷新）
        if "open.weixin.qq.com" in final_url or "oauth2" in final_url:
            print(f"[Signin/Retry] ⚠️ {ref[:8]}... 授权 Code 过期，现场 0 延迟刷新重试...")
            try:
                fresh_code = await yyb_service.get_code(ref, TEACHERMATE_APP_ID)
                resp = await client.get(
                    f"{TEACHERMATE_SIGNIN_HOST}/api/v1/wechat/r",
                    params={
                        "isTeacher": "0",
                        "m": "s_qr_sign",
                        "extra": extra_hash,
                        "code": fresh_code,
                        "state": "",
                    }
                )
                final_url = resp.headers.get("location") or str(resp.url)
                if final_url.startswith("/"):
                    final_url = f"{TEACHERMATE_SIGNIN_HOST}{final_url}"
            except Exception as retry_err:
                print(f"[Signin/Retry] 刷新重试异常: {retry_err}")

        total_duration = time.time() - signin_start
        print(f"[Signin/Time] [API] {ref[:8]}... 签到接口响应: {tm_duration:.3f}s | 总耗时: {total_duration:.3f}s | 状态: {resp.status_code}")

        if "open.weixin.qq.com" in final_url or "oauth2" in final_url:
            return {"ref": ref, "success": False, "message": "微信授权已过期，请重新登录"}

        parsed = urlparse(final_url)
        qs = parse_qs(parsed.query)

        # 4. 从 302 Location URL 查询参数中极速解析结果（无需下载/渲染 HTML 页面，0 毫秒完成）
        rank = qs.get("rank", [None])[0] or qs.get("studentRank", [None])[0] or qs.get("signRank", [None])[0]
        success_param = qs.get("success", [None])[0]
        message_param = qs.get("message", [None])[0]

        # 如果返回了 HTML 页面（非 302 重定向），提取错误或名次
        html_text = ""
        if resp.status_code == 200:
            html_text = resp.text or ""
            if not rank:
                rank_m = re.search(r'"rank":\s*(\d+)', html_text) or re.search(r'"studentRank":\s*(\d+)', html_text) or re.search(r'第\s*(\d+)\s*名', html_text)
                if rank_m:
                    rank = rank_m.group(1)

        # 5. 错误关键词判定
        combined_text = f"{message_param or ''} {html_text}"
        if "不在签到范围" in combined_text or "不在" in combined_text and "范围" in combined_text:
            return {"ref": ref, "success": False, "message": "签到失败: 不在有效签到地理范围内"}
        if "二维码已过期" in combined_text or "二维码失效" in combined_text or "已失效" in combined_text:
            return {"ref": ref, "success": False, "message": "签到失败: 签到二维码已过期或失效"}
        if "签到已结束" in combined_text or "签到结束" in combined_text:
            return {"ref": ref, "success": False, "message": "签到已结束"}
        if "未加入该课程" in combined_text or "未加入课程" in combined_text:
            return {"ref": ref, "success": False, "message": "签到失败: 该账号未加入此课程"}

        # 6. 成功状态极速断定
        is_success = False
        if (
            success_param in ("1", "true")
            or "signresult" in parsed.path.lower()
            or "sign-result" in parsed.path.lower()
            or "签到成功" in combined_text
            or "已签到" in combined_text
            or (resp.status_code in (200, 302) and "error" not in parsed.path.lower() and not message_param)
        ):
            is_success = True

        if is_success:
            msg = f"签到成功 (第 {rank} 名)" if rank else (message_param or "签到成功")
            return {"ref": ref, "success": True, "message": msg, "rank": rank}
        else:
            msg = message_param or "签到未完成"
            return {"ref": ref, "success": False, "message": msg}

    except Exception as e:
        return {"ref": ref, "success": False, "message": str(e)}



# ── 纯无锁极速并发与多协议签到扩展 ──

import random

def add_jitter(coord_str: str, min_meters: float = 5.0, max_meters: float = 10.0) -> str:
    """
    对基准坐标施加 5~10 米的真实物理微扰动 (随机正负方向)，
    确保多账号并发打卡时每个账号坐标有微小独立偏差，完美防同坐标风控，
    同时严格将偏差锁定在 5~10 米的超高精度范围内。
    """
    try:
        val = float(coord_str)
        # 1 经纬度度数在赤道/中纬度地区约等于 111,000 米
        # 5~10 米对应的度数偏移量约为 0.000045° ~ 0.000090°
        dist_m = random.uniform(min_meters, max_meters)
        deg_offset = dist_m / 111000.0
        sign = random.choice([-1, 1])
        jitter = sign * deg_offset
        return f"{val + jitter:.5f}"
    except Exception:
        return coord_str


async def get_active_signs(ref: str) -> list[dict]:
    """查询指定账号当前是否有正在进行中的活跃签到活动"""
    session = get_tm_session(ref)
    try:
        data = await session.api_get("/v1/class-attendance/student/active_signs")
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and data.get("courseId"):
            return [data]
        return []
    except Exception as e:
        print(f"[TM/ActiveSigns] 查询活跃签到失败 ({ref[:10]}...): {e}")
        return []


async def do_normal_signin(ref: str, course_id: int, sign_id: int) -> dict:
    """模式一：执行普通一键签到（无定位要求，无二维码，全无锁秒级并发）"""
    session = get_tm_session(ref)
    try:
        resp = await session.api_post(
            "/v1/class-attendance/student-sign-in",
            {"courseId": course_id, "signId": sign_id}
        )
        if isinstance(resp, dict):
            rank = resp.get("studentRank") or resp.get("signRank")
            msg = f"普通签到成功 (第{rank}名)" if rank is not None else (resp.get("message") or "普通签到成功")
            return {"ref": ref, "success": True, "message": msg, "data": resp}
        return {"ref": ref, "success": True, "message": "普通签到成功", "data": resp}
    except Exception as e:
        return {"ref": ref, "success": False, "message": str(e)}


async def do_gps_signin(ref: str, course_id: int, sign_id: int, base_lat: str, base_lon: str) -> dict:
    """模式二：执行带物理散布扰动的 GPS 定位签到（全无锁秒级并发）"""
    session = get_tm_session(ref)
    lat = add_jitter(base_lat)
    lon = add_jitter(base_lon)
    try:
        resp = await session.api_post(
            "/v1/class-attendance/student-sign-in",
            {"courseId": course_id, "signId": sign_id, "lat": lat, "lon": lon}
        )
        if isinstance(resp, dict):
            rank = resp.get("studentRank") or resp.get("signRank")
            msg = f"GPS签到成功 (第{rank}名, 坐标:{lat},{lon})" if rank is not None else (resp.get("message") or f"GPS签到成功 ({lat},{lon})")
            return {"ref": ref, "success": True, "message": msg, "data": resp, "lat": lat, "lon": lon}
        return {"ref": ref, "success": True, "message": f"GPS签到成功 ({lat},{lon})", "data": resp, "lat": lat, "lon": lon}
    except Exception as e:
        return {"ref": ref, "success": False, "message": str(e), "lat": lat, "lon": lon}


async def listen_faye_qr_and_sign(course_id: int, sign_id: int, refs: list[str], timeout_sec: int = 15) -> dict:
    """微助教官方 Faye/Bayeux 协议长轮询监听动态二维码广播，并在捕获瞬间并发极速签到"""
    import json
    import re

    # 提前在后台并发预热所有目标账号的 Code，确保一旦截获二维码，0 秒延迟全员极速并发提交
    async def _pre_warm(r: str):
        try:
            code = await yyb_service.get_code(r, TEACHERMATE_APP_ID)
            PRE_CODES[r] = {"code": code, "timestamp": time.time(), "error": None}
        except Exception as e:
            PRE_CODES[r] = {"code": None, "timestamp": time.time(), "error": str(e)}

    async def _do_pre_warm():
        await asyncio.gather(*[_pre_warm(r) for r in refs], return_exceptions=True)

    asyncio.create_task(_do_pre_warm())

    faye_url = "https://www.teachermate.com.cn/faye"
    channel = f"/attendance/{course_id}/{sign_id}/qr"
    headers = {
        "User-Agent": WECHAT_USER_AGENT,
        "Content-Type": "application/json",
        "Origin": "https://www.teachermate.com.cn",
        "Referer": "https://www.teachermate.com.cn/"
    }

    start_time = time.time()

    try:
        async with httpx.AsyncClient(headers=headers, timeout=20) as client:
            # 1. 握手 (Handshake)
            handshake_body = [{"channel": "/meta/handshake", "version": "1.0", "supportedConnectionTypes": ["long-polling"], "id": "1"}]
            r = await client.post(faye_url, json=handshake_body)
            data = r.json()
            if not data or not data[0].get("successful"):
                return {"success": False, "message": "Faye 握手失败"}

            client_id = data[0].get("clientId")
            if not client_id:
                return {"success": False, "message": "Faye 未返回有效的 clientId"}

            # 2. 订阅签到频道 (Subscribe)
            sub_body = [{"channel": "/meta/subscribe", "clientId": client_id, "subscription": channel, "id": "2"}]
            r = await client.post(faye_url, json=sub_body)
            sub_data = r.json()
            if not sub_data or not sub_data[0].get("successful"):
                return {"success": False, "message": f"Faye 频道订阅失败: {sub_data}"}

            print(f"[Faye/Bayeux] 订阅频道成功: {channel}, 开始挂起长轮询监听 (最长 {timeout_sec}s)...")

            # 3. 维持长轮询连接循环 (Connect Loop)
            counter = 3
            while time.time() - start_time < timeout_sec:
                remain = max(1.0, timeout_sec - (time.time() - start_time))
                conn_body = [{"channel": "/meta/connect", "clientId": client_id, "connectionType": "long-polling", "id": str(counter)}]
                counter += 1
                try:
                    conn_resp = await client.post(faye_url, json=conn_body, timeout=remain + 2.0)
                    events = conn_resp.json()
                except (httpx.TimeoutException, asyncio.TimeoutError):
                    break
                except Exception as e:
                    print(f"[Faye/Bayeux] 连接轮询异常: {e}")
                    await asyncio.sleep(1)
                    continue

                has_qr_event = False
                for item in events:
                    # 捕获到动态二维码推送事件！
                    if item.get("channel") == channel and "data" in item:
                        qr_url = item["data"].get("qrUrl", "")
                        if qr_url:
                            has_qr_event = True
                            # 提取 32 位及以上十六进制 extra hash
                            match = re.search(r'([a-f0-9]{32,})', qr_url, re.IGNORECASE)
                            extra = match.group(1) if match else qr_url.split("/")[-1].split("?")[0]
                            print(f"[Faye/Bayeux] ⚡ 成功截获动态二维码: {qr_url} -> extra: {extra[:16]}... 立即触发高并发极速打卡！")

                            # 高并发为所有选中账号执行打卡
                            tasks = [do_signin(ref, extra) for ref in refs]
                            results = await asyncio.gather(*tasks, return_exceptions=True)

                            final_results = []
                            success_count = 0
                            for ref, res in zip(refs, results):
                                if isinstance(res, BaseException):
                                    final_results.append({"ref": ref, "success": False, "message": str(res)})
                                else:
                                    if res.get("success"):
                                        success_count += 1
                                    final_results.append(res)

                            return {
                                "success": True,
                                "qr_url": qr_url,
                                "extra": extra,
                                "results": final_results,
                                "total": len(final_results),
                                "success_count": success_count,
                            }

                if not has_qr_event:
                    await asyncio.sleep(1.0)

        return {
            "success": False,
            "message": f"Faye 监听等待超时 ({timeout_sec}s)，教师端未广播动态二维码（首码不走WS推送），请手动扫码"
        }
    except Exception as e:
        return {"success": False, "message": f"Faye 监听异常: {e}"}

