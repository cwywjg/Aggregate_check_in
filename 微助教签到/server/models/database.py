"""
SQLite 数据库管理 (async) — 单例连接模式
"""
import aiosqlite
from config import DB_PATH

_db: aiosqlite.Connection | None = None

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts_ext (
    ref TEXT PRIMARY KEY,
    is_master INTEGER DEFAULT 0,
    tm_openid TEXT,
    tm_session TEXT,
    tm_session_sig TEXT,
    tm_session_expires INTEGER DEFAULT 0,
    keepalive_status TEXT DEFAULT 'unknown',
    last_keepalive_at TEXT,
    keepalive_fail_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS answer_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    question_type INTEGER,
    master_ref TEXT,
    master_ranks TEXT,
    master_contents TEXT,
    plain_texts TEXT,
    file_keys TEXT,
    submitted_at TEXT DEFAULT (datetime('now')),
    UNIQUE(course_id, question_id)
);

CREATE TABLE IF NOT EXISTS signin_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref TEXT NOT NULL,
    extra_hash TEXT,
    success INTEGER,
    message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS answer_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref TEXT NOT NULL,
    course_id INTEGER,
    question_id INTEGER,
    submitted_ranks TEXT,
    matched_from_master INTEGER DEFAULT 0,
    success INTEGER,
    message TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""

# ── 单例连接 ──

