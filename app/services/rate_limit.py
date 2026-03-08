from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.storage.db import Database


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int


class RateLimitService:
    def __init__(self, db: Database, daily_limit: int) -> None:
        self._db = db
        self._daily_limit = daily_limit
        self._active_users: set[int] = set()

    def _bucket(self, now: datetime | None = None) -> str:
        current = now or datetime.now(timezone.utc)
        return current.date().isoformat()

    def check_and_increment(self, user_id: int, now: datetime | None = None) -> RateLimitDecision:
        bucket = self._bucket(now)
        with self._db.connection() as conn:
            row = conn.execute(
                "SELECT request_count FROM user_rate_limit WHERE user_id = ? AND day_bucket = ?",
                (user_id, bucket),
            ).fetchone()
            current = int(row["request_count"]) if row else 0
            if current >= self._daily_limit:
                return RateLimitDecision(allowed=False, remaining=0)

            new_value = current + 1
            conn.execute(
                """
                INSERT INTO user_rate_limit(user_id, day_bucket, request_count)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, day_bucket)
                DO UPDATE SET request_count = excluded.request_count
                """,
                (user_id, bucket, new_value),
            )
        return RateLimitDecision(allowed=True, remaining=max(self._daily_limit - new_value, 0))

    def try_acquire_active_request(self, user_id: int) -> bool:
        if user_id in self._active_users:
            return False
        self._active_users.add(user_id)
        return True

    def release_active_request(self, user_id: int) -> None:
        self._active_users.discard(user_id)
