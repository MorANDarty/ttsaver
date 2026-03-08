from datetime import datetime, timezone
from pathlib import Path

from app.services.rate_limit import RateLimitService
from app.storage.db import Database


def test_rate_limit_respects_daily_quota(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    service = RateLimitService(db=db, daily_limit=2)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)

    first = service.check_and_increment(100, now=now)
    second = service.check_and_increment(100, now=now)
    third = service.check_and_increment(100, now=now)

    assert first.allowed is True
    assert second.allowed is True
    assert third.allowed is False


def test_rate_limit_active_request_guard(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    service = RateLimitService(db=db, daily_limit=5)

    assert service.try_acquire_active_request(100) is True
    assert service.try_acquire_active_request(100) is False
    service.release_active_request(100)
    assert service.try_acquire_active_request(100) is True
