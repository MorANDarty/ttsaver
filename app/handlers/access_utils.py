from __future__ import annotations

from app import texts
from app.services.auth import AuthService
from app.storage.models import UserAccessState


def build_access_denied_text(auth_service: AuthService, user_id: int) -> str:
    snapshot = auth_service.get_access_snapshot(user_id)
    if snapshot.state == UserAccessState.PENDING:
        return texts.ACCESS_REQUEST_PENDING_TEXT
    if snapshot.state == UserAccessState.REJECTED:
        return texts.ACCESS_REQUEST_REJECTED_TEXT
    return texts.ACCESS_REQUEST_PROMPT_TEXT
