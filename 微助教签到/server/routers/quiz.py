"""
答题模块路由 — 课程/题目/作答/同步
"""
import json
import re
import time
import asyncio
import uuid
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import Optional
from auth import verify_api_key
from services.yyb_service import yyb_service
from services.teachermate import get_tm_session
from services.answer_matcher import answer_matcher
from models.database import (
    get_master_ref, get_all_account_exts,
    cache_answer, get_cached_answer, log_answer
)

router = APIRouter(prefix="/api/quiz", tags=["quiz"], dependencies=[Depends(verify_api_key)])

CHOICE_TYPES = (1, 2, 3)


# ── 数据模型 ──

class AnswerData(BaseModel):
    selectedRanks: list[int] = Field(default_factory=list)
    selectedContents: list[str] = Field(default_factory=list)

class SingleSubmitRequest(BaseModel):
    courseId: int
    questionId: int
    questionType: int = 1
    ref: Optional[str] = None  # 选定的答题账号 (openid / ref)
    answer: AnswerData = Field(default_factory=AnswerData)
    answerText: list[str] = Field(default_factory=list)  # 填空/主观题文本
    files: list[str] = Field(default_factory=list)
    audio: list[str] = Field(default_factory=list)

class SubmitAnswerRequest(BaseModel):
    courseId: int
    questionId: int
    questionType: int = 1
    ref: Optional[str] = None
    answer: AnswerData = Field(default_factory=AnswerData)
    syncToAccounts: list[str] = Field(default_factory=lambda: ["all"])
    files: list[str] = Field(default_factory=list)
    audio: list[str] = Field(default_factory=list)
    answerText: list[str] = Field(default_factory=list)  # 填空/主观题文本

class PreviewSyncRequest(BaseModel):
    courseId: int
    questionId: int
    questionType: int = 1
    answer: AnswerData = Field(default_factory=AnswerData)
    answerText: list[str] = Field(default_factory=list)
    syncToAccounts: list[str] = Field(default_factory=lambda: ["all"])

class ConfirmSubmitRequest(BaseModel):
    courseId: int
    questionId: int
    questionType: int = 1
    accountAnswers: dict[str, list] = Field(default_factory=dict)  # { [ref]: [ranks] }
    files: list[str] = Field(default_factory=list)
    audio: list[str] = Field(default_factory=list)


# ── 课程 & 题目 ──

# ── 候选探针账号自动智能轮换 ──

async def get_candidate_probe_refs(explicit_ref: Optional[str] = None) -> list[str]:
    """
    智能获取探针候选账号列表（按有效性优先级排序）：
    1. 优先使用传入的 explicit_ref；
    2. 优先筛选处于 alive 且未失效的账号作为第一梯队；
    3. 其它账号按数据库顺序作为后备灾备队列。
    """
    candidates = []
    if explicit_ref:
        candidates.append(explicit_ref)

    exts = await get_all_account_exts()
    ext_map = {e["ref"]: e for e in exts}

    try:
        yyb_accounts = await yyb_service.get_accounts()
    except Exception:
        yyb_accounts = []

    alive_refs = []
    other_refs = []
    for acc in yyb_accounts:
        ref = acc.get("openid")
        if not ref:
            continue
        ext = ext_map.get(ref, {})
        is_expired = acc.get("status") == "expired" or ext.get("keepalive_status") == "expired" or ext.get("needs_rescan")
        if acc.get("status") == "alive" and not is_expired:
            alive_refs.append(ref)
        else:
            other_refs.append(ref)

    for ext in exts:
        ref = ext.get("ref")
        if ref and ref not in alive_refs and ref not in other_refs:
            other_refs.append(ref)

    all_sorted = candidates + alive_refs + other_refs
    return list(dict.fromkeys(r for r in all_sorted if r))


# ── 课程 & 题目 ──

@router.get("/courses")
async def get_courses(ref: Optional[str] = None):
    """获取课程列表（优先使用指定账号，遇异常自动单次刷新重试）"""
    candidates = [ref] if ref else await get_candidate_probe_refs()
    if not candidates:
        return {"courses": [], "message": "暂无可用账号，请先添加账号"}

    last_error = None
    first_empty_courses = None

    for target_ref in candidates:
        try:
            session = get_tm_session(target_ref)
            courses = await session.get_courses()
            if isinstance(courses, list):
                if len(courses) > 0:
                    print(f"[Quiz] ✓ 成功使用账号 {target_ref[:10]}... 获取到 {len(courses)} 门课程")
                    return {"courses": courses, "master_ref": target_ref, "total": len(courses)}
                elif first_empty_courses is None:
                    first_empty_courses = {"courses": [], "master_ref": target_ref, "total": 0}
        except Exception as e:
            # 会话失效单次自动刷新重试
            try:
                session = get_tm_session(target_ref)
                await session.refresh_session(force=True)
                courses = await session.get_courses()
                if isinstance(courses, list):
                    return {"courses": courses, "master_ref": target_ref, "total": len(courses)}
            except Exception as retry_err:
                last_error = str(retry_err)
            print(f"[Quiz] ⚠️ 账号 {target_ref[:10]}... 获取课程异常: {e}")

    if first_empty_courses is not None:
        return first_empty_courses

    return {"courses": [], "message": f"微助教课程同步异常: {str(last_error or '账号无法连接微助教')[:120]}"}



# 全局题目内存缓存，有效期 5 分钟 (300秒)
QUESTIONS_CACHE = {}
CACHE_MAX_SIZE = 100

def _evict_oldest(cache: dict):
    """如果缓存超过最大容量，移除最旧的条目"""
    while len(cache) > CACHE_MAX_SIZE:
        oldest_key = min(cache, key=lambda k: cache[k]["timestamp"])
        del cache[oldest_key]


