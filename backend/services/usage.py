"""Usage tracking functions."""
from __future__ import annotations

import datetime as dt
import logging

from backend.database import _now, db

logger = logging.getLogger("codebot")


def usage_bump(user_id: str, prompt_tokens: int, completion_tokens: int) -> None:
    """Track usage for analytics."""
    day = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d")
    now = _now()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO usage_daily (user_id, day_utc, prompt_tokens, completion_tokens, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, day_utc) DO UPDATE SET
              prompt_tokens = prompt_tokens + excluded.prompt_tokens,
              completion_tokens = completion_tokens + excluded.completion_tokens,
              updated_at = excluded.updated_at
            """,
            (user_id, day, int(prompt_tokens), int(completion_tokens), now),
        )

