from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.utils.urls import Platform


@dataclass
class MediaCacheRecord:
    normalized_url: str
    original_url: str
    platform: Platform
    telegram_file_id: str
    file_size_bytes: int | None
    created_at: datetime
    expires_at: datetime | None


@dataclass
class StatsSnapshot:
    total_requests: int
    success_count: int
    failure_count: int
    cache_hit_count: int
    recent_failures: list[str]
