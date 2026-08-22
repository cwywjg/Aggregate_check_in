"""HTTP API for account sync and the hosted AI answer engine.

The client intentionally connects to an IP address over HTTP.  Authentication,
tenant isolation, validation and concurrent persistence are therefore enforced
at the application layer.  The transport URL remains configurable and no
domain or TLS dependency is introduced here.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
import os
import secrets
import socket
import threading
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path
from urllib.parse import urlparse

import requests
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException

from ai_solver import get_ai_runtime_info, solve_yuketang_problem_with_metadata
from safe_json_store import (
    ACCOUNTS_STORE,
    AI_HEALTH_STORE,
    HISTORY_STORE,
    KEYS_STORE,
    PROBLEM_STATE_STORE,
    JsonStoreError,
    data_path,
)


APP_VERSION = "2.6.1"
MAX_ACCOUNTS_PER_SYNC = max(16, int(os.environ.get("YKT_MAX_ACCOUNTS_PER_SYNC", "500")))
MAX_IMAGE_BYTES = max(256 * 1024, int(os.environ.get("YKT_MAX_IMAGE_BYTES", str(5 * 1024 * 1024))))
REQUEST_TIMEOUT = max(3.0, float(os.environ.get("YKT_REQUEST_TIMEOUT", "12")))
ALLOW_REMOTE_ACCOUNT_DELETE = os.environ.get(
    "YKT_ALLOW_REMOTE_ACCOUNT_DELETE",
    "0",
).strip().lower() in {"1", "true", "yes", "on"}
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("YKT_MAX_REQUEST_BYTES", str(4 * 1024 * 1024)))

LOG_FILE = data_path("ai_engine.log")
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=20 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("ykt-api")


def _load_or_create_admin_key() -> str:
    configured = os.environ.get("YKT_ADMIN_KEY", "CWYWJG").strip()
    if configured:
        return configured
    logger.warning("YKT_ADMIN_KEY 为空，使用默认管理员口令 CWYWJG")
    return "CWYWJG"


ADMIN_KEY = _load_or_create_admin_key()


def _key_hash(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _find_key_record(keys_db: dict, raw_key: str) -> dict | None:
    record = keys_db.get(_key_hash(raw_key))
    if isinstance(record, dict):
        return record
    # Read-only compatibility for an older plaintext keys.json.
    legacy = keys_db.get(raw_key)
    return legacy if isinstance(legacy, dict) else None


def _tenant_id_for_key(keys_db: dict, raw_key: str) -> str | None:
    record = _find_key_record(keys_db, raw_key)
    if not record:
        return None
    return str(record.get("tenant_id") or record.get("group_key") or raw_key)


def _find_key_record_by_id(keys_db: dict, key_id: str) -> tuple[str, dict] | tuple[None, None]:
    if not key_id:
        return None, None
    for storage_key, record in keys_db.items():
        if isinstance(record, dict) and secrets.compare_digest(str(record.get("id") or ""), key_id):
            return storage_key, record
    return None, None


def _request_json() -> dict | list:
    value = request.get_json(silent=True)
    return value if isinstance(value, (dict, list)) else {}


def _safe_text(value, maximum: int = 256) -> str:
    return str(value or "").strip()[:maximum]


def _validate_user_key(raw_key: str) -> str | None:
    """User keys have no complexity rule, only transport-safe boundaries."""
    if not raw_key:
        return "Key cannot be empty"
    if len(raw_key) > 128:
        return "Key cannot exceed 128 characters"
    if any(ord(char) < 32 or ord(char) == 127 for char in raw_key):
        return "Key cannot contain control characters"
    return None


def _key_hint(raw_key: str) -> str:
    if len(raw_key) <= 2:
        return "*" * len(raw_key)
    if len(raw_key) <= 6:
        return raw_key[0] + "…" + raw_key[-1]
    return raw_key[:3] + "…" + raw_key[-3:]


def _account_identity(account: dict) -> str:
    return _safe_text(account.get("phone") or account.get("uid") or account.get("id"), 128)


def _normalize_expired(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "expired", "invalid"}


RATE_WINDOWS: dict[tuple[str, str], deque[float]] = defaultdict(deque)
RATE_LOCK = threading.Lock()


def _rate_limit(auth_identity: str, bucket: str, limit: int, seconds: int = 60) -> bool:
    now = time.monotonic()
    key = (auth_identity, bucket)
    with RATE_LOCK:
        events = RATE_WINDOWS[key]
        while events and now - events[0] >= seconds:
            events.popleft()
        if len(events) >= limit:
            return False
        events.append(now)
        return True


PUBLIC_PATHS = {"/api/status"}
ADMIN_PATHS = {
    "/api/admin/verify",
    "/api/sync/keys",
    "/api/sync/create_key",
    "/api/sync/update_key",
    "/api/sync/delete_key",
    "/api/ai/logs",
}


@app.before_request
def authenticate_request():
    if request.method == "OPTIONS" or request.path in PUBLIC_PATHS:
        return None

    auth_key = _safe_text(request.headers.get("Authorization"), 512)
    if not auth_key:
        return jsonify({"code": 401, "msg": "Authorization key required"}), 401

    g.auth_key = auth_key
    g.is_admin = secrets.compare_digest(auth_key, ADMIN_KEY)
    if g.is_admin:
        g.tenant_id = "__admin__"
    else:
        remote_identity = _safe_text(request.remote_addr, 128) or "unknown"
        if request.path in ADMIN_PATHS:
            if not _rate_limit(remote_identity, "admin-auth-failed", 10):
                return jsonify({"code": 429, "msg": "Too many administrator attempts"}), 429
            return jsonify({"code": 403, "msg": "Administrator key required"}), 403
        keys_db = KEYS_STORE.read()
        tenant_id = _tenant_id_for_key(keys_db, auth_key)
        if not tenant_id:
            if not _rate_limit(remote_identity, "unknown-key", 60):
                return jsonify({"code": 429, "msg": "Too many authentication attempts"}), 429
            return jsonify({"code": 403, "msg": "Key is not registered"}), 403
        g.tenant_id = tenant_id

    limit = (
        int(os.environ.get("YKT_AI_RATE_LIMIT", "60"))
        if request.path.startswith("/api/ai/")
        else int(os.environ.get("YKT_API_RATE_LIMIT", "300"))
    )
    bucket = "ai" if request.path.startswith("/api/ai/") else "api"
    if not _rate_limit(_key_hash(auth_key), bucket, limit):
        return jsonify({"code": 429, "msg": "Too many requests"}), 429
    return None


@app.after_request
def harden_response(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.route("/api/status", methods=["GET"])
def server_status():
    return jsonify(
        {
            "code": 0,
            "msg": "Service Running",
            "data": {"version": APP_VERSION, "server_time": int(time.time())},
        }
    )


@app.route("/api/admin/verify", methods=["POST", "GET"])
def verify_admin():
    return jsonify({"code": 0, "msg": "Administrator verified"})


@app.route("/api/sync/keys", methods=["GET"])
def list_keys():
    def normalize(keys_db: dict):
        records = []
        for record in keys_db.values():
            if not isinstance(record, dict):
                continue
            record.setdefault("id", f"key_{uuid.uuid4().hex}")
            records.append(
                {
                    "id": _safe_text(record.get("id"), 80),
                    "remark": _safe_text(record.get("remark"), 80) or "通用用户密钥",
                    "key_hint": _safe_text(record.get("key_hint"), 32) or "***",
                    "created_at": _safe_text(record.get("created_at"), 40),
                    "updated_at": _safe_text(record.get("updated_at"), 40),
                }
            )
        return records

    records = KEYS_STORE.update(normalize)
    records.sort(key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)
    return jsonify({"code": 0, "msg": "ok", "data": records})


@app.route("/api/sync/create_key", methods=["POST"])
def create_key():
    data = _request_json()
    raw_key = _safe_text(data.get("key") if isinstance(data, dict) else "", 128)
    remark = _safe_text(data.get("remark") if isinstance(data, dict) else "", 80) or "通用用户密钥"
    validation_error = _validate_user_key(raw_key)
    if validation_error:
        return jsonify({"code": 400, "msg": validation_error}), 400
    if secrets.compare_digest(raw_key, ADMIN_KEY):
        return jsonify({"code": 409, "msg": "Key is reserved for administrator access"}), 409

    def mutate(keys_db: dict):
        digest = _key_hash(raw_key)
        existing = _find_key_record(keys_db, raw_key) or {}
        keys_db.pop(raw_key, None)
        keys_db[digest] = {
            "id": str(existing.get("id") or f"key_{uuid.uuid4().hex}"),
            "tenant_id": str(existing.get("tenant_id") or uuid.uuid4()),
            "remark": remark,
            "role": "tenant",
            "created_at": existing.get("created_at") or datetime.now().isoformat(timespec="seconds"),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "key_hint": _key_hint(raw_key),
        }

    KEYS_STORE.update(mutate)
    record = _find_key_record(KEYS_STORE.read(), raw_key) or {}
    logger.info("管理员创建或更新租户 Key：%s（%s）", _key_hint(raw_key), remark)
    return jsonify(
        {
            "code": 0,
            "msg": "Key created",
            "key": raw_key,
            "key_id": record.get("id"),
            "remark": remark,
        }
    )


@app.route("/api/sync/update_key", methods=["POST"])
def update_key():
    data = _request_json()
    old_key = _safe_text(data.get("old_key") if isinstance(data, dict) else "", 128)
    key_id = _safe_text(data.get("key_id") if isinstance(data, dict) else "", 80)
    new_key = _safe_text(data.get("new_key") if isinstance(data, dict) else "", 128)
    remark = _safe_text(data.get("remark") if isinstance(data, dict) else "", 80) or "通用用户密钥"
    if not old_key and not key_id:
        return jsonify({"code": 400, "msg": "Old key or key_id is required"}), 400
    validation_error = _validate_user_key(new_key)
    if validation_error:
        return jsonify({"code": 400, "msg": validation_error}), 400
    if secrets.compare_digest(new_key, ADMIN_KEY):
        return jsonify({"code": 409, "msg": "Key is reserved for administrator access"}), 409

    def mutate(keys_db: dict):
        storage_key, existing = _find_key_record_by_id(keys_db, key_id)
        selected_by_id = existing is not None
        if not existing:
            existing = _find_key_record(keys_db, old_key)
            storage_key = _key_hash(old_key) if existing else None
            if existing is not None and storage_key not in keys_db and old_key in keys_db:
                storage_key = old_key
        if not existing:
            return "missing"
        if selected_by_id and old_key:
            old_key_record = _find_key_record(keys_db, old_key)
            if old_key_record is not None and old_key_record is not existing:
                return "mismatch"
        conflict = _find_key_record(keys_db, new_key)
        old_tenant_id = str(existing.get("tenant_id") or existing.get("group_key") or "")
        if conflict and conflict is not existing:
            conflict_tenant_id = str(conflict.get("tenant_id") or conflict.get("group_key") or "")
            if conflict_tenant_id != old_tenant_id:
                return "conflict"

        if storage_key:
            keys_db.pop(storage_key, None)
        if old_key:
            keys_db.pop(old_key, None)
            keys_db.pop(_key_hash(old_key), None)
        keys_db[_key_hash(new_key)] = {
            **existing,
            "id": str(existing.get("id") or key_id or f"key_{uuid.uuid4().hex}"),
            "tenant_id": old_tenant_id or str(uuid.uuid4()),
            "remark": remark,
            "role": "tenant",
            "updated_at": datetime.now().isoformat(timespec="seconds"),
            "key_hint": _key_hint(new_key),
        }
        return "updated"

    result = KEYS_STORE.update(mutate)
    if result == "missing":
        return jsonify({"code": 404, "msg": "Old key not found"}), 404
    if result == "conflict":
        return jsonify({"code": 409, "msg": "New key already belongs to another account group"}), 409
    if result == "mismatch":
        return jsonify({"code": 409, "msg": "old_key and key_id identify different records"}), 409
    logger.info("管理员更新租户 Key：%s -> %s（%s）", _key_hint(old_key), _key_hint(new_key), remark)
    record = _find_key_record(KEYS_STORE.read(), new_key) or {}
    return jsonify(
        {
            "code": 0,
            "msg": "Key updated",
            "key": new_key,
            "key_id": record.get("id"),
            "remark": remark,
        }
    )


@app.route("/api/sync/profile", methods=["GET"])
def sync_profile():
    if g.is_admin:
        return jsonify(
            {
                "code": 0,
                "msg": "ok",
                "data": {"role": "admin", "remark": "管理员", "tenant_id": "__admin__"},
            }
        )
    record = _find_key_record(KEYS_STORE.read(), g.auth_key) or {}
    return jsonify(
        {
            "code": 0,
            "msg": "ok",
            "data": {
                "role": "tenant",
                "remark": _safe_text(record.get("remark"), 80) or "专属账号组",
                "tenant_id": g.tenant_id,
                "key_hint": _safe_text(record.get("key_hint"), 32) or _key_hint(g.auth_key),
            },
        }
    )


ALLOWED_ACCOUNT_FIELDS = {
    "id",
    "phone",
    "uid",
    "name",
    "school",
    "remark",
    "cookie",
    "device",
    "lessonId",
    "lessonToken",
    "lessonContext",
    "lessonCredentialUpdatedAt",
    "ai_mode",
    "expired",
    "validityState",
    "validitySource",
    "validityCheckedAt",
    "validityFailureCount",
}


LESSON_CREDENTIAL_FIELDS = {
    "lessonId",
    "lessonToken",
    "lessonContext",
    "lessonCredentialUpdatedAt",
}

VALIDITY_FIELDS = {
    "expired",
    "validityState",
    "validitySource",
    "validityCheckedAt",
    "validityFailureCount",
}


def _safe_timestamp(value) -> int:
    try:
        return max(0, int(float(value or 0)))
    except (TypeError, ValueError, OverflowError):
        return 0


def _merge_lesson_credentials(target: dict, incoming: dict, is_new: bool) -> None:
    """Merge lesson credentials as one versioned unit.

    A stale client must never erase a newer server-side lesson token merely
    because its local copy is empty.  Explicit clears are accepted only when
    accompanied by a newer ``lessonCredentialUpdatedAt`` timestamp.
    """
    if not any(field in incoming for field in LESSON_CREDENTIAL_FIELDS):
        return

    incoming_updated = _safe_timestamp(incoming.get("lessonCredentialUpdatedAt"))
    stored_updated = _safe_timestamp(target.get("lessonCredentialUpdatedAt"))
    incoming_token = _safe_text(incoming.get("lessonToken"), 256)
    incoming_lesson_id = _safe_text(incoming.get("lessonId"), 256)
    stored_token = _safe_text(target.get("lessonToken"), 256)
    stored_lesson_id = _safe_text(target.get("lessonId"), 256)

    accept = is_new or incoming_updated > stored_updated
    if not accept and incoming_updated == stored_updated:
        # Same-version enrichment is safe when the server does not yet have a
        # usable credential.  It is not safe to replace one usable credential
        # with a different same-version value.
        accept = bool(incoming_token) and not stored_token
        if (
            not accept
            and incoming_token
            and incoming_token == stored_token
            and incoming_lesson_id == stored_lesson_id
            and isinstance(incoming.get("lessonContext"), dict)
        ):
            # Metadata enrichment (course name, dynamic wssUrl, etc.) may be
            # learned after check-in without rotating the actual credential.
            target["lessonContext"] = incoming["lessonContext"]
            return
    if not accept and incoming_updated == 0 and stored_updated == 0:
        # Compatibility for pre-v2.6 clients: permit a non-empty credential to
        # initialize/refresh an empty or same-lesson record, but never permit a
        # legacy empty payload to clear a non-empty server credential.
        accept = bool(incoming_token) and (
            not stored_token
            or not stored_lesson_id
            or not incoming_lesson_id
            or stored_lesson_id == incoming_lesson_id
        )
    if not accept:
        return

    target["lessonId"] = incoming_lesson_id
    target["lessonToken"] = incoming_token
    context = incoming.get("lessonContext")
    target["lessonContext"] = context if context is None or isinstance(context, dict) else None
    target["lessonCredentialUpdatedAt"] = incoming_updated


def _merge_validity(target: dict, incoming: dict, is_new: bool) -> None:
    """Merge validity evidence as one timestamped unit.

    A client-side ``unknown`` result must not erase a newer explicit server
    monitor result.  Explicit ``valid``/``expired`` evidence may replace the
    stored state only when it is at least as recent.
    """
    if not any(field in incoming for field in VALIDITY_FIELDS):
        return

    incoming_checked = _safe_timestamp(incoming.get("validityCheckedAt"))
    stored_checked = _safe_timestamp(target.get("validityCheckedAt"))
    raw_state = str(incoming.get("validityState") or "").strip().lower()
    explicit_state = raw_state if raw_state in {"valid", "expired"} else ""

    accept = is_new or bool(explicit_state and incoming_checked >= stored_checked)
    if not accept:
        return

    if explicit_state:
        target["validityState"] = explicit_state
        target["expired"] = explicit_state == "expired"
    else:
        target["validityState"] = "unknown"
        target["expired"] = _normalize_expired(incoming.get("expired"))
    target["validitySource"] = _safe_text(incoming.get("validitySource"), 64)
    target["validityCheckedAt"] = incoming_checked
    try:
        failure_count = int(incoming.get("validityFailureCount") or 0)
    except (TypeError, ValueError, OverflowError):
        failure_count = 0
    target["validityFailureCount"] = max(0, min(failure_count, 1_000_000))


def _merge_account(target: dict, incoming: dict, tenant_id: str, is_new: bool) -> None:
    _merge_lesson_credentials(target, incoming, is_new)
    _merge_validity(target, incoming, is_new)
    for field in ALLOWED_ACCOUNT_FIELDS:
        if field in LESSON_CREDENTIAL_FIELDS or field in VALIDITY_FIELDS:
            continue
        if field not in incoming or incoming[field] is None:
            continue
        if field in {"phone", "uid", "name", "school", "remark", "cookie"}:
            target[field] = _safe_text(incoming[field], 8192 if field == "cookie" else 256)
        elif field == "device":
            if isinstance(incoming[field], dict):
                target[field] = incoming[field]
        elif field == "ai_mode":
            target[field] = bool(incoming[field])
        elif field == "id":
            target[field] = incoming[field]
    target["group_key"] = tenant_id
    target["updated_at"] = int(time.time() * 1000)
    if is_new:
        target.setdefault("ai_mode", False)
        target.setdefault("expired", False)
        target.setdefault("validityState", "unknown")


@app.route("/api/sync/upload", methods=["POST"])
def upload_accounts():
    body = _request_json()
    if isinstance(body, list):
        incoming_accounts = body
        custom_remark = ""
    else:
        incoming_accounts = body.get("accounts", [])
        custom_remark = _safe_text(body.get("remark"), 80)
    deleted_accounts = body.get("deleted_accounts", []) if isinstance(body, dict) else []
    if not isinstance(incoming_accounts, list):
        return jsonify({"code": 400, "msg": "accounts must be an array"}), 400
    if not isinstance(deleted_accounts, list):
        return jsonify({"code": 400, "msg": "deleted_accounts must be an array"}), 400
    if len(incoming_accounts) > MAX_ACCOUNTS_PER_SYNC:
        return jsonify({"code": 413, "msg": f"Maximum {MAX_ACCOUNTS_PER_SYNC} accounts per sync"}), 413
    if len(deleted_accounts) > MAX_ACCOUNTS_PER_SYNC:
        return jsonify({"code": 413, "msg": f"Maximum {MAX_ACCOUNTS_PER_SYNC} deletions per sync"}), 413
    ignored_deletions = 0
    if deleted_accounts and not ALLOW_REMOTE_ACCOUNT_DELETE:
        ignored_deletions = len(deleted_accounts)
        deleted_accounts = []
        logger.warning(
            "已忽略客户端账号删除请求：tenant=%s count=%s",
            g.tenant_id,
            ignored_deletions,
        )

    tenant_id = g.tenant_id
    if g.is_admin:
        requested_tenant = _safe_text(
            body.get("tenant_id") if isinstance(body, dict) else "",
            128,
        )
        tenant_id = requested_tenant or "__admin__"

    clean_accounts = [item for item in incoming_accounts if isinstance(item, dict) and _account_identity(item)]
    deleted_identities = {
        _account_identity(item)
        for item in deleted_accounts
        if isinstance(item, dict) and _account_identity(item)
    }

    def mutate(db_accounts: list):
        before_delete = len(db_accounts)
        if deleted_identities:
            db_accounts[:] = [
                account
                for account in db_accounts
                if not (
                    isinstance(account, dict)
                    and str(account.get("group_key") or "") == tenant_id
                    and _account_identity(account) in deleted_identities
                )
            ]
        deleted = before_delete - len(db_accounts)
        index = {
            (str(acc.get("group_key") or ""), _account_identity(acc)): acc
            for acc in db_accounts
            if isinstance(acc, dict) and _account_identity(acc)
        }
        inserted = 0
        updated = 0
        for incoming in clean_accounts:
            identity = _account_identity(incoming)
            key = (tenant_id, identity)
            target = index.get(key)
            if target is None:
                target = {}
                _merge_account(target, incoming, tenant_id, True)
                db_accounts.append(target)
                index[key] = target
                inserted += 1
            else:
                _merge_account(target, incoming, tenant_id, False)
                updated += 1
        return inserted, updated, deleted

    inserted, updated, deleted = ACCOUNTS_STORE.update(mutate)

    if custom_remark and not g.is_admin:
        def update_remark(keys_db: dict):
            record = _find_key_record(keys_db, g.auth_key)
            if record:
                record["remark"] = custom_remark
                record["updated_at"] = datetime.now().isoformat(timespec="seconds")

        KEYS_STORE.update(update_remark)

    total = sum(1 for item in ACCOUNTS_STORE.read() if str(item.get("group_key")) == tenant_id)
    logger.info(
        "租户 %s 同步：新增 %s，更新 %s，删除 %s，总数 %s",
        tenant_id,
        inserted,
        updated,
        deleted,
        total,
    )
    return jsonify(
        {
            "code": 0,
            "msg": "Sync successful",
            "inserted": inserted,
            "updated": updated,
            "deleted": deleted,
            "ignored_deletions": ignored_deletions,
            "total": total,
        }
    )


@app.route("/api/sync/download", methods=["GET"])
def download_accounts():
    tenant_id = g.tenant_id
    if g.is_admin and request.args.get("all") == "1":
        selected = ACCOUNTS_STORE.read()
        remark = "管理员全量视图"
    else:
        selected = [
            account
            for account in ACCOUNTS_STORE.read()
            if str(account.get("group_key") or "") == tenant_id
        ]
        keys_db = KEYS_STORE.read()
        record = _find_key_record(keys_db, g.auth_key) if not g.is_admin else None
        remark = _safe_text(record.get("remark") if record else "", 80) or "专属账号组"
    return jsonify({"code": 0, "msg": "success", "remark": remark, "data": selected})


_AI_RUNTIME = get_ai_runtime_info()
_AI_PRIMARY_ROUTE = (
    _AI_RUNTIME["routes"][0]
    if _AI_RUNTIME.get("routes")
    else {
        "provider": _AI_RUNTIME["provider"],
        "model": _AI_RUNTIME["models"][0] if _AI_RUNTIME["models"] else "",
    }
)
ai_status_state = {
    "ready": False,
    "provider": _AI_PRIMARY_ROUTE.get("provider", ""),
    "model": _AI_PRIMARY_ROUTE.get("model", ""),
    "routes": _AI_RUNTIME.get("routes", []),
    "configured": _AI_RUNTIME["configured"],
    "last_check": "",
    "msg": "尚未执行连通性检测",
}


def _run_ai_test() -> tuple[list, str]:
    runtime = get_ai_runtime_info()
    options = [{"key": "A", "value": "4"}, {"key": "B", "value": "3"}]
    answers, error, metadata = solve_yuketang_problem_with_metadata(
        0,
        "2+2等于多少？",
        options,
    )
    ai_status_state.update(
        {
            "ready": bool(answers),
            "provider": metadata.get("provider") or runtime["provider"],
            "model": metadata.get("model") or (runtime["models"][0] if runtime["models"] else ""),
            "routes": runtime.get("routes", []),
            "configured": runtime["configured"],
            "last_check": datetime.now().strftime("%H:%M:%S"),
            "msg": "AI 引擎工作正常" if answers else f"AI 异常：{error or 'empty response'}",
        }
    )
    return answers, error


@app.route("/api/ai/test", methods=["POST", "GET"])
def test_ai_engine():
    answers, error = _run_ai_test()
    status = 200 if answers else 502
    return jsonify(
        {
            "code": 0 if answers else 502,
            "msg": "AI 引擎工作正常" if answers else error or "AI returned no result",
            "data": answers,
            "ai_status": ai_status_state,
        }
    ), status


@app.route("/api/ai/logs", methods=["GET"])
def get_ai_logs():
    if not LOG_FILE.exists():
        return jsonify({"code": 0, "data": []})
    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as handle:
        lines = handle.readlines()
    return jsonify({"code": 0, "data": [line.rstrip() for line in lines[-200:]]})


@app.route("/api/ai/history", methods=["GET"])
def get_ai_history():
    history = HISTORY_STORE.read()
    if not g.is_admin or request.args.get("all") != "1":
        history = [
            record
            for record in history
            if str(record.get("groupKey") or "") == str(g.tenant_id)
        ]
    health_state = AI_HEALTH_STORE.read()
    if not isinstance(health_state, dict):
        health_state = {}
    latest_health = health_state.get("latest")
    if not isinstance(latest_health, dict):
        latest_health = None

    visible_status = dict(ai_status_state)
    latest_routed = next(
        (
            record
            for record in history
            if record.get("aiModel") or record.get("aiProvider")
        ),
        None,
    )
    if latest_health:
        health_ok = latest_health.get("success") is True
        visible_status.update(
            {
                "ready": health_ok,
                "provider": latest_health.get("provider") or "nvidia",
                "model": latest_health.get("model") or "google/gemma-4-31b-it",
                "last_check": latest_health.get("checkedAtText") or "",
                "msg": "成功" if health_ok else "失败",
            }
        )
    elif latest_routed:
        visible_status["provider"] = latest_routed.get("aiProvider") or visible_status["provider"]
        visible_status["model"] = latest_routed.get("aiModel") or visible_status["model"]
    now_ms = int(time.time() * 1000)
    active_statuses = {"processing"}
    active_tasks = [
        state
        for state in PROBLEM_STATE_STORE.read().values()
        if isinstance(state, dict)
        and str(state.get("groupKey") or "") == str(g.tenant_id)
        and str(state.get("status") or "") in active_statuses
        and now_ms - int(state.get("updatedAt") or 0) < 120_000
    ]
    active_tasks.sort(key=lambda state: int(state.get("updatedAt") or 0), reverse=True)
    return jsonify(
        {
            "code": 0,
            "msg": "ok",
            "data": history,
            "ai_status": visible_status,
            "ai_health": health_state,
            "active_tasks": active_tasks,
            "server_time": now_ms,
        }
    )


@app.route("/api/ai/health", methods=["GET"])
def get_ai_health():
    health_state = AI_HEALTH_STORE.read()
    if not isinstance(health_state, dict):
        health_state = {}
    latest = health_state.get("latest")
    if not isinstance(latest, dict):
        latest = None
    return jsonify(
        {
            "code": 0,
            "msg": "ok",
            "data": health_state,
            "status": (
                "成功"
                if latest and latest.get("success") is True
                else "失败"
                if latest
                else "尚未检测"
            ),
        }
    )


def _host_allowed(hostname: str) -> bool:
    configured = {
        item.strip().lower()
        for item in os.environ.get("YKT_IMAGE_HOSTS", "").split(",")
        if item.strip()
    }
    host = hostname.lower().rstrip(".")
    if host == "yuketang.cn" or host.endswith(".yuketang.cn"):
        return True
    return host in configured


def _assert_public_host(hostname: str, port: int) -> None:
    addresses = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise ValueError("image host has no address")
    for address in addresses:
        ip = ipaddress.ip_address(address[4][0])
        if not ip.is_global:
            raise ValueError("private or local image address rejected")


def _safe_fetch_image(image_url: str) -> bytes:
    parsed = urlparse(image_url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise ValueError("image URL must be http or https")
    if parsed.username or parsed.password or not _host_allowed(parsed.hostname):
        raise ValueError("image host is not allowed")
    _assert_public_host(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80))
    with requests.get(
        image_url,
        headers={"User-Agent": "YKT-AI/2.1"},
        timeout=REQUEST_TIMEOUT,
        stream=True,
        allow_redirects=False,
    ) as response:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "").lower()
        if not content_type.startswith("image/"):
            raise ValueError("remote content is not an image")
        declared = int(response.headers.get("Content-Length") or 0)
        if declared > MAX_IMAGE_BYTES:
            raise ValueError("image is too large")
        chunks = []
        total = 0
        for chunk in response.iter_content(64 * 1024):
            total += len(chunk)
            if total > MAX_IMAGE_BYTES:
                raise ValueError("image is too large")
            chunks.append(chunk)
        return b"".join(chunks)


@app.route("/api/ai/solve", methods=["POST"])
def ai_solve():
    data = _request_json()
    problem_type = data.get("problem_type")
    try:
        problem_type = int(problem_type)
    except (TypeError, ValueError):
        return jsonify({"code": 400, "msg": "invalid problem_type", "answers": []}), 400
    if problem_type not in {0, 1, 2, 3, 4}:
        return jsonify({"code": 400, "msg": "unsupported problem_type", "answers": []}), 400
    body = _safe_text(data.get("body"), 20000)
    options = data.get("options") if isinstance(data.get("options"), list) else []
    blank_count = _safe_timestamp(data.get("blank_count")) or None
    max_select = _safe_timestamp(data.get("max_select")) or None
    image_url = _safe_text(data.get("image_url"), 2048)
    image_bytes = None
    if image_url:
        try:
            image_bytes = _safe_fetch_image(image_url)
        except Exception as exc:
            return jsonify({"code": 400, "msg": f"image rejected: {exc}", "answers": []}), 400

    started = time.monotonic()
    answers, error, metadata = solve_yuketang_problem_with_metadata(
        problem_type,
        body,
        options,
        image_bytes,
        blank_count=blank_count,
        max_select=max_select,
    )
    elapsed = round(time.monotonic() - started, 2)
    if not answers:
        return jsonify(
            {
                "code": 502,
                "msg": error or "AI returned no result",
                "answers": [],
                "elapsed": elapsed,
                "provider": metadata.get("provider", ""),
                "model": metadata.get("model", ""),
                "ai_metadata": metadata,
            }
        ), 502
    ai_status_state.update(
        {
            "ready": True,
            "provider": metadata.get("provider", ""),
            "model": metadata.get("model", ""),
            "ai_metadata": metadata,
            "configured": True,
            "last_check": datetime.now().strftime("%H:%M:%S"),
            "msg": "AI 引擎工作正常",
        }
    )
    return jsonify(
        {
            "code": 0,
            "answers": answers,
            "elapsed": elapsed,
            "provider": metadata.get("provider", ""),
            "model": metadata.get("model", ""),
        }
    )


@app.route("/api/ai/history/record", methods=["POST"])
def record_ai_history():
    data = _request_json()
    now = datetime.now()
    record = {
        "id": _safe_text(data.get("id"), 128) or f"rec_{uuid.uuid4().hex}",
        "timestamp": int(data.get("timestamp") or data.get("problemStartedAt") or int(now.timestamp() * 1000)),
        "problemStartedAt": int(data.get("problemStartedAt") or data.get("timestamp") or int(now.timestamp() * 1000)),
        "groupKey": g.tenant_id,
        "time": _safe_text(data.get("time"), 16) or now.strftime("%H:%M:%S"),
        "date": _safe_text(data.get("date"), 16) or now.strftime("%Y-%m-%d"),
        "lessonId": _safe_text(data.get("lessonId"), 128),
        "lessonName": _safe_text(data.get("lessonName"), 256),
        "courseName": _safe_text(data.get("courseName"), 256),
        "lessonTitle": _safe_text(data.get("lessonTitle"), 256),
        "problemId": _safe_text(data.get("problemId"), 128),
        "problemType": _safe_text(data.get("problemType"), 64),
        "body": _safe_text(data.get("body"), 20000),
        "options": data.get("options") if isinstance(data.get("options"), list) else [],
        "aiAnswer": data.get("aiAnswer") if isinstance(data.get("aiAnswer"), list) else [],
        "aiProvider": _safe_text(data.get("aiProvider"), 64),
        "aiModel": _safe_text(data.get("aiModel"), 256),
        "aiAttempts": data.get("aiAttempts") if isinstance(data.get("aiAttempts"), list) else [],
        "aiAttemptCount": int(data.get("aiAttemptCount") or 0),
        "aiFallbackUsed": bool(data.get("aiFallbackUsed")),
        "correctAnswer": data.get("correctAnswer") if isinstance(data.get("correctAnswer"), list) else [],
        "elapsedSeconds": float(data.get("elapsedSeconds") or 0),
        "answerReadySeconds": float(data.get("answerReadySeconds") or 0),
        "submitStartedSeconds": float(data.get("submitStartedSeconds") or 0),
        "submittedSeconds": float(data.get("submittedSeconds") or 0),
        "cover": _safe_text(data.get("cover"), 2048),
        "totalAccounts": int(data.get("totalAccounts") or 0),
        "successCount": int(data.get("successCount") or 0),
        "successAccounts": data.get("successAccounts") if isinstance(data.get("successAccounts"), list) else [],
        "status": _safe_text(data.get("status"), 32) or "success",
    }

    def mutate(history: list):
        history.insert(0, record)
        del history[500:]

    HISTORY_STORE.update(mutate)
    return jsonify({"code": 0, "msg": "recorded", "id": record["id"]})


@app.route("/api/sync/delete_key", methods=["POST"])
def delete_key():
    data = _request_json()
    raw_key = _safe_text(data.get("key"), 128)
    key_id = _safe_text(data.get("key_id"), 80)
    if not raw_key and not key_id:
        return jsonify({"code": 400, "msg": "Missing key or key_id"}), 400

    def mutate(keys_db: dict):
        storage_key, record = _find_key_record_by_id(keys_db, key_id)
        selected_by_id = record is not None
        if selected_by_id and raw_key:
            raw_record = _find_key_record(keys_db, raw_key)
            if raw_record is not None and raw_record is not record:
                return "mismatch", None
        removed = keys_db.pop(storage_key, None) if storage_key else None
        if raw_key:
            raw_removed = keys_db.pop(_key_hash(raw_key), None)
            legacy_removed = keys_db.pop(raw_key, None)
            removed = removed or raw_removed or legacy_removed
        return "deleted" if removed else "missing", removed

    delete_status, removed = KEYS_STORE.update(mutate)
    if delete_status == "mismatch":
        return jsonify({"code": 409, "msg": "key and key_id identify different records"}), 409
    if delete_status == "missing" or not removed:
        return jsonify({"code": 404, "msg": "Key not found"}), 404
    tenant_id = str(removed.get("tenant_id") or removed.get("group_key") or "")

    def purge_accounts(accounts: list):
        before = len(accounts)
        accounts[:] = [
            account
            for account in accounts
            if str(account.get("group_key") or "") != tenant_id
        ]
        return before - len(accounts)

    def purge_history(history: list):
        before = len(history)
        history[:] = [
            record
            for record in history
            if str(record.get("groupKey") or "") != tenant_id
        ]
        return before - len(history)

    def purge_problem_states(states: dict):
        stale_keys = [
            state_key
            for state_key, state in states.items()
            if isinstance(state, dict)
            and str(state.get("groupKey") or "") == tenant_id
        ]
        for state_key in stale_keys:
            states.pop(state_key, None)
        return len(stale_keys)

    purged = {
        "accounts": ACCOUNTS_STORE.update(purge_accounts) if tenant_id else 0,
        "history": HISTORY_STORE.update(purge_history) if tenant_id else 0,
        "problem_states": PROBLEM_STATE_STORE.update(purge_problem_states) if tenant_id else 0,
    }
    logger.info("管理员删除租户 Key：%s", _key_hint(raw_key))
    return jsonify({"code": 0, "msg": "Key deleted", "purged": purged})


def _auto_ai_tester_loop():
    while True:
        try:
            _run_ai_test()
        except Exception:
            logger.exception("AI 定时自检失败")
        time.sleep(1800)


if os.environ.get("YKT_ENABLE_AI_SELF_TEST", "0") == "1":
    threading.Thread(target=_auto_ai_tester_loop, daemon=True, name="ai-self-test").start()


@app.errorhandler(JsonStoreError)
def handle_store_error(exc):
    logger.exception("数据存储异常")
    return jsonify({"code": 503, "msg": "Data store is temporarily unavailable"}), 503


@app.errorhandler(413)
def handle_too_large(_exc):
    return jsonify({"code": 413, "msg": "Request body is too large"}), 413


@app.errorhandler(HTTPException)
def handle_http_exception(exc: HTTPException):
    return jsonify({"code": exc.code or 400, "msg": exc.description or "HTTP error"}), exc.code or 400


@app.errorhandler(Exception)
def handle_global_exception(exc):
    logger.exception("未捕获的服务端异常")
    return jsonify({"code": 500, "msg": "Internal server error"}), 500


if __name__ == "__main__":
    host = os.environ.get("YKT_BIND_HOST", "0.0.0.0")
    port = int(os.environ.get("YKT_PORT", "5000"))
    logger.info("雨课堂同步 API %s 启动：http://%s:%s", APP_VERSION, host, port)
    try:
        from waitress import serve

        serve(
            app,
            host=host,
            port=port,
            threads=max(8, int(os.environ.get("YKT_HTTP_THREADS", "24"))),
            channel_timeout=60,
        )
    except ImportError:
        logger.warning("waitress 未安装，临时使用 Flask threaded server")
        app.run(host=host, port=port, threaded=True, use_reloader=False)