async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（单例模式，整个应用复用同一个连接）"""
    global _db
    if _db is None:
        _db = await aiosqlite.connect(DB_PATH)
        _db.row_factory = aiosqlite.Row
        await _db.execute("PRAGMA journal_mode=WAL")
        await _db.execute("PRAGMA busy_timeout=5000")
    return _db


async def close_db():
    """关闭数据库连接（优雅退出时调用）"""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


async def init_db():
    """初始化数据库表"""
    db = await get_db()
    await db.executescript(SCHEMA)
    await db.commit()
    # 迁移：逐列检查，避免“第一列已存在”导致后续缺失列被跳过。
    cursor = await db.execute("PRAGMA table_info(accounts_ext)")
    existing_columns = {row[1] for row in await cursor.fetchall()}
    migrations = {
        "keepalive_status": "ALTER TABLE accounts_ext ADD COLUMN keepalive_status TEXT DEFAULT 'unknown'",
        "last_keepalive_at": "ALTER TABLE accounts_ext ADD COLUMN last_keepalive_at TEXT",
        "keepalive_fail_count": "ALTER TABLE accounts_ext ADD COLUMN keepalive_fail_count INTEGER DEFAULT 0",
        "last_probe_at": "ALTER TABLE accounts_ext ADD COLUMN last_probe_at TEXT",
        "last_probe_status": "ALTER TABLE accounts_ext ADD COLUMN last_probe_status TEXT DEFAULT 'unknown'",
    }
    added = []
    for column, statement in migrations.items():
        if column not in existing_columns:
            await db.execute(statement)
            added.append(column)
    if added:
        await db.commit()
        print(f"[DB] Migrated columns: {', '.join(added)}")


# ── 账号扩展表操作 ──

async def get_account_ext(ref: str) -> dict | None:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM accounts_ext WHERE ref = ?", (ref,))
    row = await cursor.fetchone()
    return dict(row) if row else None


async def upsert_account_ext(ref: str, **kwargs):
    """使用 SQLite UPSERT 实现原子更新"""
    db = await get_db()
    kwargs["ref"] = ref
    cols = list(kwargs.keys())
    placeholders = ", ".join("?" for _ in cols)
    col_names = ", ".join(cols)
    # 除 ref 外的列用于 ON CONFLICT 更新
    update_cols = [c for c in cols if c != "ref"]
    update_clause = ", ".join(f"{c} = excluded.{c}" for c in update_cols)
    if update_clause:
        update_clause += ", updated_at = datetime('now')"
    else:
        update_clause = "updated_at = datetime('now')"
    await db.execute(
        f"INSERT INTO accounts_ext ({col_names}) VALUES ({placeholders}) "
        f"ON CONFLICT(ref) DO UPDATE SET {update_clause}",
        list(kwargs.values())
    )
    await db.commit()


async def set_master_account(ref: str):
    db = await get_db()
    await db.execute("UPDATE accounts_ext SET is_master = 0")
    await db.execute("UPDATE accounts_ext SET is_master = 1 WHERE ref = ?", (ref,))
    await db.commit()


async def get_master_ref() -> str | None:
    db = await get_db()
    cursor = await db.execute("SELECT ref FROM accounts_ext WHERE is_master = 1 LIMIT 1")
    row = await cursor.fetchone()
    return row["ref"] if row else None


async def get_all_account_exts() -> list[dict]:
    db = await get_db()
    cursor = await db.execute("SELECT * FROM accounts_ext ORDER BY is_master DESC, created_at ASC")
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def delete_account_ext(ref: str):
    db = await get_db()
    await db.execute("DELETE FROM accounts_ext WHERE ref = ?", (ref,))
    await db.commit()


async def update_keepalive_status(ref: str, status: str, fail_count: int = 0):
    """更新凭证轮换保活状态"""
    db = await get_db()
    if status == 'alive':
        await db.execute(
            """UPDATE accounts_ext 
               SET keepalive_status = ?, last_keepalive_at = datetime('now'), 
                   keepalive_fail_count = 0, updated_at = datetime('now')
               WHERE ref = ?""",
            (status, ref)
        )
    else:
        await db.execute(
            """UPDATE accounts_ext 
               SET keepalive_status = ?, keepalive_fail_count = ?, 
                   updated_at = datetime('now')
               WHERE ref = ?""",
            (status, fail_count, ref)
        )
    await db.commit()


async def update_probe_status(ref: str, status: str):
    """更新独立小程序 Code 有效性实测检验时间"""
    db = await get_db()
    await db.execute(
        """UPDATE accounts_ext 
           SET last_probe_at = datetime('now'), last_probe_status = ?, 
               updated_at = datetime('now')
           WHERE ref = ?""",
        (status, ref)
    )
    await db.commit()


async def get_all_keepalive_status() -> list[dict]:
    """获取所有账号的保活状态摘要"""
    db = await get_db()
    cursor = await db.execute(
        """SELECT ref, is_master, keepalive_status, last_keepalive_at, 
                  last_probe_at, last_probe_status,
                  keepalive_fail_count, updated_at 
           FROM accounts_ext ORDER BY is_master DESC, created_at ASC"""
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]


async def reset_keepalive_for_ref(ref: str):
    """重扫成功后重置保活状态"""
    db = await get_db()
    await db.execute(
        """UPDATE accounts_ext 
           SET keepalive_status = 'alive', keepalive_fail_count = 0, 
               last_keepalive_at = datetime('now'), last_probe_at = datetime('now'),
               last_probe_status = 'alive', updated_at = datetime('now')
           WHERE ref = ?""",
        (ref,)
    )
    await db.commit()


# ── 答案缓存 ──

async def cache_answer(course_id: int, question_id: int, question_type: int,
                       master_ref: str, master_ranks: str, master_contents: str,
                       plain_texts: str, file_keys: str = "[]"):
    db = await get_db()
    await db.execute("""
        INSERT OR REPLACE INTO answer_cache 
        (course_id, question_id, question_type, master_ref, master_ranks, 
         master_contents, plain_texts, file_keys, submitted_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
    """, (course_id, question_id, question_type, master_ref,
          master_ranks, master_contents, plain_texts, file_keys))
    await db.commit()


async def get_cached_answer(course_id: int, question_id: int) -> dict | None:
    db = await get_db()
    if course_id:
        cursor = await db.execute(
            "SELECT * FROM answer_cache WHERE course_id = ? AND question_id = ?",
            (course_id, question_id)
        )
    else:
        # 兼容未携带 courseId 的旧客户端；question_id 在微助教侧全局唯一。
        cursor = await db.execute(
            "SELECT * FROM answer_cache WHERE question_id = ? ORDER BY submitted_at DESC LIMIT 1",
            (question_id,)
        )
    row = await cursor.fetchone()
    return dict(row) if row else None


# ── 日志 ──

async def log_signin(ref: str, extra_hash: str, success: bool, message: str):
    db = await get_db()
    await db.execute(
        "INSERT INTO signin_log (ref, extra_hash, success, message) VALUES (?, ?, ?, ?)",
        (ref, extra_hash, 1 if success else 0, message)
    )
    await db.commit()


async def log_answer(ref: str, course_id: int, question_id: int,
                     submitted_ranks: str, matched: bool, success: bool, message: str):
    db = await get_db()
    await db.execute("""
        INSERT INTO answer_log 
        (ref, course_id, question_id, submitted_ranks, matched_from_master, success, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (ref, course_id, question_id, submitted_ranks,
          1 if matched else 0, 1 if success else 0, message))
    await db.commit()


async def get_signin_history(limit: int = 50) -> list[dict]:
    db = await get_db()
    cursor = await db.execute(
        "SELECT * FROM signin_log ORDER BY created_at DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(r) for r in rows]