def _as_int(value, default: int | None = None) -> int | None:
    """把微助教偶尔返回的字符串数字统一为 int。"""
    if isinstance(value, bool):
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_question(question: dict) -> dict:
    """统一列表与详情字段，避免前端因 number/string 或字段名差异失效。"""
    if not isinstance(question, dict):
        return question
    normalized = dict(question)
    for key in (
        "id", "courseId", "type", "status", "isAnswered", "isCorrect",
        "minChosen", "maxChosen", "blankNum",
    ):
        if key in normalized and normalized[key] is not None:
            normalized[key] = _as_int(normalized[key], normalized[key])

    if "isOpen" not in normalized:
        # 微助教列表/详情用 status=1 表示开放、status=2 表示关闭。
        normalized["isOpen"] = 1 if _as_int(normalized.get("status")) == 1 else 0
    else:
        normalized["isOpen"] = _as_int(normalized["isOpen"], 0)

    options = normalized.get("answerContent")
    # 微助教判断题的选项由官方前端补齐，接口本身可能只返回空数组。
    if _as_int(normalized.get("type")) == 3 and not options:
        options = [
            {"rank": 0, "content": "是"},
            {"rank": 1, "content": "否"},
        ]
    if isinstance(options, list):
        normalized_options = []
        for option in options:
            if not isinstance(option, dict):
                continue
            item = dict(option)
            item["rank"] = _as_int(item.get("rank"), item.get("rank"))
            normalized_options.append(item)
        normalized["answerContent"] = normalized_options
    return normalized


def _normalize_questions_result(result: dict) -> dict:
    if not isinstance(result, dict):
        return result
    normalized = dict(result)
    questions = normalized.get("questions")
    if isinstance(questions, list):
        normalized["questions"] = [_normalize_question(q) for q in questions]
    return normalized

async def fetch_questions_page(ref: str, course_id: int, is_open: Optional[int], is_answered: int, chapter_id: Optional[int], page: int = 0) -> dict:
    session = get_tm_session(ref)
    
    # 仅获取单页数据，不强行并发拉取全部，保证极速响应
    result = await session.get_questions(
        course_id, page=page, is_open=is_open,
        is_answered=is_answered, chapter_id=chapter_id
    )
    return _normalize_questions_result(result)

@router.get("/questions")
async def get_questions(courseId: int, ref: Optional[str] = None, page: int = 0, isOpen: Optional[int] = None,
                        isAnswered: int = 2, chapterId: Optional[int] = None):
    """获取指定账号的题目列表（优先使用选定账号）"""
    candidates = [ref] if ref else await get_candidate_probe_refs()
    if not candidates:
        return {"questions": [], "message": "暂无可用账号"}

    cache_key = f"{ref or 'default'}_{courseId}_{isOpen}_{isAnswered}_{chapterId}_{page}"
    last_error = None

    for target_ref in candidates:
        try:
            result = await fetch_questions_page(target_ref, courseId, isOpen, isAnswered, chapterId, page=page)
            if result and isinstance(result.get("questions"), list):
                QUESTIONS_CACHE[cache_key] = {"timestamp": time.time(), "data": result}
                _evict_oldest(QUESTIONS_CACHE)
                return result
        except Exception as e:
            try:
                session = get_tm_session(target_ref)
                await session.refresh_session(force=True)
                result = await fetch_questions_page(target_ref, courseId, isOpen, isAnswered, chapterId, page=page)
                if result and isinstance(result.get("questions"), list):
                    QUESTIONS_CACHE[cache_key] = {"timestamp": time.time(), "data": result}
                    _evict_oldest(QUESTIONS_CACHE)
                    return result
            except Exception as retry_err:
                last_error = str(retry_err)
            print(f"[Quiz] ⚠️ 账号 {target_ref[:10]}... 拉取题目异常: {e}")

    cached = QUESTIONS_CACHE.get(cache_key)
    if cached:
        return cached["data"]
    return {"questions": [], "questionNum": 0, "message": f"加载题目失败: {str(last_error or '所有账号均无法获取题目')[:100]}"}


def _choice_ranks_from_remote(answer) -> list[int]:
    """只解析学生自己的作答；answerContent.answer 是标准答案标记，不能用于回显。"""
    ranks: list[int] = []
    if isinstance(answer, dict):
        answer = answer.get("answer", answer.get("ranks", []))
    if not isinstance(answer, list):
        answer = [answer] if answer is not None else []
    if isinstance(answer, list):
        for item in answer:
            if isinstance(item, dict):
                rank = item.get("rank", item.get("index"))
            else:
                rank = item
            parsed = _as_int(rank)
            if parsed is not None and parsed not in ranks:
                ranks.append(parsed)
    return ranks


def _fill_answers_from_remote(answer) -> list[str]:
    """把填空题返回的 [{rank, answer, isCorrect}] 还原成按空位排序的字符串数组。"""
    if isinstance(answer, dict):
        answer = answer.get("answer", [])
    if not isinstance(answer, list):
        answer = [answer] if answer is not None else []

    values: list[tuple[int, str]] = []
    for position, item in enumerate(answer):
        if isinstance(item, dict):
            rank = _as_int(item.get("rank", item.get("index")), position)
            value = item.get("answer", item.get("content", item.get("value", "")))
        else:
            rank = position
            value = item
        values.append((rank if rank is not None else position, str(value or "")))
    return [value for _, value in sorted(values, key=lambda pair: pair[0])]


def _clean_answer_text(val) -> str:
    if val is None or isinstance(val, bool):
        return ""
    if isinstance(val, (list, tuple, set)):
        items = [_clean_answer_text(x) for x in val]
        return " / ".join([x for x in items if x])
    
    s = str(val).strip()
    if not s:
        return ""

    # 解析 JSON 或 Python repr 数组字符串 (例如 '["2"]' 或 "['2']")
    if (s.startswith("[") and s.endswith("]")) or (s.startswith("{") and s.endswith("}")):
        try:
            parsed = json.loads(s)
            if isinstance(parsed, list):
                items = [_clean_answer_text(x) for x in parsed]
                return " / ".join([x for x in items if x])
            elif isinstance(parsed, dict):
                return _clean_answer_text(parsed.get("content") or parsed.get("answer") or parsed.get("value"))
        except Exception:
            try:
                import ast
                parsed = ast.literal_eval(s)
                if isinstance(parsed, (list, tuple, set)):
                    items = [_clean_answer_text(x) for x in parsed]
                    return " / ".join([x for x in items if x])
            except Exception:
                pass

    # 正则安全剥离 ['2'] 或 ["2"] 或 [2]
    s = re.sub(r"^\s*\[\s*['\"]?(.*?)['\"]?\s*\]\s*$", r"\1", s).strip()
    # 去除 HTML 标签
    s = re.sub(r'<[^>]+>', '', s).strip()
    # 过滤布尔字面量
    if s.lower() in ("true", "false", "null", "none", "undefined"):
        return ""
    return s


