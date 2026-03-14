from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from app.utils.urls import Platform


class UserAccessStatus(str, Enum):
    ACTIVE = "active"
    REVOKED = "revoked"


class AccessRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class AccessRequestCreateStatus(str, Enum):
    CREATED = "created"
    ALREADY_ALLOWED = "already_allowed"
    ALREADY_PENDING = "already_pending"
    COOLDOWN = "cooldown"


class AccessRequestDecisionStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    ALREADY_RESOLVED = "already_resolved"
    NOT_FOUND = "not_found"


class UserAccessState(str, Enum):
    ACTIVE = "active"
    PENDING = "pending"
    REJECTED = "rejected"
    NONE = "none"


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


@dataclass
class UserAccessRecord:
    user_id: int
    username_snapshot: str | None
    first_name_snapshot: str | None
    status: UserAccessStatus
    granted_at: datetime | None
    granted_by_admin_id: int | None
    revoked_at: datetime | None
    revoked_by_admin_id: int | None
    created_at: datetime
    updated_at: datetime


@dataclass
class AccessRequestRecord:
    id: int
    user_id: int
    username_snapshot: str | None
    first_name_snapshot: str | None
    status: AccessRequestStatus
    requested_at: datetime
    resolved_at: datetime | None
    resolution_admin_id: int | None
    resolution_reason: str | None


@dataclass
class AccessRequestCreateResult:
    status: AccessRequestCreateStatus
    request: AccessRequestRecord | None
    retry_after_seconds: int | None = None


@dataclass
class AccessRequestDecisionResult:
    status: AccessRequestDecisionStatus
    request: AccessRequestRecord | None
    user_access: UserAccessRecord | None = None


@dataclass
class UserAccessSnapshot:
    state: UserAccessState
    access: UserAccessRecord | None
    pending_request: AccessRequestRecord | None
    latest_request: AccessRequestRecord | None
