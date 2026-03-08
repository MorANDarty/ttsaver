from __future__ import annotations


class AuthService:
    def __init__(self, allowed_user_ids: set[int], admin_user_ids: set[int]) -> None:
        self._allowed_user_ids = allowed_user_ids
        self._admin_user_ids = admin_user_ids

    def is_allowed(self, user_id: int) -> bool:
        return user_id in self._allowed_user_ids

    def is_admin(self, user_id: int) -> bool:
        return user_id in self._admin_user_ids