def _extract_fill_correct_answers(detail: dict) -> list[str]:
    """从微助教题目详情中提取填空题的标准正确答案"""
    blanks: dict[int, list[str]] = {}
    
    # 1. 从 answerContent 提取（微助教标准填空题的真实文字通常在 content 或 answers 中，answer 字段常为布尔标志）
    options = detail.get("answerContent")
    if isinstance(options, list):
        for idx, opt in enumerate(options):
            if isinstance(opt, dict):
                rank = _as_int(opt.get("rank", opt.get("index")), idx)
                ans_list = []
                
                # answers 数组优先 (微助教填空题 answers: ["正确答案1", "同义答案2"])
                if isinstance(opt.get("answers"), list):
                    for x in opt["answers"]:
                        cleaned = _clean_answer_text(x.get("content") or x.get("answer") or x.get("value") if isinstance(x, dict) else x)
                        if cleaned:
                            ans_list.append(cleaned)
                
                # content
                c = _clean_answer_text(opt.get("content"))
                if c:
                    ans_list.append(c)
                
                # value / text / answerText
                for key in ("value", "text", "answerText"):
                    v = _clean_answer_text(opt.get(key))
                    if v:
                        ans_list.append(v)
                
                # 若 answer 字段为纯文本且非布尔标志
                if "answer" in opt and not isinstance(opt["answer"], (bool, int, float)):
                    v = _clean_answer_text(opt["answer"])
                    if v:
                        ans_list.append(v)
                
                if ans_list:
                    blanks.setdefault(rank if rank is not None else idx, []).extend(ans_list)
            elif isinstance(opt, str):
                c = _clean_answer_text(opt)
                if c:
                    blanks.setdefault(idx, []).append(c)

    # 2. 从 correctAnswer / standardAnswer / rightAnswer / answerKey / solution 提取
    if not blanks:
        for key in ("correctAnswer", "standardAnswer", "rightAnswer", "answerKey", "solution"):
            raw = detail.get(key)
            if not raw:
                continue
            if isinstance(raw, list):
                for idx, item in enumerate(raw):
                    if isinstance(item, dict):
                        rank = _as_int(item.get("rank", item.get("index")), idx)
                        candidates = []
                        if isinstance(item.get("answers"), list):
                            for x in item["answers"]:
                                c = _clean_answer_text(x)
                                if c:
                                    candidates.append(c)
                        for f in ("content", "value", "text", "answer"):
                            if f == "answer" and isinstance(item.get(f), (bool, int, float)):
                                continue
                            c = _clean_answer_text(item.get(f))
                            if c:
                                candidates.append(c)
                        if candidates:
                            blanks.setdefault(rank if rank is not None else idx, []).extend(candidates)
                    else:
                        c = _clean_answer_text(item)
                        if c:
                            blanks.setdefault(idx, []).append(c)
            elif isinstance(raw, dict):
                ans = raw.get("answers") or raw.get("content") or raw.get("value") or raw.get("text")
                if isinstance(ans, list):
                    for idx, v in enumerate(ans):
                        c = _clean_answer_text(v)
                        if c:
                            blanks.setdefault(idx, []).append(c)
                else:
                    c = _clean_answer_text(ans)
                    if c:
                        blanks.setdefault(0, []).append(c)
            elif isinstance(raw, str):
                parts = [p.strip() for p in raw.split("|") if p.strip()]
                for idx, p in enumerate(parts):
                    c = _clean_answer_text(p)
                    if c:
                        blanks.setdefault(idx, []).append(c)
            if blanks:
                break

    result = []
    for rank in sorted(blanks.keys()):
        candidates = list(dict.fromkeys(blanks[rank]))
        if candidates:
            result.append(" / ".join(candidates))
    return result


def _json_list(value, default: list | None = None) -> list:
    if isinstance(value, list):
        return value
    try:
        parsed = json.loads(value or "[]")
        return parsed if isinstance(parsed, list) else (default or [])
    except (TypeError, ValueError, json.JSONDecodeError):
        return default or []


