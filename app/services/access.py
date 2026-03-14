from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

from app.storage.db import Database
from app.storage.models import (
    AccessRequestCreateResult,
    AccessRequestCreateStatus,
    AccessRequestDecisionResult,
    AccessRequestDecisionStatus,
    AccessRequestRecord,
    AccessRequestStatus,
    UserAccessRecord,
    UserAccessSnapshot,
    UserAccessState,
    UserAccessStatus,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AccessService:
    def __init__(self, db: Database, request_cooldown_hours: int = 24) -> None:
        self._db = db
        self._request_cooldown = timedelta(hours=request_cooldown_hours)

    def is_allowed(self, user_id: int) -> bool:
        access = self.get_user_access(user_id)
        return access is not None and access.status == UserAccessStatus.ACTIVE

    def get_user_access(self, user_id: int) -> UserAccessRecord | None:
        with self._db.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM user_access
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
        return self._row_to_user_access(row) if row else None

    def get_access_request(self, request_id: int) -> AccessRequestRecord | None:
        with self._db.connection() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
        return self._row_to_access_request(row) if row else None

    def get_snapshot(self, user_id: int) -> UserAccessSnapshot:
        with self._db.connection() as conn:
            access_row = conn.execute(
                """
                SELECT *
                FROM user_access
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            pending_row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE user_id = ? AND status = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, AccessRequestStatus.PENDING.value),
            ).fetchone()
            latest_row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()

        access = self._row_to_user_access(access_row) if access_row else None
        pending_request = self._row_to_access_request(pending_row) if pending_row else None
        latest_request = self._row_to_access_request(latest_row) if latest_row else None

        if access and access.status == UserAccessStatus.ACTIVE:
            state = UserAccessState.ACTIVE
        elif pending_request:
            state = UserAccessState.PENDING
        elif latest_request and latest_request.status == AccessRequestStatus.REJECTED:
            state = UserAccessState.REJECTED
        else:
            state = UserAccessState.NONE

        return UserAccessSnapshot(
            state=state,
            access=access,
            pending_request=pending_request,
            latest_request=latest_request,
        )

    def create_request(
        self,
        *,
        user_id: int,
        username: str | None,
        first_name: str | None,
        now: datetime | None = None,
    ) -> AccessRequestCreateResult:
        now = now or utc_now()
        with self._db.connection() as conn:
            self._begin_immediate(conn)
            access_row = conn.execute(
                """
                SELECT *
                FROM user_access
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            access = self._row_to_user_access(access_row) if access_row else None
            if access and access.status == UserAccessStatus.ACTIVE:
                return AccessRequestCreateResult(
                    status=AccessRequestCreateStatus.ALREADY_ALLOWED,
                    request=None,
                )

            pending_row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE user_id = ? AND status = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id, AccessRequestStatus.PENDING.value),
            ).fetchone()
            if pending_row:
                return AccessRequestCreateResult(
                    status=AccessRequestCreateStatus.ALREADY_PENDING,
                    request=self._row_to_access_request(pending_row),
                )

            latest_row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (user_id,),
            ).fetchone()
            latest_request = self._row_to_access_request(latest_row) if latest_row else None
            if latest_request and latest_request.status == AccessRequestStatus.REJECTED:
                retry_at = latest_request.resolved_at or latest_request.requested_at
                retry_after = retry_at + self._request_cooldown - now
                if retry_after.total_seconds() > 0:
                    return AccessRequestCreateResult(
                        status=AccessRequestCreateStatus.COOLDOWN,
                        request=latest_request,
                        retry_after_seconds=int(retry_after.total_seconds()),
                    )

            cursor = conn.execute(
                """
                INSERT INTO access_request(
                    user_id,
                    username_snapshot,
                    first_name_snapshot,
                    status,
                    requested_at
                )
                VALUES(?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    first_name,
                    AccessRequestStatus.PENDING.value,
                    now.isoformat(),
                ),
            )
            row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE id = ?
                """,
                (cursor.lastrowid,),
            ).fetchone()
        return AccessRequestCreateResult(
            status=AccessRequestCreateStatus.CREATED,
            request=self._row_to_access_request(row) if row else None,
        )

    def approve_request(
        self,
        *,
        request_id: int,
        admin_user_id: int,
        now: datetime | None = None,
    ) -> AccessRequestDecisionResult:
        now = now or utc_now()
        with self._db.connection() as conn:
            self._begin_immediate(conn)
            request_row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
            if not request_row:
                return AccessRequestDecisionResult(
                    status=AccessRequestDecisionStatus.NOT_FOUND,
                    request=None,
                )

            request = self._row_to_access_request(request_row)
            if request.status != AccessRequestStatus.PENDING:
                return AccessRequestDecisionResult(
                    status=AccessRequestDecisionStatus.ALREADY_RESOLVED,
                    request=request,
                    user_access=self._get_user_access_in_conn(conn, request.user_id),
                )

            conn.execute(
                """
                UPDATE access_request
                SET status = ?, resolved_at = ?, resolution_admin_id = ?, resolution_reason = NULL
                WHERE id = ? AND status = ?
                """,
                (
                    AccessRequestStatus.APPROVED.value,
                    now.isoformat(),
                    admin_user_id,
                    request_id,
                    AccessRequestStatus.PENDING.value,
                ),
            )
            conn.execute(
                """
                INSERT INTO user_access(
                    user_id,
                    username_snapshot,
                    first_name_snapshot,
                    status,
                    granted_at,
                    granted_by_admin_id,
                    revoked_at,
                    revoked_by_admin_id,
                    created_at,
                    updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username_snapshot = excluded.username_snapshot,
                    first_name_snapshot = excluded.first_name_snapshot,
                    status = excluded.status,
                    granted_at = excluded.granted_at,
                    granted_by_admin_id = excluded.granted_by_admin_id,
                    revoked_at = NULL,
                    revoked_by_admin_id = NULL,
                    updated_at = excluded.updated_at
                """,
                (
                    request.user_id,
                    request.username_snapshot,
                    request.first_name_snapshot,
                    UserAccessStatus.ACTIVE.value,
                    now.isoformat(),
                    admin_user_id,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            updated_request = self._get_request_in_conn(conn, request_id)
            user_access = self._get_user_access_in_conn(conn, request.user_id)
        return AccessRequestDecisionResult(
            status=AccessRequestDecisionStatus.APPROVED,
            request=updated_request,
            user_access=user_access,
        )

    def reject_request(
        self,
        *,
        request_id: int,
        admin_user_id: int,
        now: datetime | None = None,
    ) -> AccessRequestDecisionResult:
        now = now or utc_now()
        with self._db.connection() as conn:
            self._begin_immediate(conn)
            request_row = conn.execute(
                """
                SELECT *
                FROM access_request
                WHERE id = ?
                """,
                (request_id,),
            ).fetchone()
            if not request_row:
                return AccessRequestDecisionResult(
                    status=AccessRequestDecisionStatus.NOT_FOUND,
                    request=None,
                )

            request = self._row_to_access_request(request_row)
            if request.status != AccessRequestStatus.PENDING:
                return AccessRequestDecisionResult(
                    status=AccessRequestDecisionStatus.ALREADY_RESOLVED,
                    request=request,
                    user_access=self._get_user_access_in_conn(conn, request.user_id),
                )

            conn.execute(
                """
                UPDATE access_request
                SET status = ?, resolved_at = ?, resolution_admin_id = ?
                WHERE id = ? AND status = ?
                """,
                (
                    AccessRequestStatus.REJECTED.value,
                    now.isoformat(),
                    admin_user_id,
                    request_id,
                    AccessRequestStatus.PENDING.value,
                ),
            )
            updated_request = self._get_request_in_conn(conn, request_id)
        return AccessRequestDecisionResult(
            status=AccessRequestDecisionStatus.REJECTED,
            request=updated_request,
            user_access=None,
        )

    def _begin_immediate(self, conn: sqlite3.Connection) -> None:
        conn.execute("BEGIN IMMEDIATE")

    def _get_request_in_conn(self, conn: sqlite3.Connection, request_id: int) -> AccessRequestRecord | None:
        row = conn.execute(
            """
            SELECT *
            FROM access_request
            WHERE id = ?
            """,
            (request_id,),
        ).fetchone()
        return self._row_to_access_request(row) if row else None

    def _get_user_access_in_conn(self, conn: sqlite3.Connection, user_id: int) -> UserAccessRecord | None:
        row = conn.execute(
            """
            SELECT *
            FROM user_access
            WHERE user_id = ?
            """,
            (user_id,),
        ).fetchone()
        return self._row_to_user_access(row) if row else None

    def _row_to_user_access(self, row: sqlite3.Row) -> UserAccessRecord:
        return UserAccessRecord(
            user_id=row["user_id"],
            username_snapshot=row["username_snapshot"],
            first_name_snapshot=row["first_name_snapshot"],
            status=UserAccessStatus(row["status"]),
            granted_at=self._parse_datetime(row["granted_at"]),
            granted_by_admin_id=row["granted_by_admin_id"],
            revoked_at=self._parse_datetime(row["revoked_at"]),
            revoked_by_admin_id=row["revoked_by_admin_id"],
            created_at=self._parse_datetime(row["created_at"]),
            updated_at=self._parse_datetime(row["updated_at"]),
        )

    def _row_to_access_request(self, row: sqlite3.Row) -> AccessRequestRecord:
        return AccessRequestRecord(
            id=row["id"],
            user_id=row["user_id"],
            username_snapshot=row["username_snapshot"],
            first_name_snapshot=row["first_name_snapshot"],
            status=AccessRequestStatus(row["status"]),
            requested_at=self._parse_datetime(row["requested_at"]),
            resolved_at=self._parse_datetime(row["resolved_at"]),
            resolution_admin_id=row["resolution_admin_id"],
            resolution_reason=row["resolution_reason"],
        )

    def _parse_datetime(self, value: str | None) -> datetime | None:
        if value is None:
            return None
        return datetime.fromisoformat(value)
