from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.storage.db import Database
from app.storage.models import MediaCacheRecord, StatsSnapshot
from app.utils.urls import Platform


def _parse_iso(raw: str | None) -> datetime | None:
    return datetime.fromisoformat(raw) if raw else None


class CacheService:
    def __init__(self, db: Database, ttl_hours: int) -> None:
        self._db = db
        self._ttl_hours = ttl_hours

    def get_cached_media(self, normalized_url: str, now: datetime | None = None) -> MediaCacheRecord | None:
        current = now or datetime.now(timezone.utc)
        with self._db.connection() as conn:
            row = conn.execute(
                """
                SELECT normalized_url, original_url, source_platform, telegram_file_id,
                       file_size_bytes, created_at, expires_at
                FROM media_cache
                WHERE normalized_url = ?
                """,
                (normalized_url,),
            ).fetchone()
        if not row:
            return None

        expires_at = _parse_iso(row["expires_at"])
        if expires_at and expires_at <= current:
            self.delete(normalized_url)
            return None

        return MediaCacheRecord(
            normalized_url=row["normalized_url"],
            original_url=row["original_url"],
            platform=Platform(row["source_platform"]),
            telegram_file_id=row["telegram_file_id"],
            file_size_bytes=row["file_size_bytes"],
            created_at=datetime.fromisoformat(row["created_at"]),
            expires_at=expires_at,
        )

    def save_media(
        self,
        *,
        normalized_url: str,
        original_url: str,
        platform: Platform,
        telegram_file_id: str,
        file_size_bytes: int | None,
        now: datetime | None = None,
    ) -> None:
        created_at = now or datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=self._ttl_hours)
        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO media_cache(
                    normalized_url, source_platform, telegram_file_id, file_size_bytes,
                    original_url, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(normalized_url)
                DO UPDATE SET
                    source_platform = excluded.source_platform,
                    telegram_file_id = excluded.telegram_file_id,
                    file_size_bytes = excluded.file_size_bytes,
                    original_url = excluded.original_url,
                    created_at = excluded.created_at,
                    expires_at = excluded.expires_at
                """,
                (
                    normalized_url,
                    platform.value,
                    telegram_file_id,
                    file_size_bytes,
                    original_url,
                    created_at.isoformat(),
                    expires_at.isoformat(),
                ),
            )

    def delete(self, normalized_url: str) -> None:
        with self._db.connection() as conn:
            conn.execute("DELETE FROM media_cache WHERE normalized_url = ?", (normalized_url,))

    def cleanup_expired(self, now: datetime | None = None) -> int:
        current = now or datetime.now(timezone.utc)
        with self._db.connection() as conn:
            cursor = conn.execute(
                "DELETE FROM media_cache WHERE expires_at IS NOT NULL AND expires_at <= ?",
                (current.isoformat(),),
            )
            return cursor.rowcount

    def log_request(
        self,
        *,
        user_id: int,
        username: str | None,
        original_url: str | None,
        normalized_url: str | None,
        status: str,
        error_code: str | None = None,
        now: datetime | None = None,
    ) -> None:
        created_at = now or datetime.now(timezone.utc)
        with self._db.connection() as conn:
            conn.execute(
                """
                INSERT INTO request_log(user_id, username, original_url, normalized_url, status, error_code, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    original_url,
                    normalized_url,
                    status,
                    error_code,
                    created_at.isoformat(),
                ),
            )

    def get_stats_snapshot(self, recent_failures_limit: int = 5) -> StatsSnapshot:
        with self._db.connection() as conn:
            total_requests = int(conn.execute("SELECT COUNT(*) FROM request_log").fetchone()[0])
            success_count = int(
                conn.execute("SELECT COUNT(*) FROM request_log WHERE status = 'success'").fetchone()[0]
            )
            failure_count = int(
                conn.execute("SELECT COUNT(*) FROM request_log WHERE status LIKE 'failed:%'").fetchone()[0]
            )
            cache_hit_count = int(
                conn.execute("SELECT COUNT(*) FROM request_log WHERE status = 'cache_hit'").fetchone()[0]
            )
            rows = conn.execute(
                """
                SELECT created_at, error_code, original_url
                FROM request_log
                WHERE status LIKE 'failed:%'
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (recent_failures_limit,),
            ).fetchall()

        recent_failures = [
            f"{row['created_at']} | {row['error_code'] or 'unknown'} | {row['original_url'] or '-'}" for row in rows
        ]
        return StatsSnapshot(
            total_requests=total_requests,
            success_count=success_count,
            failure_count=failure_count,
            cache_hit_count=cache_hit_count,
            recent_failures=recent_failures,
        )