async def process_question_detail(detail: dict, course_id: int | None = None) -> dict:
    if not detail or not isinstance(detail, dict):
        return detail

    detail = _normalize_question(detail)
    question_id = _as_int(detail.get("id"), 0)
    resolved_course_id = _as_int(course_id, None)
    if resolved_course_id is None:
        resolved_course_id = _as_int(detail.get("courseId"), 0) or 0
    if resolved_course_id:
        detail["courseId"] = resolved_course_id
    q_type = _as_int(detail.get("type"), 0) or 0

    # 1. 优先解析微助教的原生作答数据
    has_server_answer = False
    if _as_int(detail.get("isAnswered"), 0) == 1:
        ans = detail.get("answer")
        if q_type in CHOICE_TYPES:
            ranks = _choice_ranks_from_remote(ans)
            if ranks:
                detail["serverAnswer"] = ranks
                detail["serverAnswerSource"] = "remote"
                has_server_answer = True
        elif q_type == 4:
            texts = _fill_answers_from_remote(ans)
            if texts:
                detail["serverAnswer"] = texts
                detail["serverAnswerSource"] = "remote"
                has_server_answer = True
        elif q_type == 5 and isinstance(ans, dict):
            texts = ans.get("answer")
            attaches = ans.get("attaches")
            if isinstance(texts, str):
                texts = [texts]
            if isinstance(texts, list):
                detail["serverAnswer"] = [str(text) for text in texts]
                has_server_answer = bool(texts)
            if isinstance(attaches, list):
                detail["serverFiles"] = attaches
                has_server_answer = has_server_answer or bool(attaches)
            if has_server_answer:
                detail["serverAnswerSource"] = "remote"
        elif isinstance(ans, list):
            detail["serverAnswer"] = ans
            detail["serverAnswerSource"] = "remote"
            has_server_answer = bool(ans)
        if not has_server_answer:
            if "myAnswer" in detail:
                detail["serverAnswer"] = _json_list(detail["myAnswer"], [detail["myAnswer"]])
                has_server_answer = True
            elif "studentAnswer" in detail:
                detail["serverAnswer"] = _json_list(detail["studentAnswer"], [detail["studentAnswer"]])
                has_server_answer = True
            elif "reply" in detail:
                detail["serverAnswer"] = [detail["reply"]]
                has_server_answer = True
            if has_server_answer:
                detail["serverAnswerSource"] = "remote"

    # 2. 解析微助教标准正确答案
    if q_type in CHOICE_TYPES:
        correct_ranks: list[int] = []
        options = detail.get("answerContent") or []
        if isinstance(options, list):
            for opt in options:
                if isinstance(opt, dict):
                    is_opt_correct = (
                        opt.get("answer") in (1, "1", True) or
                        opt.get("isCorrect") in (1, "1", True) or
                        opt.get("isRight") in (1, "1", True) or
                        opt.get("correct") is True
                    )
                    if is_opt_correct:
                        r = _as_int(opt.get("rank"))
                        if r is not None and r not in correct_ranks:
                            correct_ranks.append(r)

        if not correct_ranks:
            raw_correct = detail.get("correctAnswer") or detail.get("standardAnswer") or detail.get("rightAnswer") or detail.get("answerKey")
            if raw_correct is not None:
                if isinstance(raw_correct, list):
                    for item in raw_correct:
                        r = _as_int(item.get("rank") if isinstance(item, dict) else item)
                        if r is not None and r not in correct_ranks:
                            correct_ranks.append(r)
                elif isinstance(raw_correct, (int, str)) and str(raw_correct).strip().isdigit():
                    correct_ranks.append(int(raw_correct))

        detail["correctAnswerRanks"] = sorted(correct_ranks)
        if correct_ranks and isinstance(options, list):
            labels = []
            for r in sorted(correct_ranks):
                idx = next((i for i, o in enumerate(options) if _as_int(o.get("rank", o.get("index")), i) == r), r)
                letter = chr(65 + idx) if 0 <= idx < 26 else str(r + 1)
                labels.append(letter)
            detail["correctAnswer"] = ", ".join(labels)
            detail["standardAnswer"] = detail["correctAnswer"]
        else:
            detail["correctAnswer"] = ""
            detail["standardAnswer"] = ""
    elif q_type == 4:
        # 填空题提取正确答案
        correct_fills = _extract_fill_correct_answers(detail)
        detail["correctFillAnswers"] = correct_fills
        if correct_fills:
            detail["correctAnswer"] = " | ".join(f"空{idx+1}: {ans}" for idx, ans in enumerate(correct_fills))
            detail["standardAnswer"] = detail["correctAnswer"]
        else:
            detail["correctAnswer"] = ""
            detail["standardAnswer"] = ""
    elif q_type == 5:
        # 主观题标准答案
        raw_std = detail.get("standardAnswer") or detail.get("correctAnswer") or detail.get("referenceAnswer") or detail.get("solution") or ""
        if isinstance(raw_std, (dict, list)):
            detail["correctAnswer"] = json.dumps(raw_std, ensure_ascii=False)
        else:
            std_str = str(raw_std).strip()
            detail["correctAnswer"] = std_str if std_str.lower() not in ("true", "false", "1", "0", "null") else ""
        detail["standardAnswer"] = detail["correctAnswer"]

    detail["explain"] = str(detail.get("explain") or detail.get("analysis") or detail.get("description") or detail.get("solution") or "").strip()

    return detail


# 全局题目详情内存缓存
QUESTION_DETAIL_CACHE = {}


@router.post("/refresh-session")
async def force_refresh_quiz_session():
    """强制重新建立并刷新微助教会话，清理过期的题目缓存"""
    global QUESTIONS_CACHE, QUESTION_DETAIL_CACHE
    QUESTIONS_CACHE.clear()
    QUESTION_DETAIL_CACHE.clear()

    candidates = await get_candidate_probe_refs()
    if not candidates:
        return {"success": False, "message": "暂无可用账号，请先添加账号"}

    refreshed_count = 0
    errors = []
    for ref in candidates:
        try:
            session = get_tm_session(ref)
            await session.refresh_session(force=True)
            refreshed_count += 1
            print(f"[Quiz/Refresh] ✓ 账号 {ref[:10]}... 强制会话刷新成功")
        except Exception as e:
            errors.append(f"{ref[:6]}: {str(e)}")
            print(f"[Quiz/Refresh] ✗ 账号 {ref[:10]}... 刷新异常: {e}")

    return {
        "success": refreshed_count > 0,
        "message": f"已成功强制刷新 {refreshed_count} 个有效账号的会话凭证" if refreshed_count > 0 else f"会话刷新失败: {', '.join(errors)}",
        "refreshed_count": refreshed_count,
        "total": len(candidates)
    }


