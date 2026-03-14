from datetime import datetime, timezone
from pathlib import Path

from app.services.access import AccessService
from app.services.auth import AuthService
from app.storage.db import Database


def test_auth_service_supports_db_access_and_admins(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    approved = access_service.create_request(
        user_id=1,
        username="alice",
        first_name="Alice",
        now=datetime(2026, 3, 8, 10, 0, tzinfo=timezone.utc),
    )
    assert approved.request is not None
    access_service.approve_request(
        request_id=approved.request.id,
        admin_user_id=10,
        now=datetime(2026, 3, 8, 10, 5, tzinfo=timezone.utc),
    )

    service = AuthService(
        access_service=access_service,
        admin_user_ids={2},
        legacy_allowed_user_ids=set(),
    )

    assert service.is_allowed(1) is True
    assert service.is_allowed(99) is False
    assert service.is_admin(2) is True
    assert service.is_admin(1) is False


def test_auth_service_supports_legacy_allowed_ids(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    service = AuthService(
        access_service=access_service,
        admin_user_ids=set(),
        legacy_allowed_user_ids={42},
    )

    assert service.is_allowed(42) is True
