from __future__ import annotations

from app.services.access import AccessService
from app.storage.models import UserAccessSnapshot, UserAccessState


class AuthService:
    def __init__(
        self,
        access_service: AccessService,
        admin_user_ids: set[int],
        legacy_allowed_user_ids: set[int] | None = None,
    ) -> None:
        self._access_service = access_service
        self._admin_user_ids = admin_user_ids
        self._legacy_allowed_user_ids = legacy_allowed_user_ids or set()

    def is_allowed(self, user_id: int) -> bool:
        return user_id in self._legacy_allowed_user_ids or self._access_service.is_allowed(user_id)

    def is_admin(self, user_id: int) -> bool:
        return user_id in self._admin_user_ids

    def get_access_snapshot(self, user_id: int) -> UserAccessSnapshot:
        if user_id in self._legacy_allowed_user_ids:
            snapshot = self._access_service.get_snapshot(user_id)
            return UserAccessSnapshot(
                state=UserAccessState.ACTIVE,
                access=snapshot.access,
                pending_request=snapshot.pending_request,
                latest_request=snapshot.latest_request,
            )
        return self._access_service.get_snapshot(user_id)