@router.get("/questions/{question_id}")
async def get_question_detail(question_id: int, courseId: int | None = None, ref: Optional[str] = None):
    """获取题目详情（包含指定学生的作答状态与回显）"""
    cache_key = (ref or 'default', courseId or 0, question_id)
    cached = QUESTION_DETAIL_CACHE.get(cache_key)
    if cached:
        cached_data = cached["data"]
        if cached_data.get("isAnswered") == 1 and cached_data.get("isOpen") == 0:
            return cached_data

    candidates = [ref] if ref else await get_candidate_probe_refs()
    if not candidates:
        return {"message": "暂无可用账号"}

    last_error = None
    for target_ref in candidates:
        try:
            session = get_tm_session(target_ref)
            detail = await session.get_question_detail(question_id)
            processed = await process_question_detail(detail, courseId)

            QUESTION_DETAIL_CACHE[cache_key] = {"timestamp": time.time(), "data": processed}
            _evict_oldest(QUESTION_DETAIL_CACHE)
            return processed
        except Exception as e:
            try:
                session = get_tm_session(target_ref)
                await session.refresh_session(force=True)
                detail = await session.get_question_detail(question_id)
                processed = await process_question_detail(detail, courseId)
                QUESTION_DETAIL_CACHE[cache_key] = {"timestamp": time.time(), "data": processed}
                _evict_oldest(QUESTION_DETAIL_CACHE)
                return processed
            except Exception as retry_err:
                last_error = str(retry_err)
            print(f"[Quiz] ⚠️ 账号 {target_ref[:10]}... 获取题目详情异常: {e}")

    if cached:
        return cached["data"]
    return {"message": f"加载题目详情失败: {str(last_error or '所有账号均无法获取详情')[:100]}"}


@router.get("/chapters/{course_id}")
async def get_chapters(course_id: int):
    """获取课程章节（自动轮换有效账号）"""
    candidates = await get_candidate_probe_refs()
    for target_ref in candidates:
        try:
            session = get_tm_session(target_ref)
            chapters = await session.get_chapters(course_id)
            if isinstance(chapters, list):
                return chapters
        except Exception as e:
            print(f"[Quiz/Rotation] get_chapters error with {target_ref[:10]}: {e}")
    return []


SYNC_JOBS: dict[str, dict] = {}
BACKGROUND_TASKS: set[asyncio.Task] = set()
SYNC_JOB_MAX_SIZE = 100


def _remember_background_task(task: asyncio.Task) -> None:
    """持有后台任务的强引用，并在完成后自动释放。"""
    BACKGROUND_TASKS.add(task)
    task.add_done_callback(BACKGROUND_TASKS.discard)


def _create_sync_job(sub_refs: list[str], course_id: int, question_id: int) -> str:
    job_id = uuid.uuid4().hex
    SYNC_JOBS[job_id] = {
        "job_id": job_id,
        "status": "running",
        "course_id": course_id,
        "question_id": question_id,
        "total": len(sub_refs),
        "completed": 0,
        "success_count": 0,
        "failure_count": 0,
        "results": [],
        "timestamp": time.time(),
    }
    while len(SYNC_JOBS) > SYNC_JOB_MAX_SIZE:
        oldest = min(SYNC_JOBS, key=lambda key: SYNC_JOBS[key]["timestamp"])
        SYNC_JOBS.pop(oldest, None)
    return job_id


async def run_background_sync(sub_refs: list[str], course_id: int, question_id: int,
                              question_type: int, selected_contents: list[str],
                              master_answer: list, files: list, audio: list,
                              job_id: str | None = None) -> list[dict]:
    """后台异步同步子账号答案，完全不阻塞主账号返回"""
    try:
        if question_type in CHOICE_TYPES:
            tasks = [
                _sync_choice_to_sub(
                    ref, course_id, question_id, question_type,
                    selected_contents, master_answer, files, audio
                )
                for ref in sub_refs
            ]
        else:
            tasks = [
                _sync_direct_to_sub(
                    ref, course_id, question_id, question_type,
                    master_answer, files, audio
                )
                for ref in sub_refs
            ]

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        results: list[dict] = []
        for ref, result in zip(sub_refs, raw_results):
            if isinstance(result, BaseException):
                results.append({
                    "ref": ref, "matched": False, "matched_ranks": [],
                    "success": False, "message": f"同步任务异常: {result}",
                })
            else:
                results.append(result)

        if job_id and job_id in SYNC_JOBS:
            job = SYNC_JOBS[job_id]
            job["results"] = results
            job["completed"] = len(results)
            job["success_count"] = sum(1 for result in results if result.get("success"))
            job["failure_count"] = len(results) - job["success_count"]
            job["status"] = "completed"
            job["timestamp"] = time.time()
        return results
    except Exception as exc:
        if job_id and job_id in SYNC_JOBS:
            SYNC_JOBS[job_id].update({
                "status": "failed", "message": str(exc), "timestamp": time.time()
            })
        raise


@router.get("/sync/{job_id}")
async def get_sync_status(job_id: str):
    job = SYNC_JOBS.get(job_id)
    if not job:
        return {"job_id": job_id, "status": "expired"}
    return job


async def _resolve_master_contents(
    master_ref: str,
    course_id: int,
    question_id: int,
    selected_ranks: list[int],
    supplied_contents: list[str],
) -> list[str]:
    """从主账号详情快照按 rank 反查内容，杜绝客户端内容与 rank 错位。"""
    cached = QUESTION_DETAIL_CACHE.get((course_id, question_id))
    detail = cached.get("data") if cached else None
    if not detail or not detail.get("answerContent"):
        detail = await get_tm_session(master_ref).get_question_detail(question_id)
        detail = await process_question_detail(detail, course_id)
        QUESTION_DETAIL_CACHE[(course_id, question_id)] = {
            "timestamp": time.time(), "data": detail,
        }
        _evict_oldest(QUESTION_DETAIL_CACHE)

    options = detail.get("answerContent") or []
    by_rank: dict[int, str] = {}
    for option in options:
        if not isinstance(option, dict):
            continue
        rank = _as_int(option.get("rank"))
        if rank is not None:
            by_rank[rank] = str(option.get("content", ""))

    if not by_rank and len(supplied_contents) == len(selected_ranks):
        return [str(content) for content in supplied_contents]

    resolved: list[str] = []
    for rank in selected_ranks:
        parsed_rank = _as_int(rank)
        if parsed_rank is None or parsed_rank not in by_rank:
            raise ValueError(f"主账号选项 rank={rank} 不存在")
        resolved.append(by_rank[parsed_rank])

    if len(resolved) != len(selected_ranks):
        raise ValueError("主账号答案与选项内容数量不一致")
    return resolved


# ── 提交答案 + 同步 + 全员选项匹配预览 ──

