"""Hosted WebSocket AI answering engine.

Each ``group_key + lessonId`` receives an isolated runtime.  Manual client
answering remains in ``pages/index/answer-engine.js``; this process only handles
accounts whose ``ai_mode`` flag is true.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import aiohttp
import websockets

from ai_solver import solve_yuketang_problem_with_metadata
from safe_json_store import ACCOUNTS_STORE, HISTORY_STORE, PROBLEM_STATE_STORE, data_path
from ykt_monitor import send_wechat_alert


WS_URL = os.environ.get("YKT_WS_URL", "wss://changjiang.yuketang.cn/wsapp/").strip()
API_BASE_URL = os.environ.get("YKT_API_BASE", "https://changjiang.yuketang.cn").strip().rstrip("/")
ANSWER_CONCURRENCY = max(1, min(64, int(os.environ.get("YKT_BATCH_CONCURRENCY", "16"))))
REQUEST_TIMEOUT = max(3.0, float(os.environ.get("YKT_REQUEST_TIMEOUT", "12")))
AI_TIMEOUT = max(5.0, float(os.environ.get("YKT_AI_TIMEOUT", "55")))
SUBMIT_MIN_DELAY_SECONDS = max(
    0.0,
    float(
        os.environ.get(
            "YKT_SUBMIT_PREFERRED_DELAY",
            os.environ.get("YKT_SUBMIT_MIN_DELAY", "35"),
        )
    ),
)
SUBMIT_FALLBACK_DELAY_SECONDS = max(
    SUBMIT_MIN_DELAY_SECONDS,
    float(os.environ.get("YKT_SUBMIT_FALLBACK_DELAY", "40")),
)
SUBMIT_MAX_DELAY_SECONDS = max(
    SUBMIT_MIN_DELAY_SECONDS + 1.0,
    float(
        os.environ.get(
            "YKT_SUBMIT_HARD_LIMIT",
            os.environ.get("YKT_SUBMIT_MAX_DELAY", "60"),
        )
    ),
)
THINKING_CUTOFF_SECONDS = max(
    1.0,
    float(os.environ.get("YKT_AI_THINKING_CUTOFF", "25")),
)
SUBMIT_RESERVE_SECONDS = max(
    1.0,
    float(os.environ.get("YKT_SUBMIT_RESERVE", "6")),
)
DEADLINE_SAFETY_SECONDS = max(
    0.2,
    float(os.environ.get("YKT_DEADLINE_SAFETY", "1.5")),
)
MAX_IMAGE_BYTES = max(256 * 1024, int(os.environ.get("YKT_MAX_IMAGE_BYTES", str(5 * 1024 * 1024))))
POLL_INTERVAL = max(1.0, float(os.environ.get("YKT_WS_POLL_INTERVAL", "3")))
MAX_ACTIVE_SESSIONS = max(1, int(os.environ.get("YKT_MAX_ACTIVE_SESSIONS", "8")))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("ykt-ws")


def first_defined(*values):
    for value in values:
        if value is not None and value != "":
            return value
    return None


def to_epoch_ms(value) -> int | None:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number * 1000 if abs(number) < 100_000_000_000 else number


def safe_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def account_identity(account: dict) -> str:
    return str(account.get("phone") or account.get("uid") or account.get("id") or "")


def extract_inline_image_url(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        match = re.search(r'<img\s+[^>]*?src=["\']([^"\']+)["\']', value, re.I)
        if match:
            return match.group(1).strip()
        trimmed = value.strip()
        if trimmed.startswith(("http://", "https://", "//", "/")) and any(
            trimmed.lower().endswith(ext) or ext + "?" in trimmed.lower()
            for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp")
        ):
            return trimmed
    elif isinstance(value, list) and value:
        for item in value:
            found = extract_inline_image_url(item)
            if found:
                return found
    elif isinstance(value, dict):
        for k in ("url", "URL", "src", "path", "image", "cover", "pic", "picture", "slide_cover"):
            if k in value:
                found = extract_inline_image_url(value[k])
                if found:
                    return found
    return ""


@dataclass
class LessonRuntime:
    group_key: str
    lesson_id: str
    generation: int
    stopped: bool = False
    active_probe_uid: str = ""
    websocket: Any = None
    connection_task: asyncio.Task | None = None
    heartbeat_task: asyncio.Task | None = None
    problem_tasks: dict[str, asyncio.Task] = field(default_factory=dict)
    failed_probe_uids: set[str] = field(default_factory=set)
    closed_problem_ids: set[str] = field(default_factory=set)
    last_message_at: float = field(default_factory=time.monotonic)
    presentation_id: str = ""
    slide_id: str = ""
    slide_index: int | None = None

    @property
    def key(self) -> tuple[str, str]:
        return self.group_key, self.lesson_id


class YktWsEngine:
    def __init__(self):
        self.runtimes: dict[tuple[str, str], LessonRuntime] = {}
        self.poll_task: asyncio.Task | None = None
        self._generation = 0
        self._stopping = False

    def load_accounts(self) -> list[dict]:
        return ACCOUNTS_STORE.read()

    def _eligible(self, account: dict, runtime: LessonRuntime | None = None) -> bool:
        if account.get("expired") or not account.get("ai_mode"):
            return False
        if not account.get("cookie") or not account.get("lessonToken") or not account.get("uid"):
            return False
        if runtime is None:
            return bool(account.get("lessonId"))
        return (
            str(account.get("group_key") or "") == runtime.group_key
            and str(account.get("lessonId") or "") == runtime.lesson_id
        )

    def get_probe_account(self, runtime: LessonRuntime) -> dict | None:
        for account in self.load_accounts():
            if not self._eligible(account, runtime):
                continue
            if str(account.get("uid")) in runtime.failed_probe_uids:
                continue
            return account
        return None

    def get_ready_accounts(self, runtime: LessonRuntime) -> list[dict]:
        return [account for account in self.load_accounts() if self._eligible(account, runtime)]

    def websocket_url_for(self, account: dict) -> str:
        context = account.get("lessonContext") if isinstance(account.get("lessonContext"), dict) else {}
        candidate = str(
            first_defined(
                context.get("wssUrl"),
                context.get("wsUrl"),
                context.get("websocketUrl"),
                "",
            )
            or ""
        ).strip()
        if candidate:
            if candidate.startswith("//"):
                candidate = f"wss:{candidate}"
            elif candidate.startswith("https://"):
                candidate = f"wss://{candidate[len('https://'):]}"
            elif not candidate.startswith(("ws://", "wss://")):
                candidate = f"wss://{candidate}"
            parsed = urlparse(candidate)
            host = str(parsed.hostname or "").lower().rstrip(".")
            if parsed.scheme == "wss" and (
                host == "yuketang.cn" or host.endswith(".yuketang.cn")
            ):
                if parsed.path in {"", "/"}:
                    candidate = candidate.rstrip("/") + "/wsapp/"
                return candidate
        return WS_URL

    async def start(self):
        logger.info(
            "云端 AI WebSocket 引擎启动，提交并发=%s，地址=%s",
            ANSWER_CONCURRENCY,
            WS_URL,
        )
        self.poll_task = asyncio.create_task(self.poll_accounts_loop(), name="account-poller")
        try:
            await self.poll_task
        finally:
            await self.shutdown()

    async def shutdown(self):
        if self._stopping:
            return
        self._stopping = True
        runtimes = list(self.runtimes.values())
        await asyncio.gather(*(self.stop_runtime(runtime, "engine_shutdown") for runtime in runtimes))
        if self.poll_task and self.poll_task is not asyncio.current_task():
            self.poll_task.cancel()
            await asyncio.gather(self.poll_task, return_exceptions=True)

    async def poll_accounts_loop(self):
        while not self._stopping:
            try:
                active_keys = []
                for account in self.load_accounts():
                    if not self._eligible(account):
                        continue
                    key = (
                        str(account.get("group_key") or ""),
                        str(account.get("lessonId") or ""),
                    )
                    if key not in active_keys:
                        active_keys.append(key)

                for key in active_keys[:MAX_ACTIVE_SESSIONS]:
                    if key not in self.runtimes:
                        self._generation += 1
                        runtime = LessonRuntime(key[0], key[1], self._generation)
                        self.runtimes[key] = runtime
                        runtime.connection_task = asyncio.create_task(
                            self.connect_ws(runtime),
                            name=f"ws-{runtime.group_key}-{runtime.lesson_id}",
                        )
                        logger.info("启动 AI 课堂会话：group=%s lesson=%s", *key)
                        self.notify(
                            "云端 AI 已进入课堂",
                            f"课堂 <b>{runtime.lesson_id}</b> 的 WebSocket 监听已启动。",
                        )

                active_set = set(active_keys)
                stale = [runtime for key, runtime in self.runtimes.items() if key not in active_set]
                for runtime in stale:
                    await self.stop_runtime(runtime, "no_ready_accounts")
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("账号轮询异常")
            await asyncio.sleep(POLL_INTERVAL)

    def notify(self, title: str, content: str) -> None:
        asyncio.create_task(asyncio.to_thread(send_wechat_alert, title, content))

    async def connect_ws(self, runtime: LessonRuntime):
        reconnect_delay = 1
        while not runtime.stopped and runtime.generation == self._runtime_generation(runtime.key):
            probe = self.get_probe_account(runtime)
            if not probe:
                if runtime.failed_probe_uids:
                    logger.warning(
                        "课堂 %s 所有探针均失败，20 秒后清空失败列表重试",
                        runtime.lesson_id,
                    )
                    await asyncio.sleep(20)
                    runtime.failed_probe_uids.clear()
                    continue
                await asyncio.sleep(5)
                continue
            runtime.active_probe_uid = str(probe.get("uid"))
            try:
                logger.info(
                    "连接 WebSocket：lesson=%s probe=%s",
                    runtime.lesson_id,
                    runtime.active_probe_uid,
                )
                async with websockets.connect(
                    self.websocket_url_for(probe),
                    extra_headers={"User-Agent": "Android-mobile"},
                    ping_interval=None,
                    open_timeout=REQUEST_TIMEOUT,
                    close_timeout=5,
                    max_size=2 * 1024 * 1024,
                ) as websocket:
                    runtime.websocket = websocket
                    runtime.last_message_at = time.monotonic()
                    await websocket.send(
                        json.dumps(
                            {
                                "op": "hello",
                                "userid": probe.get("uid"),
                                "role": "student",
                                "auth": probe.get("lessonToken"),
                                "lessonid": safe_int(runtime.lesson_id, runtime.lesson_id),
                            }
                        )
                    )
                    runtime.heartbeat_task = asyncio.create_task(
                        self.heartbeat_loop(runtime, websocket),
                        name=f"heartbeat-{runtime.lesson_id}",
                    )
                    reconnect_delay = 1
                    async for message in websocket:
                        if runtime.stopped:
                            break
                        runtime.last_message_at = time.monotonic()
                        await self.process_message(runtime, message)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                if not runtime.stopped:
                    logger.warning("WebSocket 中断：lesson=%s error=%s", runtime.lesson_id, exc)
            finally:
                if runtime.heartbeat_task:
                    runtime.heartbeat_task.cancel()
                    await asyncio.gather(runtime.heartbeat_task, return_exceptions=True)
                    runtime.heartbeat_task = None
                runtime.websocket = None
            if not runtime.stopped:
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(15, reconnect_delay * 2)

    async def heartbeat_loop(self, runtime: LessonRuntime, websocket):
        while not runtime.stopped and runtime.websocket is websocket:
            try:
                await websocket.send(
                    json.dumps(
                        {
                            "op": "detectlesson",
                            "lessonid": safe_int(runtime.lesson_id, runtime.lesson_id),
                        }
                    )
                )
                pong = await websocket.ping()
                await asyncio.wait_for(pong, timeout=10)
                await asyncio.sleep(15)
            except asyncio.CancelledError:
                raise
            except Exception:
                try:
                    await websocket.close()
                except Exception:
                    pass
                return

    def _runtime_generation(self, key: tuple[str, str]) -> int:
        runtime = self.runtimes.get(key)
        return runtime.generation if runtime else -1

    def _message_matches_lesson(self, runtime: LessonRuntime, data: dict) -> bool:
        nested = data.get("data") if isinstance(data.get("data"), dict) else {}
        lesson = first_defined(
            data.get("lessonid"),
            data.get("lessonId"),
            nested.get("lessonid"),
            nested.get("lessonId"),
            (data.get("problem") or {}).get("lessonid") if isinstance(data.get("problem"), dict) else None,
        )
        return lesson in {None, ""} or str(lesson) == runtime.lesson_id

    async def process_message(self, runtime: LessonRuntime, message):
        try:
            data = json.loads(message)
        except (TypeError, json.JSONDecodeError):
            return
        if not isinstance(data, dict) or not self._message_matches_lesson(runtime, data):
            return
        op = str(data.get("op") or data.get("operation") or "").lower()

        if op == "hello":
            nested = data.get("data") if isinstance(data.get("data"), dict) else {}
            hello = {**data, **nested}
            if (
                hello.get("isEnd") is True
                or hello.get("ended") is True
                or re.search(
                    r"finish|ended|closed|已结束|已关闭",
                    str(hello.get("lessonStatus") or hello.get("status") or ""),
                    re.I,
                )
            ):
                self.clear_lesson_tokens(runtime.group_key, runtime.lesson_id)
                await self.stop_runtime(runtime, "lesson_finished_on_hello")
                return
            failed = hello.get("success") is False or (
                hello.get("code") not in {None, "", 0, "0"}
            )
            if failed:
                runtime.failed_probe_uids.add(runtime.active_probe_uid)
                logger.error(
                    "WebSocket hello 鉴权失败：lesson=%s probe=%s",
                    runtime.lesson_id,
                    runtime.active_probe_uid,
                )
                if runtime.websocket:
                    await runtime.websocket.close()
            else:
                runtime.failed_probe_uids.clear()
                logger.info("WebSocket 鉴权成功：lesson=%s", runtime.lesson_id)
                self.consume_presentation_state(runtime, hello)
                self.schedule_unlocked_problem(runtime, hello)
            return

        if op in {"showpresentation", "slidenav", "presentationupdated"}:
            nested = data.get("data") if isinstance(data.get("data"), dict) else {}
            payload = {**data, **nested}
            self.consume_presentation_state(runtime, payload)
            self.schedule_unlocked_problem(runtime, payload)
            return

        if op in {
            "unlockproblem",
            "unlock_problem",
            "sendsproblem",
            "sendproblem",
            "sproblemshown",
            "problemshown",
            "probleminfo",
        }:
            problem = (
                {**data, **data["problem"]}
                if isinstance(data.get("problem"), dict)
                else dict(data)
            )
            if not first_defined(
                problem.get("problemid"),
                problem.get("problemId"),
                problem.get("id"),
                problem.get("prob"),
            ):
                inferred = first_defined(
                    data.get("problemid"),
                    data.get("problemId"),
                    data.get("spid"),
                    data.get("prob"),
                    data.get("problem") if not isinstance(data.get("problem"), dict) else None,
                )
                if inferred is not None:
                    problem["problemid"] = inferred
            if not first_defined(problem.get("pres"), problem.get("presentationId")):
                problem["pres"] = runtime.presentation_id
            if not first_defined(problem.get("sid"), problem.get("slideId")):
                problem["sid"] = runtime.slide_id
            if runtime.slide_index is not None and safe_int(problem.get("si")) is None:
                problem["si"] = runtime.slide_index
            self.schedule_problem(runtime, problem, data)
            return

        if op == "extendtime":
            problem = (
                {**data, **data["problem"]}
                if isinstance(data.get("problem"), dict)
                else dict(data)
            )
            inferred = first_defined(
                problem.get("problemid"),
                problem.get("problemId"),
                problem.get("prob"),
                data.get("problemid"),
                data.get("problemId"),
                data.get("spid"),
                data.get("prob"),
                data.get("problem") if not isinstance(data.get("problem"), dict) else None,
            )
            if inferred is not None:
                problem["problemid"] = inferred
                # If the original task already finished unsuccessfully, an
                # extension gets one fresh chance. Active tasks continue and
                # still obey the global 60-second safety ceiling.
                state = self._read_problem_state(runtime, str(inferred))
                if state.get("status") not in {"completed", "closed"}:
                    self.schedule_problem(runtime, problem, data)
            return

        if op in {"problemfinished", "finishproblem"}:
            problem_id = str(
                first_defined(
                    data.get("problemid"),
                    data.get("problemId"),
                    data.get("spid"),
                    data.get("prob"),
                    "",
                )
            )
            await self.close_problem(runtime, problem_id)
            return

        if op in {"lessonfinished", "finishlesson", "endlesson", "lessonend"}:
            logger.info("收到课堂结束信号：group=%s lesson=%s", runtime.group_key, runtime.lesson_id)
            self.notify("课堂已结束", f"课堂 <b>{runtime.lesson_id}</b> 的 AI 监听已释放。")
            self.clear_lesson_tokens(runtime.group_key, runtime.lesson_id)
            await self.stop_runtime(runtime, "lesson_finished")

    def consume_presentation_state(self, runtime: LessonRuntime, data: dict) -> None:
        presentation = data.get("presentation")
        if isinstance(presentation, dict):
            presentation = first_defined(
                presentation.get("id"),
                presentation.get("presentationId"),
                presentation.get("presentation_id"),
            )
        runtime.presentation_id = str(
            first_defined(
                presentation,
                data.get("pres"),
                data.get("presentationId"),
                data.get("presentation_id"),
                runtime.presentation_id,
                "",
            )
            or ""
        )
        runtime.slide_id = str(
            first_defined(
                data.get("slideid"),
                data.get("slideId"),
                data.get("sid"),
                runtime.slide_id,
                "",
            )
            or ""
        )
        slide_index = safe_int(
            first_defined(
                data.get("slideindex"),
                data.get("slideIndex"),
                data.get("si"),
                runtime.slide_index,
            )
        )
        if slide_index is not None:
            runtime.slide_index = slide_index

    def schedule_unlocked_problem(self, runtime: LessonRuntime, data: dict) -> None:
        unlocked = first_defined(data.get("unlockedproblem"), data.get("unlockedProblem"))
        if not isinstance(unlocked, list) or not unlocked:
            return
        latest = unlocked[-1]
        if isinstance(latest, dict):
            problem = dict(latest)
        else:
            if runtime.websocket:
                asyncio.create_task(
                    self.request_problem_info(runtime, str(latest)),
                    name=f"recover-problem-{runtime.lesson_id}-{latest}",
                )
            return
        if not first_defined(problem.get("pres"), problem.get("presentationId")):
            problem["pres"] = runtime.presentation_id
        if not first_defined(problem.get("sid"), problem.get("slideId")):
            problem["sid"] = runtime.slide_id
        if runtime.slide_index is not None and safe_int(problem.get("si")) is None:
            problem["si"] = runtime.slide_index
        self.schedule_problem(runtime, problem, data)

    async def request_problem_info(self, runtime: LessonRuntime, problem_id: str) -> None:
        websocket = runtime.websocket
        if not websocket or runtime.stopped:
            return
        try:
            await websocket.send(
                json.dumps(
                    {
                        "op": "probleminfo",
                        "lessonid": safe_int(runtime.lesson_id, runtime.lesson_id),
                        "problemid": safe_int(problem_id, problem_id),
                        "msgid": "1",
                    }
                )
            )
        except Exception:
            logger.debug(
                "恢复题目信息请求失败：lesson=%s problem=%s",
                runtime.lesson_id,
                problem_id,
            )

    def schedule_problem(self, runtime: LessonRuntime, problem: dict, raw: dict):
        problem_id = first_defined(
            problem.get("problemid"),
            problem.get("problemId"),
            problem.get("id"),
            problem.get("prob"),
        )
        if problem_id is None or str(problem_id).strip() in {"", "None", "null"}:
            logger.warning("忽略缺少 problemId 的题目消息")
            return
        problem_id = str(problem_id)
        if problem_id in runtime.closed_problem_ids:
            return
        task = runtime.problem_tasks.get(problem_id)
        if task and not task.done():
            return
        state = self._read_problem_state(runtime, problem_id)
        if state.get("status") == "completed":
            logger.info("题目 %s 已持久化完成，跳过重复事件", problem_id)
            return
        captured_generation = runtime.generation
        task = asyncio.create_task(
            self.handle_new_problem(runtime, problem, raw, captured_generation),
            name=f"problem-{runtime.lesson_id}-{problem_id}",
        )
        runtime.problem_tasks[problem_id] = task

        def cleanup(finished: asyncio.Task):
            if runtime.problem_tasks.get(problem_id) is finished:
                runtime.problem_tasks.pop(problem_id, None)
            try:
                finished.result()
            except asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("题目任务异常：%s", problem_id)

        task.add_done_callback(cleanup)

    async def close_problem(self, runtime: LessonRuntime, problem_id: str):
        if not problem_id:
            problem_ids = list(runtime.problem_tasks)
        else:
            problem_ids = [problem_id]
        for item in problem_ids:
            runtime.closed_problem_ids.add(item)
            task = runtime.problem_tasks.get(item)
            if task and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            self._write_problem_state(runtime, item, "closed", "teacher_closed")

    def _problem_state_key(self, runtime: LessonRuntime, problem_id: str) -> str:
        return f"{runtime.group_key}|{runtime.lesson_id}|{problem_id}"

    def _read_problem_state(self, runtime: LessonRuntime, problem_id: str) -> dict:
        return PROBLEM_STATE_STORE.read().get(self._problem_state_key(runtime, problem_id), {})

    def _write_problem_state(
        self,
        runtime: LessonRuntime,
        problem_id: str,
        status: str,
        error: str = "",
        **details,
    ):
        key = self._problem_state_key(runtime, problem_id)

        def mutate(states: dict):
            state = dict(states.get(key) or {})
            state.update(
                {
                "groupKey": runtime.group_key,
                "lessonId": runtime.lesson_id,
                "problemId": problem_id,
                "status": status,
                "error": str(error)[:500],
                "updatedAt": int(time.time() * 1000),
                }
            )
            state.update(details)
            states[key] = state
            if len(states) > 2000:
                oldest = sorted(states, key=lambda item: int(states[item].get("updatedAt") or 0))
                for stale_key in oldest[: len(states) - 1500]:
                    states.pop(stale_key, None)

        PROBLEM_STATE_STORE.update(mutate)

    def _runtime_active(self, runtime: LessonRuntime, generation: int, problem_id: str) -> bool:
        return (
            not runtime.stopped
            and runtime.generation == generation
            and self.runtimes.get(runtime.key) is runtime
            and problem_id not in runtime.closed_problem_ids
        )

    def _problem_started_from(
        self,
        problem: dict,
        raw: dict,
        fallback_ms: int | None = None,
    ) -> int:
        started = to_epoch_ms(
            first_defined(
                problem.get("dt"),
                problem.get("sendTime"),
                problem.get("send_time"),
                raw.get("dt"),
                raw.get("sendTime"),
                raw.get("send_time"),
                raw.get("now"),
            )
        )
        return started if started is not None else (fallback_ms or int(time.time() * 1000))

    def _deadline_from(
        self,
        problem: dict,
        raw: dict,
        started_at_ms: int | None = None,
    ) -> int | None:
        limit = safe_int(
            first_defined(
                problem.get("limit"),
                problem.get("limit_time"),
                problem.get("limitTime"),
                problem.get("timeLimit"),
                raw.get("limit"),
                raw.get("limit_time"),
                raw.get("limitTime"),
                raw.get("timeLimit"),
            )
        )
        if limit == -1:
            return None
        if limit is None:
            return None
        extend = safe_int(
            first_defined(
                problem.get("extend"),
                problem.get("extended_time"),
                problem.get("extendTime"),
                raw.get("extend"),
                raw.get("extended_time"),
                raw.get("extendTime"),
            ),
            0,
        ) or 0
        started = started_at_ms or self._problem_started_from(problem, raw)
        return started + max(0, limit + extend) * 1000

    def _submission_timing_from(
        self,
        problem: dict,
        raw: dict,
        received_at_ms: int | None = None,
    ) -> dict[str, int | None]:
        received_at_ms = received_at_ms or int(time.time() * 1000)
        started_at_ms = self._problem_started_from(problem, raw, received_at_ms)
        teacher_deadline_ms = self._deadline_from(problem, raw, started_at_ms)
        hard_deadline_ms = started_at_ms + int(SUBMIT_MAX_DELAY_SECONDS * 1000)
        if teacher_deadline_ms is not None:
            hard_deadline_ms = min(
                hard_deadline_ms,
                teacher_deadline_ms - int(DEADLINE_SAFETY_SECONDS * 1000),
            )
        available_seconds = max(0.0, (hard_deadline_ms - received_at_ms) / 1000)
        effective_reserve_seconds = min(
            SUBMIT_RESERVE_SECONDS,
            max(1.0, available_seconds * 0.25),
        )
        analysis_deadline_ms = hard_deadline_ms - int(
            effective_reserve_seconds * 1000
        )
        preferred_submit_at_ms = started_at_ms + int(
            SUBMIT_MIN_DELAY_SECONDS * 1000
        )
        return {
            "started_at_ms": started_at_ms,
            "teacher_deadline_ms": teacher_deadline_ms,
            "hard_deadline_ms": hard_deadline_ms,
            "analysis_deadline_ms": analysis_deadline_ms,
            "submit_not_before_ms": min(
                preferred_submit_at_ms,
                analysis_deadline_ms,
            ),
            "thinking_cutoff_ms": started_at_ms
            + int(THINKING_CUTOFF_SECONDS * 1000),
        }

    def _problem_open(
        self,
        runtime: LessonRuntime,
        generation: int,
        problem_id: str,
        deadline: int | None,
    ) -> bool:
        return self._runtime_active(runtime, generation, problem_id) and (
            deadline is None or int(time.time() * 1000) < deadline
        )

    async def handle_new_problem(
        self,
        runtime: LessonRuntime,
        problem: dict,
        raw: dict,
        generation: int,
    ):
        started = time.monotonic()
        received_at_ms = int(time.time() * 1000)
        problem_id = str(
            first_defined(
                problem.get("problemid"),
                problem.get("problemId"),
                problem.get("id"),
                problem.get("prob"),
            )
        )
        timing = self._submission_timing_from(problem, raw, received_at_ms)
        problem_started_at_ms = int(timing["started_at_ms"])
        teacher_deadline_ms = timing["teacher_deadline_ms"]
        deadline = int(timing["hard_deadline_ms"])
        analysis_deadline_ms = int(timing["analysis_deadline_ms"])
        submit_not_before_ms = int(timing["submit_not_before_ms"])
        thinking_cutoff_ms = int(timing["thinking_cutoff_ms"])
        self._write_problem_state(
            runtime,
            problem_id,
            "processing",
            stage="preparing",
            problemStartedAt=problem_started_at_ms,
            receivedAt=received_at_ms,
            teacherDeadlineAt=teacher_deadline_ms,
            submitNotBeforeAt=submit_not_before_ms,
            hardDeadlineAt=deadline,
        )
        try:
            if deadline <= received_at_ms:
                raise RuntimeError("problem deadline already expired when received")
            problem_type = first_defined(problem.get("problemType"), problem.get("type"))
            body = first_defined(problem.get("body"), problem.get("content"), problem.get("title"), "")
            options = first_defined(problem.get("options"), problem.get("choices"), []) or []
            blanks = problem.get("blanks") if isinstance(problem.get("blanks"), list) else []
            polling_count = safe_int(
                first_defined(
                    problem.get("pollingCount"),
                    problem.get("maxSelect"),
                    problem.get("max_select"),
                    raw.get("pollingCount"),
                    raw.get("maxSelect"),
                    raw.get("max_select"),
                ),
                1,
            ) or 1
            cover = first_defined(
                problem.get("cover"),
                problem.get("slide_cover"),
                problem.get("image"),
                problem.get("picture"),
                problem.get("pic"),
                extract_inline_image_url(problem.get("pics")),
                extract_inline_image_url(problem.get("images")),
                extract_inline_image_url(body),
                "",
            )
            correct_answer = first_defined(problem.get("answer"), problem.get("correct_answer"), problem.get("solution"))
            presentation_id = first_defined(
                problem.get("pres"),
                problem.get("presentationId"),
                problem.get("presentation_id"),
                raw.get("pres"),
                raw.get("presentationId"),
                raw.get("presentation_id"),
                "",
            )
            slide_id = first_defined(
                problem.get("sid"),
                problem.get("slideId"),
                raw.get("sid"),
                raw.get("slideId"),
                "",
            )

            connector = aiohttp.TCPConnector(limit=max(ANSWER_CONCURRENCY * 2, 32))
            timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
            async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
                if (not body or not options or problem_type is None) and presentation_id:
                    probe = self.get_probe_account(runtime)
                    if probe:
                        presentation = await self.fetch_presentation(session, probe, str(presentation_id))
                        extracted = self.extract_problem(presentation or {}, problem_id, str(slide_id or ""))
                        if extracted:
                            body = body or extracted.get("body", "")
                            options = options or extracted.get("options", [])
                            cover = cover or extracted.get("cover", "")
                            if problem_type is None:
                                problem_type = extracted.get("problemType")
                            if not blanks and isinstance(extracted.get("blanks"), list):
                                blanks = extracted["blanks"]
                            polling_count = safe_int(
                                first_defined(
                                    extracted.get("pollingCount"),
                                    polling_count,
                                ),
                                1,
                            ) or 1

                problem_type = safe_int(problem_type)
                if problem_type not in {0, 1, 2, 3, 4}:
                    raise ValueError(f"unknown problem type: {problem_type!r}")
                body = self.normalize_rich_text(body)
                options = self.normalize_options(options)
                if problem_type in {0, 1, 2} and not options:
                    raise ValueError("selection problem metadata has no options")
                if not body and not cover:
                    raise ValueError("question body and cover are both empty")
                if not self._problem_open(runtime, generation, problem_id, deadline):
                    return

                image_bytes = await self.download_cover_image(session, str(cover)) if cover else None
                self.notify(
                    "AI 捕获到新题",
                    f"课堂 {runtime.lesson_id}，题目 {problem_id}，正在分析。",
                )
                remaining_ai_seconds = (
                    analysis_deadline_ms - int(time.time() * 1000)
                ) / 1000
                if remaining_ai_seconds <= 0.5:
                    raise RuntimeError("no time budget remains for AI analysis")
                ai_budget_seconds = min(AI_TIMEOUT, remaining_ai_seconds)
                thinking_budget_seconds = max(
                    0.0,
                    (thinking_cutoff_ms - int(time.time() * 1000)) / 1000,
                )
                self._write_problem_state(
                    runtime,
                    problem_id,
                    "processing",
                    stage="ai_analyzing",
                    aiBudgetSeconds=round(ai_budget_seconds, 2),
                    thinkingCutoffAt=thinking_cutoff_ms,
                )
                ai_answers, ai_error, ai_metadata = await asyncio.wait_for(
                    asyncio.to_thread(
                        solve_yuketang_problem_with_metadata,
                        problem_type,
                        body,
                        options,
                        image_bytes,
                        ai_budget_seconds,
                        thinking_budget_seconds,
                        len(blanks) or None,
                        polling_count,
                    ),
                    timeout=ai_budget_seconds + 1.0,
                )
                if not ai_answers:
                    raise RuntimeError(
                        f"all AI routes returned no validated answer: {ai_error}"
                    )
                if not self._problem_open(runtime, generation, problem_id, deadline):
                    return

                answer_ready_at_ms = int(time.time() * 1000)
                self._write_problem_state(
                    runtime,
                    problem_id,
                    "processing",
                    stage="waiting_submit",
                    aiProvider=str(ai_metadata.get("provider") or ""),
                    aiModel=str(ai_metadata.get("model") or ""),
                    aiAttemptCount=int(ai_metadata.get("attemptCount") or 0),
                    aiFallbackUsed=bool(ai_metadata.get("fallbackUsed")),
                    answerReadyAt=answer_ready_at_ms,
                )
                target_delay = float(
                    ai_metadata.get("targetSubmitDelaySeconds")
                    or (
                        SUBMIT_FALLBACK_DELAY_SECONDS
                        if ai_metadata.get("fallbackUsed")
                        else SUBMIT_MIN_DELAY_SECONDS
                    )
                )
                target_submit_at_ms = problem_started_at_ms + int(target_delay * 1000)
                effective_submit_at_ms = min(target_submit_at_ms, analysis_deadline_ms)
                wait_seconds = max(
                    0.0,
                    (effective_submit_at_ms - int(time.time() * 1000)) / 1000,
                )
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                if not self._problem_open(runtime, generation, problem_id, deadline):
                    return

                ready_accounts = self.get_ready_accounts(runtime)
                if not ready_accounts:
                    raise RuntimeError("no AI-hosted account is ready")

                submit_started_at_ms = int(time.time() * 1000)
                self._write_problem_state(
                    runtime,
                    problem_id,
                    "processing",
                    stage="submitting",
                    submitStartedAt=submit_started_at_ms,
                    totalAccounts=len(ready_accounts),
                )
                semaphore = asyncio.Semaphore(ANSWER_CONCURRENCY)

                async def submit_one(account: dict):
                    async with semaphore:
                        if not self._problem_open(runtime, generation, problem_id, deadline):
                            return False, self.account_summary(account)
                        return await self.submit_answer(
                            session,
                            runtime,
                            generation,
                            deadline,
                            account,
                            problem_id,
                            problem_type,
                            ai_answers,
                        )

                pending_accounts = list(ready_accounts)
                success_by_identity: dict[str, dict] = {}
                for submit_round in range(1, 3):
                    remaining_seconds = (
                        deadline - int(time.time() * 1000)
                    ) / 1000
                    if not pending_accounts or remaining_seconds <= 0.25:
                        break
                    self._write_problem_state(
                        runtime,
                        problem_id,
                        "processing",
                        stage="submitting",
                        submitRound=submit_round,
                        pendingAccounts=len(pending_accounts),
                    )
                    task_accounts = {
                        asyncio.create_task(
                            submit_one(account),
                            name=(
                                f"submit-{problem_id}-r{submit_round}-"
                                f"{account_identity(account)}"
                            ),
                        ): account
                        for account in pending_accounts
                    }
                    done, pending = await asyncio.wait(
                        task_accounts,
                        timeout=max(0.1, remaining_seconds),
                    )
                    for task in pending:
                        task.cancel()
                    if pending:
                        await asyncio.gather(*pending, return_exceptions=True)

                    failed_accounts = [
                        task_accounts[task]
                        for task in pending
                    ]
                    for task in done:
                        account = task_accounts[task]
                        if task.cancelled() or task.exception() is not None:
                            failed_accounts.append(account)
                            continue
                        ok, account_info = task.result()
                        if ok:
                            success_by_identity[account_identity(account)] = account_info
                        else:
                            failed_accounts.append(account)

                    if submit_round == 1 and failed_accounts:
                        still_ready = {
                            account_identity(account)
                            for account in self.get_ready_accounts(runtime)
                        }
                        pending_accounts = [
                            account
                            for account in failed_accounts
                            if account_identity(account) in still_ready
                        ]
                        if pending_accounts and deadline - int(time.time() * 1000) > 500:
                            await asyncio.sleep(0.25)
                    else:
                        pending_accounts = failed_accounts
                successes = list(success_by_identity.values())
                failed_count = len(ready_accounts) - len(successes)
                elapsed = round(time.monotonic() - started, 2)
                completed_at_ms = int(time.time() * 1000)
                self.record_ai_history(
                    runtime=runtime,
                    problem_id=problem_id,
                    problem_type=problem_type,
                    body=body,
                    options=options,
                    ai_answers=ai_answers,
                    correct_answer=correct_answer,
                    cover=cover,
                    elapsed=elapsed,
                    success_accounts=successes,
                    total_accounts=len(ready_accounts),
                    ai_provider=str(ai_metadata.get("provider") or ""),
                    ai_model=str(ai_metadata.get("model") or ""),
                    ai_attempts=list(ai_metadata.get("attempts") or []),
                    ai_fallback_used=bool(ai_metadata.get("fallbackUsed")),
                    problem_started_at=problem_started_at_ms,
                    answer_ready_seconds=round(
                        max(0, answer_ready_at_ms - problem_started_at_ms) / 1000,
                        2,
                    ),
                    submit_started_seconds=round(
                        max(0, submit_started_at_ms - problem_started_at_ms) / 1000,
                        2,
                    ),
                    submitted_seconds=round(
                        max(0, completed_at_ms - problem_started_at_ms) / 1000,
                        2,
                    ),
                    hard_deadline_at=deadline,
                )
                self._write_problem_state(
                    runtime,
                    problem_id,
                    "completed" if successes else "failed",
                    "" if successes else "all submissions failed",
                    stage="completed" if successes else "failed",
                    successCount=len(successes),
                    failedCount=failed_count,
                    completedAt=completed_at_ms,
                )
                self.notify(
                    "AI 批量答题完成",
                    f"课堂 {runtime.lesson_id}，题目 {problem_id}：成功 {len(successes)}/{len(ready_accounts)}，耗时 {elapsed} 秒。",
                )
        except asyncio.CancelledError:
            self._write_problem_state(runtime, problem_id, "cancelled", "session_or_problem_closed")
            raise
        except Exception as exc:
            logger.exception(
                "题目处理失败：group=%s lesson=%s problem=%s",
                runtime.group_key,
                runtime.lesson_id,
                problem_id,
            )
            self._write_problem_state(runtime, problem_id, "failed", str(exc))
            self.notify("AI 题目处理失败", f"题目 {problem_id}：{str(exc)[:160]}")

    async def fetch_presentation(self, session, probe: dict, presentation_id: str) -> dict | None:
        url = (
            f"{API_BASE_URL}/api/v3/lesson/presentation/fetch"
            f"?presentation_id={presentation_id}"
        )
        headers = self.account_headers(probe, include_lesson_token=False)
        for attempt in range(3):
            try:
                async with session.get(url, headers=headers) as response:
                    try:
                        data = await response.json(content_type=None)
                    except (ValueError, TypeError):
                        data = {}
                    if response.status == 200 and isinstance(data, dict):
                        if data.get("code") in {None, 0, "0"} or data.get("success") is True:
                            return data.get("data", data)
                    if response.status in {401, 403}:
                        return None
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
            if attempt < 2:
                await asyncio.sleep(0.5 * (2**attempt))
        return None

    def _presentation_payload(self, presentation: dict) -> dict:
        data = presentation if isinstance(presentation, dict) else {}
        for _ in range(3):
            nested = data.get("data")
            if not isinstance(nested, dict):
                break
            if any(key in data for key in ("slides", "problems", "presentation", "presentationData")):
                break
            data = nested
        return data

    def _presentation_lists(self, presentation: dict) -> tuple[list, list]:
        data = self._presentation_payload(presentation)
        nested_sources = [
            data,
            data.get("presentation") if isinstance(data.get("presentation"), dict) else {},
            data.get("presentationData") if isinstance(data.get("presentationData"), dict) else {},
        ]
        slides = next(
            (source.get("slides") for source in nested_sources if isinstance(source.get("slides"), list)),
            [],
        )
        problems = next(
            (source.get("problems") for source in nested_sources if isinstance(source.get("problems"), list)),
            [],
        )
        return slides, problems

    def extract_problem(self, presentation: dict, problem_id: str, slide_id: str = "") -> dict:
        slides, top_level_problems = self._presentation_lists(presentation)
        candidates: list[tuple[dict, dict]] = []
        for slide in slides:
            if not isinstance(slide, dict):
                continue
            problem = slide.get("problem")
            if isinstance(problem, dict):
                candidates.append((slide, problem))
        for problem in top_level_problems:
            if isinstance(problem, dict):
                matched_slide = {}
                problem_slide_id = str(
                    first_defined(problem.get("slideId"), problem.get("lessonSlideID"), "")
                    or ""
                )
                problem_slide_index = safe_int(problem.get("slideIndex"))
                for slide in slides:
                    if not isinstance(slide, dict):
                        continue
                    current_slide_id = str(
                        first_defined(
                            slide.get("lessonSlideID"),
                            slide.get("lesson_slide_id"),
                            slide.get("id"),
                            "",
                        )
                        or ""
                    )
                    current_index = safe_int(slide.get("index"))
                    if (
                        problem_slide_id
                        and current_slide_id == problem_slide_id
                    ) or (
                        problem_slide_index is not None
                        and current_index == problem_slide_index
                    ):
                        matched_slide = slide
                        break
                candidates.append((matched_slide, problem))

        for slide, problem in candidates:
            pid = str(first_defined(problem.get("problemId"), problem.get("problemid"), problem.get("id"), ""))
            sid = str(first_defined(slide.get("lessonSlideID"), slide.get("id"), ""))
            if (pid and pid == problem_id) or (slide_id and sid == slide_id):
                return self.extract_content(slide, problem)
        return self.extract_content(*candidates[-1]) if candidates else {}

    def extract_content(self, slide: dict, problem: dict) -> dict:
        body = first_defined(problem.get("body"), problem.get("content"), problem.get("title"), "")
        cover = first_defined(
            slide.get("cover"),
            slide.get("coverAlt"),
            slide.get("thumbnail"),
            self._shape_resource(slide.get("shapes")),
            problem.get("cover"),
            problem.get("slide_cover"),
            problem.get("image"),
            problem.get("picture"),
            problem.get("pic"),
            extract_inline_image_url(problem.get("pics")),
            extract_inline_image_url(problem.get("images")),
            extract_inline_image_url(body),
            "",
        )
        return {
            "body": body,
            "options": self.normalize_options(first_defined(problem.get("options"), problem.get("choices"), [])),
            "cover": self._normalize_resource_url(cover),
            "problemType": first_defined(problem.get("problemType"), problem.get("type")),
            "blanks": problem.get("blanks") if isinstance(problem.get("blanks"), list) else [],
            "pollingCount": first_defined(
                problem.get("pollingCount"),
                problem.get("maxSelect"),
                problem.get("max_select"),
                1,
            ),
        }

    def _shape_resource(self, shapes) -> str:
        if not isinstance(shapes, list):
            return ""
        for shape in shapes:
            if not isinstance(shape, dict):
                continue
            direct = first_defined(
                shape.get("URL"),
                shape.get("url"),
                shape.get("src"),
                shape.get("image"),
                shape.get("picture"),
            )
            if isinstance(direct, dict):
                direct = first_defined(
                    direct.get("url"),
                    direct.get("URL"),
                    direct.get("src"),
                    direct.get("path"),
                )
            if direct:
                return str(direct)
            nested = self._shape_resource(first_defined(shape.get("shapes"), shape.get("children")))
            if nested:
                return nested
        return ""

    def _normalize_resource_url(self, value) -> str:
        if isinstance(value, dict):
            value = first_defined(
                value.get("url"),
                value.get("URL"),
                value.get("src"),
                value.get("path"),
            )
        raw = str(value or "").strip()
        if not raw:
            return ""
        if raw.startswith("//"):
            return f"https:{raw}"
        return urljoin(f"{API_BASE_URL}/", raw)

    def normalize_options(self, raw_options) -> list[dict]:
        options = []
        for index, option in enumerate(raw_options if isinstance(raw_options, list) else []):
            if isinstance(option, dict):
                key = first_defined(option.get("key"), option.get("id"), chr(65 + index))
                value = first_defined(option.get("value"), option.get("label"), option.get("content"), "")
            else:
                key = chr(65 + index)
                value = option
            options.append({"key": str(key), "value": self.normalize_rich_text(value)})
        return options

    def normalize_rich_text(self, value) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            return self.normalize_rich_text(
                first_defined(
                    value.get("html"),
                    value.get("content"),
                    value.get("text"),
                    value.get("value"),
                    "",
                )
            )
        if isinstance(value, list):
            return " ".join(
                item
                for item in (self.normalize_rich_text(entry) for entry in value)
                if item
            )
        return str(value)

    def _cover_host_allowed(self, hostname: str) -> bool:
        host = hostname.lower().rstrip(".")
        # Cover URLs come from the authenticated presentation response and may
        # use changing CDN domains.  Public-address validation below remains
        # mandatory; operators can additionally enable a strict host list.
        if os.environ.get("YKT_STRICT_COVER_HOSTS", "0") != "1":
            return True
        if host == "yuketang.cn" or host.endswith(".yuketang.cn"):
            return True
        configured = {
            item.strip().lower()
            for item in os.environ.get("YKT_COVER_IMAGE_HOSTS", "").split(",")
            if item.strip()
        }
        return host in configured

    async def download_cover_image(self, session, url: str) -> bytes | None:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return None
        if not self._cover_host_allowed(parsed.hostname):
            logger.warning("跳过未允许的课件图片域名：%s", parsed.hostname)
            return None
        try:
            addresses = await asyncio.to_thread(
                socket.getaddrinfo,
                parsed.hostname,
                parsed.port or (443 if parsed.scheme == "https" else 80),
                0,
                socket.SOCK_STREAM,
            )
            if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
                return None
            async with session.get(url, allow_redirects=False) as response:
                content_type = response.headers.get("Content-Type", "").lower()
                is_img_ct = (
                    content_type.startswith("image/")
                    or content_type in {"application/octet-stream", "binary/octet-stream", ""}
                    or any(url.lower().endswith(ext) or ext + "?" in url.lower() for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"))
                )
                if response.status != 200 or not is_img_ct:
                    return None
                declared = safe_int(response.headers.get("Content-Length"), 0) or 0
                if declared > MAX_IMAGE_BYTES:
                    return None
                chunks = []
                size = 0
                async for chunk in response.content.iter_chunked(64 * 1024):
                    size += len(chunk)
                    if size > MAX_IMAGE_BYTES:
                        return None
                    chunks.append(chunk)
                data = b"".join(chunks)
                if not (
                    content_type.startswith("image/")
                    or data.startswith(b"\xff\xd8")  # JPEG
                    or data.startswith(b"\x89PNG\r\n\x1a\n")  # PNG
                    or data.startswith((b"GIF87a", b"GIF89a"))  # GIF
                    or (data.startswith(b"RIFF") and len(data) >= 12 and data[8:12] == b"WEBP")  # WEBP
                    or data.startswith(b"BM")  # BMP
                ):
                    return None
                return data
        except Exception as exc:
            logger.warning("课件图片下载失败：%s", exc)
            return None

    def account_headers(self, account: dict, include_lesson_token: bool = True) -> dict:
        cookie = str(account.get("cookie") or "")
        csrf_match = re.search(r"csrftoken=([^;\s]+)", cookie)
        device = account.get("device") if isinstance(account.get("device"), dict) else {}
        headers = {
            "cookie": cookie,
            "x-csrftoken": csrf_match.group(1) if csrf_match else "",
            "content-type": "application/json",
            "x-client": "app",
            "xtbz": "ykt",
            "user-agent": device.get("user-agent", "okhttp/4.12.0 Android"),
        }
        if include_lesson_token:
            headers["lessonToken"] = str(account.get("lessonToken") or "")
        if account.get("uid"):
            headers["x-uid"] = str(account["uid"])
        for key in ("brand", "model", "osVersion", "appVersion"):
            if device.get(key):
                headers[key] = str(device[key])
        return headers

    def account_summary(self, account: dict) -> dict:
        phone = str(account.get("phone") or "")
        masked_phone = phone[:3] + "****" + phone[-4:] if len(phone) >= 7 else phone
        return {
            "id": account.get("id"),
            "remark": account.get("remark") or account.get("name") or "托管账号",
            "phone": masked_phone,
            "name": account.get("name", ""),
        }

    async def submit_answer(
        self,
        session,
        runtime: LessonRuntime,
        generation: int,
        deadline: int | None,
        account: dict,
        problem_id: str,
        problem_type: int,
        result: list,
    ):
        summary = self.account_summary(account)
        if not self._problem_open(runtime, generation, problem_id, deadline):
            return False, summary
        if problem_type == 4:
            result_payload: Any = {
                "content": "\n".join(str(item) for item in result),
                "pics": [],
                "videos": [],
            }
        elif problem_type == 1:
            result_payload = sorted(set(str(item) for item in result))
        else:
            result_payload = result
        payload = {
            "problemId": safe_int(problem_id, problem_id),
            "dt": int(time.time() * 1000),
            "problemType": problem_type,
            "result": result_payload,
        }
        url = f"{API_BASE_URL}/api/v3/lesson/problem/answer"
        for attempt in range(2):
            if not self._problem_open(runtime, generation, problem_id, deadline):
                return False, summary
            try:
                async with session.post(
                    url,
                    headers=self.account_headers(account),
                    json=payload,
                ) as response:
                    try:
                        data = await response.json(content_type=None)
                    except (ValueError, TypeError):
                        data = {}
                    if response.status == 200 and (
                        data.get("code") in {0, "0"} or data.get("success") is True
                    ):
                        logger.info("AI 提交成功：%s", summary["remark"])
                        return True, summary
                    message = str(
                        first_defined(data.get("msg"), data.get("message"), data.get("error"), "")
                        or ""
                    ).lower()
                    code = str(first_defined(data.get("code"), data.get("status"), "") or "").lower()
                    auth_failed = response.status in {401, 403} or code in {
                        "401",
                        "403",
                        "unauthorized",
                        "forbidden",
                    } or (
                        any(word in message for word in ("token", "登录", "认证", "凭证"))
                        and any(word in message for word in ("失效", "过期", "无效", "expired", "invalid"))
                    )
                    if auth_failed:
                        self.invalidate_lesson_token(runtime, account)
                        return False, summary
                    if response.status < 500:
                        return False, summary
            except (aiohttp.ClientError, asyncio.TimeoutError):
                pass
            if attempt == 0:
                await asyncio.sleep(0.35)
        return False, summary

    def invalidate_lesson_token(self, runtime: LessonRuntime, account: dict):
        identity = account_identity(account)

        def mutate(accounts: list):
            for current in accounts:
                if (
                    str(current.get("group_key") or "") == runtime.group_key
                    and str(current.get("lessonId") or "") == runtime.lesson_id
                    and account_identity(current) == identity
                ):
                    current["lessonToken"] = ""
                    current["lessonCredentialUpdatedAt"] = int(time.time() * 1000)

        ACCOUNTS_STORE.update(mutate)

    def clear_lesson_tokens(self, group_key: str, lesson_id: str):
        def mutate(accounts: list):
            for account in accounts:
                if (
                    str(account.get("group_key") or "") == group_key
                    and str(account.get("lessonId") or "") == lesson_id
                ):
                    account["lessonId"] = ""
                    account["lessonToken"] = ""
                    account["lessonContext"] = None
                    account["lessonCredentialUpdatedAt"] = int(time.time() * 1000)

        ACCOUNTS_STORE.update(mutate)

    def record_ai_history(
        self,
        *,
        runtime: LessonRuntime,
        problem_id: str,
        problem_type: int,
        body,
        options,
        ai_answers,
        correct_answer,
        cover,
        elapsed: float,
        success_accounts: list,
        total_accounts: int,
        ai_provider: str,
        ai_model: str,
        ai_attempts: list,
        ai_fallback_used: bool,
        problem_started_at: int,
        answer_ready_seconds: float,
        submit_started_seconds: float,
        submitted_seconds: float,
        hard_deadline_at: int,
    ):
        type_names = {0: "单选题", 1: "多选题", 2: "投票题", 3: "填空题", 4: "简答题"}
        now = datetime.now()
        lesson_context: dict = {}
        for account in self.load_accounts():
            if (
                str(account.get("group_key") or "") == runtime.group_key
                and str(account.get("lessonId") or "") == runtime.lesson_id
                and isinstance(account.get("lessonContext"), dict)
            ):
                lesson_context = account["lessonContext"]
                break
        course_name = str(
            first_defined(
                lesson_context.get("courseName"),
                lesson_context.get("course_name"),
                lesson_context.get("classroomName"),
                "常规课程",
            )
        )
        lesson_title = str(
            first_defined(
                lesson_context.get("title"),
                lesson_context.get("lessonTitle"),
                f"课堂 #{runtime.lesson_id}",
            )
        )
        record = {
            "id": f"rec_{uuid.uuid4().hex}",
            "timestamp": int(problem_started_at or time.time() * 1000),
            "groupKey": runtime.group_key,
            "time": now.strftime("%H:%M:%S"),
            "date": now.strftime("%Y-%m-%d"),
            "lessonId": runtime.lesson_id,
            "lessonName": lesson_title,
            "courseName": course_name,
            "lessonTitle": lesson_title,
            "problemId": problem_id,
            "problemType": type_names.get(problem_type, str(problem_type)),
            "body": str(body or "课堂题目"),
            "options": options,
            "aiAnswer": ai_answers,
            "aiProvider": ai_provider,
            "aiModel": ai_model,
            "aiAttempts": ai_attempts,
            "aiAttemptCount": len(ai_attempts),
            "aiFallbackUsed": ai_fallback_used,
            "correctAnswer": correct_answer if isinstance(correct_answer, list) else [],
            "cover": cover,
            "elapsedSeconds": elapsed,
            "problemStartedAt": problem_started_at,
            "answerReadySeconds": answer_ready_seconds,
            "submitStartedSeconds": submit_started_seconds,
            "submittedSeconds": submitted_seconds,
            "hardDeadlineAt": hard_deadline_at,
            "totalAccounts": total_accounts,
            "successCount": len(success_accounts),
            "successAccounts": success_accounts,
            "status": "success" if success_accounts else "failed",
        }

        def mutate(history: list):
            history.insert(0, record)
            del history[500:]

        HISTORY_STORE.update(mutate)

    async def stop_runtime(self, runtime: LessonRuntime, reason: str):
        if runtime.stopped:
            self.runtimes.pop(runtime.key, None)
            return
        runtime.stopped = True
        runtime.generation += 1
        tasks = [task for task in runtime.problem_tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        runtime.problem_tasks.clear()
        if runtime.heartbeat_task:
            runtime.heartbeat_task.cancel()
            await asyncio.gather(runtime.heartbeat_task, return_exceptions=True)
            runtime.heartbeat_task = None
        if runtime.websocket:
            try:
                await runtime.websocket.close()
            except Exception:
                pass
            runtime.websocket = None
        connection = runtime.connection_task
        if connection and connection is not asyncio.current_task() and not connection.done():
            connection.cancel()
            await asyncio.gather(connection, return_exceptions=True)
        self.runtimes.pop(runtime.key, None)
        logger.info(
            "停止 AI 课堂会话：group=%s lesson=%s reason=%s",
            runtime.group_key,
            runtime.lesson_id,
            reason,
        )


if __name__ == "__main__":
    engine = YktWsEngine()
    try:
        asyncio.run(engine.start())
    except KeyboardInterrupt:
        logger.info("WebSocket 引擎已退出")
