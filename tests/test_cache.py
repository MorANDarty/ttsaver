from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.cache import CacheService
from app.storage.db import Database
from app.utils.urls import Platform


def test_cache_save_and_get(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    cache = CacheService(db=db, ttl_hours=24)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)

    cache.save_media(
        normalized_url="https://tiktok.com/@alice/video/123",
        original_url="https://www.tiktok.com/@alice/video/123?foo=bar",
        platform=Platform.TIKTOK,
        telegram_file_id="abc123",
        file_size_bytes=1024,
        now=now,
    )

    record = cache.get_cached_media("https://tiktok.com/@alice/video/123", now=now + timedelta(hours=1))
    assert record is not None
    assert record.telegram_file_id == "abc123"


def test_cache_expires_records(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    cache = CacheService(db=db, ttl_hours=1)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)

    cache.save_media(
        normalized_url="https://instagram.com/reel/abc",
        original_url="https://www.instagram.com/reel/abc/",
        platform=Platform.INSTAGRAM,
        telegram_file_id="fileid",
        file_size_bytes=2048,
        now=now,
    )

    expired = cache.get_cached_media("https://instagram.com/reel/abc", now=now + timedelta(hours=2))
    assert expired is None