@router.post("/preview")
async def preview_sync(req: PreviewSyncRequest):
    """
    全员选项匹配预览：
    计算主账号答案在所有子账号上的乱序匹配结果，
    返回每个账号的匹配选项与标签（如 "张三 -> A. 牛顿", "李四 -> C. 牛顿"），
    供用户人工复核确认，确保万无一失！
    """
    master_ref = await get_master_ref()
    if not master_ref:
        return {"can_submit": False, "message": "请先设置主账号", "preview_list": []}

    # 1. 规范化主账号答案
    if req.questionType in CHOICE_TYPES:
        master_answer = [rank for rank in (_as_int(v) for v in req.answer.selectedRanks) if rank is not None]
    else:
        master_answer = [str(value) for value in req.answerText]

    if req.questionType in CHOICE_TYPES and not master_answer:
        return {"can_submit": False, "message": "请先在主账号选择答案", "preview_list": []}

    selected_contents = [str(content) for content in req.answer.selectedContents]
    if req.questionType in CHOICE_TYPES:
        try:
            selected_contents = await _resolve_master_contents(
                master_ref, req.courseId, req.questionId, master_answer, selected_contents
            )
        except Exception as e:
            return {"can_submit": False, "message": f"解析主账号选项失败: {e}", "preview_list": []}

    # 2. 获取所有目标账号
    if "all" in req.syncToAccounts:
        all_exts = await get_all_account_exts()
        target_refs = [e["ref"] for e in all_exts if e.get("ref")]
    else:
        target_refs = req.syncToAccounts

    # 确保主账号在第一位
    if master_ref not in target_refs:
        target_refs = [master_ref] + target_refs
    else:
        target_refs = [master_ref] + [r for r in target_refs if r != master_ref]

    # 获取账号昵称映射
    from routers.signin import get_fast_nickname_map
    nickname_map = await get_fast_nickname_map()

    # 3. 并发为每个账号计算匹配选项
    async def match_account(ref: str) -> dict:
        is_master = (ref == master_ref)
        nickname = nickname_map.get(ref, ref[:8])

        if not (req.questionType in CHOICE_TYPES):
            # 填空/主观题
            return {
                "ref": ref,
                "nickname": nickname,
                "is_master": is_master,
                "matched": True,
                "ranks": master_answer,
                "labels": [str(x) for x in master_answer],
                "status": "ready",
                "message": "主选内容同步" if not is_master else "主选内容"
            }

        try:
            session = get_tm_session(ref)
            detail = await session.get_question_detail(req.questionId)
            sub_options = detail.get("answerContent", []) if isinstance(detail, dict) else []

            if req.questionType == 3 and not sub_options:
                sub_options = [
                    {"rank": 0, "content": "是"},
                    {"rank": 1, "content": "否"},
                ]

            if is_master:
                # 主账号直接格式化其已选选项
                labels = []
                for rank in master_answer:
                    opt = next((o for o in sub_options if _as_int(o.get("rank")) == rank), None)
                    content_str = answer_matcher.strip_html(opt.get("content", "")) if opt else ""
                    letter = chr(65 + rank) if req.questionType != 3 else ("对" if rank == 0 else "错")
                    labels.append(f"{letter}. {content_str}" if content_str else f"选项 {letter}")
                return {
                    "ref": ref,
                    "nickname": nickname,
                    "is_master": True,
                    "matched": True,
                    "ranks": master_answer,
                    "labels": labels,
                    "status": "ready",
                    "message": "主选答案"
                }

            # 子账号：进行严格语义匹配
            if not sub_options:
                return {
                    "ref": ref,
                    "nickname": nickname,
                    "is_master": False,
                    "matched": False,
                    "ranks": [],
                    "labels": [],
                    "status": "error",
                    "message": "子账号未拉取到选项数据"
                }

            matched_ranks = answer_matcher.build_sub_answer(
                req.questionType, selected_contents, master_answer, sub_options
            )

            # 格式化子账号匹配到的选项标签
            labels = []
            for rank in matched_ranks:
                opt = next((o for o in sub_options if _as_int(o.get("rank")) == rank), None)
                content_str = answer_matcher.strip_html(opt.get("content", "")) if opt else ""
                letter = chr(65 + rank) if req.questionType != 3 else ("对" if rank == 0 else "错")
                labels.append(f"{letter}. {content_str}" if content_str else f"选项 {letter}")

            return {
                "ref": ref,
                "nickname": nickname,
                "is_master": False,
                "matched": True,
                "ranks": matched_ranks,
                "labels": labels,
                "status": "ready",
                "message": "精确匹配成功"
            }

        except Exception as e:
            return {
                "ref": ref,
                "nickname": nickname,
                "is_master": is_master,
                "matched": False,
                "ranks": [],
                "labels": [],
                "status": "error",
                "message": f"选项匹配失败: {e}"
            }

    tasks = [match_account(ref) for ref in target_refs]
    preview_list = await asyncio.gather(*tasks)

    matched_count = sum(1 for p in preview_list if p.get("matched"))
    can_submit = (matched_count > 0)

    return {
        "can_submit": can_submit,
        "total_accounts": len(preview_list),
        "matched_count": matched_count,
        "unmatched_count": len(preview_list) - matched_count,
        "preview_list": preview_list
    }


