"""Database helpers and schema.

Hard rule enforced here:
- Anything read from SQLite is converted to plain dicts before leaving this module.
- This prevents runtime errors like: "'sqlite3.Row' object has no attribute 'get'".
"""
from __future__ import annotations

import contextlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple, Union

from backend.config import DATA_DIR, DB_PATH

logger = logging.getLogger("codebot")

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  pw_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  is_admin INTEGER NOT NULL DEFAULT 0,

  stripe_customer_id TEXT,
  stripe_subscription_id TEXT,
  subscription_status TEXT DEFAULT 'none',
  current_period_end INTEGER DEFAULT 0,
  plan TEXT DEFAULT 'none',

  last_login_at INTEGER DEFAULT 0,

  api_key_encrypted TEXT,
  api_key_provider TEXT DEFAULT 'openai'
);

CREATE TABLE IF NOT EXISTS refresh_tokens (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  issued_at INTEGER NOT NULL,
  expires_at INTEGER NOT NULL,
  revoked_at INTEGER DEFAULT 0,
  user_agent TEXT DEFAULT '',
  ip TEXT DEFAULT '',
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS chats (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- NOTE: ai_layer column is used by stream route (safe migration also exists below)
CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  chat_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  ai_layer TEXT NOT NULL DEFAULT '',
  FOREIGN KEY(chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  name TEXT NOT NULL,
  root_path TEXT NOT NULL,
  created_at INTEGER NOT NULL,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS usage_daily (
  user_id TEXT NOT NULL,
  day_utc TEXT NOT NULL,
  prompt_tokens INTEGER NOT NULL DEFAULT 0,
  completion_tokens INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(user_id, day_utc),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS user_credits (
  user_id TEXT PRIMARY KEY,
  credits_remaining REAL NOT NULL DEFAULT 0.0,
  credits_total REAL NOT NULL DEFAULT 0.0,
  monthly_budget REAL NOT NULL DEFAULT 0.0,
  reset_day INTEGER NOT NULL DEFAULT 1,
  last_reset INTEGER NOT NULL DEFAULT 0,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS credit_transactions (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  amount REAL NOT NULL,
  description TEXT NOT NULL,
  model_used TEXT,
  tokens_input INTEGER,
  tokens_output INTEGER,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS file_uploads (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  file_type TEXT NOT NULL,
  file_name TEXT NOT NULL,
  file_path TEXT NOT NULL,
  file_size INTEGER NOT NULL,
  created_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_messages_chat_created ON messages(chat_id, created_at);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_credit_transactions_user ON credit_transactions(user_id, created_at);
CREATE INDEX IF NOT EXISTS idx_file_uploads_user_type ON file_uploads(user_id, file_type, created_at);
CREATE INDEX IF NOT EXISTS idx_chats_user_updated ON chats(user_id, updated_at);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_stripe_customer ON users(stripe_customer_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id, expires_at);

CREATE TABLE IF NOT EXISTS preview_registry (
  project_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
  preview_url TEXT,
  port INTEGER,
  ports_json TEXT,
  started_at TEXT,
  stopped_at TEXT
);

CREATE TABLE IF NOT EXISTS provider_spend (
  user_id TEXT PRIMARY KEY,
  total_spent REAL NOT NULL DEFAULT 0.0,
  updated_at INTEGER NOT NULL,
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS provider_spend_daily (
  user_id TEXT NOT NULL,
  day_utc TEXT NOT NULL,
  total_spent REAL NOT NULL DEFAULT 0.0,
  updated_at INTEGER NOT NULL,
  PRIMARY KEY(user_id, day_utc),
  FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);
"""


def _now() -> int:
    return int(time.time())


def _ensure_db_dir() -> None:
    # Lock everything to one path: backend.config.DB_PATH
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_db_dir()
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    # We keep Row for convenient column access, BUT we never return Row outside this module.
    conn.row_factory = sqlite3.Row

    try:
        conn.execute("PRAGMA foreign_keys=ON;")
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
    except Exception:
        pass

    return conn


def _row_to_dict(row: Any) -> Any:
    """Convert sqlite3.Row to dict; pass through other types safely."""
    if row is None:
        return None
    if isinstance(row, sqlite3.Row):
        # dict(row) produces {col: value, ...}
        return dict(row)
    return row


def _rows_to_dicts(rows: Sequence[Any]) -> List[Any]:
    return [(_row_to_dict(r)) for r in rows]


@contextlib.contextmanager
def db() -> Iterator[sqlite3.Connection]:
    conn = _connect()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# ----------------------------
# Read helpers (ALWAYS dict-safe)
# ----------------------------
SqlParams = Union[Tuple[Any, ...], Dict[str, Any], Sequence[Any]]


def fetchone(
    conn: sqlite3.Connection, sql: str, params: Optional[SqlParams] = None
) -> Optional[Dict[str, Any]]:
    cur = conn.execute(sql, params or ())
    row = cur.fetchone()
    out = _row_to_dict(row)
    return out  # type: ignore[return-value]


def fetchall(
    conn: sqlite3.Connection, sql: str, params: Optional[SqlParams] = None
) -> List[Dict[str, Any]]:
    cur = conn.execute(sql, params or ())
    rows = cur.fetchall()
    out = _rows_to_dicts(rows)
    return out  # type: ignore[return-value]


def scalar(
    conn: sqlite3.Connection, sql: str, params: Optional[SqlParams] = None, default: Any = None
) -> Any:
    cur = conn.execute(sql, params or ())
    row = cur.fetchone()
    if row is None:
        return default
    # sqlite3.Row behaves like a sequence too; handle both
    try:
        return row[0]
    except Exception:
        return default


def execute(
    conn: sqlite3.Connection, sql: str, params: Optional[SqlParams] = None
) -> sqlite3.Cursor:
    return conn.execute(sql, params or ())


def executemany(
    conn: sqlite3.Connection, sql: str, seq_of_params: Sequence[SqlParams]
) -> sqlite3.Cursor:
    return conn.executemany(sql, seq_of_params)


# ----------------------------
# Migrations
# ----------------------------
def _migrate_add_byok_columns() -> None:
    try:
        with db() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(users)").fetchall()]
            if "api_key_encrypted" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN api_key_encrypted TEXT")
                logger.info("Added api_key_encrypted column to users table")
            if "api_key_provider" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN api_key_provider TEXT DEFAULT 'openai'")
                logger.info("Added api_key_provider column to users table")
    except Exception as e:
        logger.warning("BYOK migration check failed (may already be applied): %s", e)


def _migrate_add_messages_ai_layer() -> None:
    """Your stream route inserts ai_layer; ensure the column exists."""
    try:
        with db() as conn:
            cols = [r[1] for r in conn.execute("PRAGMA table_info(messages)").fetchall()]
            if "ai_layer" not in cols:
                conn.execute("ALTER TABLE messages ADD COLUMN ai_layer TEXT NOT NULL DEFAULT ''")
                logger.info("Added ai_layer column to messages table")
    except Exception as e:
        logger.warning("messages.ai_layer migration check failed (may already be applied): %s", e)


def init_db() -> None:
    with db() as conn:
        conn.executescript(SCHEMA_SQL)  # type: ignore
    _migrate_add_byok_columns()
    _migrate_add_messages_ai_layer()
