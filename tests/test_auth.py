from app.services.auth import AuthService


def test_auth_service_whitelist() -> None:
    service = AuthService(allowed_user_ids={1, 2}, admin_user_ids={2})
    assert service.is_allowed(1) is True
    assert service.is_allowed(99) is False
    assert service.is_admin(2) is True
    assert service.is_admin(1) is False