@router.post("/confirm-submit")
async def confirm_submit(req: ConfirmSubmitRequest):
    """
    全员确认提交：
    按照已核对无误的多账号选项映射，并发将各自已核实的正确选项提交至微助教！
    """
    if not req.accountAnswers:
        return {"success": False, "message": "没有需要提交的账号答案", "results": []}

    from routers.signin import get_fast_nickname_map
    nickname_map = await get_fast_nickname_map()

    async def submit_one(ref: str, answer_ranks: list) -> dict:
        nickname = nickname_map.get(ref, ref[:8])
        try:
            session = get_tm_session(ref)
            await session.submit_answer(
                req.courseId, req.questionId, answer_ranks,
                files=req.files, audio=req.audio,
                question_type=req.questionType
            )
            await log_answer(ref, req.courseId, req.questionId, json.dumps(answer_ranks), True, True, "确认提交成功")
            return {"ref": ref, "nickname": nickname, "success": True, "message": "提交成功"}
        except Exception as e:
            err_msg = str(e)
            # 自动单次刷新重试
            try:
                session = get_tm_session(ref)
                await session.refresh_session(force=True)
                await session.submit_answer(
                    req.courseId, req.questionId, answer_ranks,
                    files=req.files, audio=req.audio,
                    question_type=req.questionType
                )
                await log_answer(ref, req.courseId, req.questionId, json.dumps(answer_ranks), True, True, "重试提交成功")
                return {"ref": ref, "nickname": nickname, "success": True, "message": "提交成功"}
            except Exception as retry_err:
                err_msg = str(retry_err)
            await log_answer(ref, req.courseId, req.questionId, json.dumps(answer_ranks), False, False, f"提交失败: {err_msg}")
            return {"ref": ref, "nickname": nickname, "success": False, "message": f"提交失败: {err_msg}"}

    tasks = [submit_one(ref, ans) for ref, ans in req.accountAnswers.items()]
    results = await asyncio.gather(*tasks)

    success_count = sum(1 for r in results if r.get("success"))

    # 清除题目详情缓存以加载最新状态
    cache_key = (req.courseId, req.questionId)
    QUESTION_DETAIL_CACHE.pop(cache_key, None)
    for k in list(QUESTIONS_CACHE.keys()):
        if k.startswith(f"{req.courseId}_"):
            QUESTIONS_CACHE.pop(k, None)

    return {
        "success": success_count > 0,
        "total": len(results),
        "success_count": success_count,
        "failure_count": len(results) - success_count,
        "results": results
    }


# ── 单账号极速直接答题 ──

@router.post("/submit")
async def submit_single_answer(req: SingleSubmitRequest):
    """
    单账号直接提交答案（秒级极速响应，直接为指定选定账号提交）
    """
    target_ref = req.ref
    if not target_ref:
        target_ref = await get_master_ref()
    if not target_ref:
        candidates = await get_candidate_probe_refs()
        target_ref = candidates[0] if candidates else None

    if not target_ref:
        return {"success": False, "message": "未选定答题账号，请先选择账号"}

    # 规范化答案
    if req.questionType in CHOICE_TYPES:
        answer_payload = [rank for rank in (_as_int(v) for v in req.answer.selectedRanks) if rank is not None]
        if not answer_payload:
            return {"success": False, "message": "请先选择答案"}
    elif req.questionType == 4:
        answer_payload = [str(x) for x in req.answerText]
        if not any(answer_payload):
            return {"success": False, "message": "请填写答案"}
    elif req.questionType == 5:
        answer_payload = req.answerText if req.answerText else []
    else:
        answer_payload = [rank for rank in (_as_int(v) for v in req.answer.selectedRanks) if rank is not None]

    session = get_tm_session(target_ref)

    # 严格校验：已作答题目不允许修改
    try:
        cur_detail = await session.get_question_detail(req.questionId)
        if cur_detail and _as_int(cur_detail.get("isAnswered"), 0) == 1:
            return {"success": False, "message": "该题目您已作答，系统不允许修改作答"}
    except Exception as check_err:
        print(f"[Quiz/Submit] 预检题目作答状态: {check_err}")

    try:
        res = await session.submit_answer(
            req.courseId, req.questionId, answer_payload,
            files=req.files, audio=req.audio,
            question_type=req.questionType
        )
        await log_answer(target_ref, req.courseId, req.questionId, json.dumps(answer_payload), True, True, "单账号提交成功")
        
        # 清除内存缓存以展示最新状态
        QUESTION_DETAIL_CACHE.pop((target_ref, req.courseId, req.questionId), None)
        QUESTION_DETAIL_CACHE.pop(('default', req.courseId, req.questionId), None)
        for k in list(QUESTIONS_CACHE.keys()):
            if k.startswith(f"{target_ref}_") or k.startswith("default_"):
                QUESTIONS_CACHE.pop(k, None)

        return {
            "success": True,
            "message": "提交成功",
            "serverAnswer": answer_payload,
            "raw": res
        }
    except Exception as e:
        # 会话失效单次自动刷新重试
        try:
            print(f"[Quiz/Submit] 账号 {target_ref[:10]} 提交遇到异常: {e}，正在刷新会话并重试...")
            await session.refresh_session(force=True)
            res = await session.submit_answer(
                req.courseId, req.questionId, answer_payload,
                files=req.files, audio=req.audio,
                question_type=req.questionType
            )
            await log_answer(target_ref, req.courseId, req.questionId, json.dumps(answer_payload), True, True, "单账号重试提交成功")
            
            QUESTION_DETAIL_CACHE.pop((target_ref, req.courseId, req.questionId), None)
            QUESTION_DETAIL_CACHE.pop(('default', req.courseId, req.questionId), None)
            return {
                "success": True,
                "message": "提交成功",
                "serverAnswer": answer_payload,
                "raw": res
            }
        except Exception as retry_err:
            await log_answer(target_ref, req.courseId, req.questionId, json.dumps(answer_payload), False, False, f"单账号提交失败: {retry_err}")
            return {
                "success": False,
                "message": f"提交失败: {retry_err}"
            }


# ── 提交答案 + 同步 ──

