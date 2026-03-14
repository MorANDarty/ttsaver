from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.access import AccessService
from app.storage.db import Database
from app.storage.models import (
    AccessRequestCreateStatus,
    AccessRequestDecisionStatus,
    AccessRequestStatus,
    UserAccessState,
    UserAccessStatus,
)


def test_create_access_request_blocks_duplicate_pending(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    service = AccessService(db=db, request_cooldown_hours=24)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)

    first = service.create_request(user_id=100, username="alice", first_name="Alice", now=now)
    second = service.create_request(user_id=100, username="alice", first_name="Alice", now=now)

    assert first.status == AccessRequestCreateStatus.CREATED
    assert first.request is not None
    assert second.status == AccessRequestCreateStatus.ALREADY_PENDING
    assert second.request is not None
    assert second.request.id == first.request.id


def test_approve_request_activates_user_access(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    service = AccessService(db=db, request_cooldown_hours=24)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
    created = service.create_request(user_id=100, username="alice", first_name="Alice", now=now)

    assert created.request is not None
    approved = service.approve_request(
        request_id=created.request.id,
        admin_user_id=999,
        now=now + timedelta(minutes=5),
    )

    assert approved.status == AccessRequestDecisionStatus.APPROVED
    assert approved.request is not None
    assert approved.request.status == AccessRequestStatus.APPROVED
    assert approved.user_access is not None
    assert approved.user_access.status == UserAccessStatus.ACTIVE
    assert approved.user_access.granted_by_admin_id == 999
    assert service.is_allowed(100) is True


def test_reject_request_enforces_cooldown(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    service = AccessService(db=db, request_cooldown_hours=24)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
    created = service.create_request(user_id=100, username="alice", first_name="Alice", now=now)

    assert created.request is not None
    rejected = service.reject_request(
        request_id=created.request.id,
        admin_user_id=999,
        now=now + timedelta(minutes=10),
    )
    retry_too_early = service.create_request(
        user_id=100,
        username="alice",
        first_name="Alice",
        now=now + timedelta(hours=23),
    )
    retry_later = service.create_request(
        user_id=100,
        username="alice",
        first_name="Alice",
        now=now + timedelta(hours=25),
    )

    assert rejected.status == AccessRequestDecisionStatus.REJECTED
    assert rejected.request is not None
    assert rejected.request.status == AccessRequestStatus.REJECTED
    assert retry_too_early.status == AccessRequestCreateStatus.COOLDOWN
    assert retry_too_early.retry_after_seconds is not None
    assert retry_too_early.retry_after_seconds > 0
    assert retry_later.status == AccessRequestCreateStatus.CREATED


def test_second_decision_does_not_reprocess_request(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    service = AccessService(db=db, request_cooldown_hours=24)
    now = datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc)
    created = service.create_request(user_id=100, username="alice", first_name="Alice", now=now)

    assert created.request is not None
    service.approve_request(
        request_id=created.request.id,
        admin_user_id=999,
        now=now + timedelta(minutes=1),
    )
    second = service.reject_request(
        request_id=created.request.id,
        admin_user_id=1000,
        now=now + timedelta(minutes=2),
    )
    snapshot = service.get_snapshot(100)

    assert second.status == AccessRequestDecisionStatus.ALREADY_RESOLVED
    assert second.request is not None
    assert second.request.status == AccessRequestStatus.APPROVED
    assert snapshot.state == UserAccessState.ACTIVE