@router.post("/answer")
async def submit_answer(req: SubmitAnswerRequest):
    """
    主账号提交答案 + 后台自动异步同步到子账号 (0延时无感响应)
    """
    master_ref = await get_master_ref()
    if not master_ref:
        return {"message": "请先设置主账号", "master": None}

    master_session = get_tm_session(master_ref)

    # ── Step 1: 规范化并提交主账号答案 ──
    if req.questionType in CHOICE_TYPES:  # 选择题/判断题
        master_answer = [rank for rank in (_as_int(v) for v in req.answer.selectedRanks) if rank is not None]
    elif req.questionType == 4:  # 填空题
        master_answer = [str(value) for value in req.answerText]
    else:  # 主观题
        master_answer = [str(value) for value in req.answerText]

    master_result = {"ref": master_ref, "success": False, "submitted_ranks": master_answer}
    selected_contents = [str(content) for content in req.answer.selectedContents]

    try:
        if req.questionType in CHOICE_TYPES:
            if not master_answer:
                raise ValueError("请选择答案")
            selected_contents = await _resolve_master_contents(
                master_ref, req.courseId, req.questionId,
                master_answer, selected_contents,
            )
        await master_session.submit_answer(
            req.courseId, req.questionId, master_answer,
            files=req.files, audio=req.audio,
            question_type=req.questionType,
        )
        master_result["success"] = True
        master_result["message"] = "提交成功"
    except Exception as e:
        master_result["message"] = str(e)

    # 记录日志
    await log_answer(master_ref, req.courseId, req.questionId,
                     json.dumps(master_answer), False,
                     master_result["success"], master_result.get("message", ""))

    # 如果主账号提交成功，缓存答案并触发子账号后台同步
    sync_job_id = None
    sync_started = False
    if master_result["success"]:
        # ── Step 2: 缓存答案 ──
        plain_texts = [answer_matcher.strip_html(c) for c in selected_contents]
        await cache_answer(
            req.courseId, req.questionId, req.questionType,
            master_ref,
            json.dumps(master_answer),
            json.dumps(selected_contents),
            json.dumps(plain_texts),
            json.dumps(req.files),
        )

        # ── Step 3: 后台派发同步到子账号 ──
        if "all" in req.syncToAccounts:
            all_exts = await get_all_account_exts()
            sub_refs = [e["ref"] for e in all_exts if not e.get("is_master")]
        else:
            sub_refs = [r for r in req.syncToAccounts if r != master_ref]

        if sub_refs:
            sync_job_id = _create_sync_job(sub_refs, req.courseId, req.questionId)
            task = asyncio.create_task(run_background_sync(
                sub_refs, req.courseId, req.questionId, req.questionType,
                selected_contents, master_answer, req.files, req.audio, sync_job_id
            ))
            _remember_background_task(task)
            sync_started = True

        # ── Step 4: 立即更新详情快照，抵消微助教接口的状态传播延迟 ──
        cache_key = (req.courseId, req.questionId)
        detail_cache = QUESTION_DETAIL_CACHE.get(cache_key)
        if detail_cache:
            detail_cache["data"]["isAnswered"] = 1
            detail_cache["data"]["serverAnswer"] = master_answer
            detail_cache["data"]["serverAnswerSource"] = "local_cache"
            detail_cache["timestamp"] = time.time()
        for k in list(QUESTIONS_CACHE.keys()):
            if k.startswith(f"{req.courseId}_"):
                QUESTIONS_CACHE.pop(k, None)

    return {
        "master": master_result,
        "sync_started": sync_started,
        "sync_job_id": sync_job_id,
    }


async def _sync_choice_to_sub(ref: str, course_id: int, question_id: int,
                               question_type: int, master_contents: list[str],
                               master_answer: list, files: list, audio: list) -> dict:
    """将选择题答案同步到一个子账号（支持判断题标准化、选项智能降级与重试）"""
    result = {"ref": ref, "matched": False, "matched_ranks": [], "success": False, "message": ""}

    sub_session = get_tm_session(ref)
    for attempt in range(2):
        try:
            # 获取子账号的题目详情（选项可能乱序）
            detail = await sub_session.get_question_detail(question_id)
            sub_options = detail.get("answerContent", []) if isinstance(detail, dict) else []

            # 判断题（Type 3）微助教原生不返回选项，自动补齐
            if question_type == 3 and not sub_options:
                sub_options = [
                    {"rank": 0, "content": "是"},
                    {"rank": 1, "content": "否"},
                ]

            # 语义匹配选项
            matched_ranks = None
            if sub_options and master_contents:
                try:
                    matched_ranks = answer_matcher.build_sub_answer(
                        question_type, master_contents, master_answer, sub_options
                    )
                except Exception as match_err:
                    print(f"[Sync/Match] ⚠️ 账号 {ref[:8]} 选项匹配异常: {match_err}，智能回退至主账号选项")

            if matched_ranks is None:
                matched_ranks = master_answer

            result["matched"] = True
            result["matched_ranks"] = matched_ranks

            # 提交答案
            await sub_session.submit_answer(
                course_id, question_id, matched_ranks, files, audio,
                question_type=question_type,
            )
            result["success"] = True
            result["message"] = "同步成功"
            break

        except Exception as e:
            err_msg = str(e)
            if attempt == 0 and ("401" in err_msg or "登录" in err_msg or "session" in err_msg.lower() or "timeout" in err_msg.lower()):
                print(f"[Sync/Retry] 账号 {ref[:8]}... 提交异常 ({err_msg})，正在刷新会话并重试...")
                try:
                    await sub_session.refresh_session(force=True)
                    continue
                except Exception:
                    pass
            result["message"] = f"同步失败: {err_msg}"

    # 日志记录
    await log_answer(ref, course_id, question_id,
                     json.dumps(result.get("matched_ranks", [])),
                     result["matched"], result["success"], result["message"])

    return result


async def _sync_direct_to_sub(ref: str, course_id: int, question_id: int,
                               question_type: int,
                               answer: list, files: list, audio: list) -> dict:
    """填空/主观题直接复制答案到子账号（支持自动重试）"""
    result = {"ref": ref, "matched": True, "matched_ranks": answer, "success": False, "message": ""}

    sub_session = get_tm_session(ref)
    for attempt in range(2):
        try:
            await sub_session.submit_answer(
                course_id, question_id, answer, files, audio,
                question_type=question_type,
            )
            result["success"] = True
            result["message"] = "同步成功"
            break
        except Exception as e:
            err_msg = str(e)
            if attempt == 0 and ("401" in err_msg or "登录" in err_msg or "session" in err_msg.lower() or "timeout" in err_msg.lower()):
                try:
                    await sub_session.refresh_session(force=True)
                    continue
                except Exception:
                    pass
            result["message"] = f"同步失败: {err_msg}"

    await log_answer(ref, course_id, question_id,
                     json.dumps(answer), True, result["success"], result["message"])

    return result
