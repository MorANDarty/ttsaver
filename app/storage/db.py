from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS media_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    normalized_url TEXT NOT NULL UNIQUE,
    source_platform TEXT NOT NULL,
    telegram_file_id TEXT NOT NULL,
    file_size_bytes INTEGER,
    original_url TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS request_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username TEXT,
    original_url TEXT,
    normalized_url TEXT,
    status TEXT NOT NULL,
    error_code TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS user_rate_limit (
    user_id INTEGER NOT NULL,
    day_bucket TEXT NOT NULL,
    request_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (user_id, day_bucket)
);

CREATE TABLE IF NOT EXISTS user_access (
    user_id INTEGER PRIMARY KEY,
    username_snapshot TEXT,
    first_name_snapshot TEXT,
    status TEXT NOT NULL,
    granted_at TEXT,
    granted_by_admin_id INTEGER,
    revoked_at TEXT,
    revoked_by_admin_id INTEGER,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS access_request (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    username_snapshot TEXT,
    first_name_snapshot TEXT,
    status TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    resolved_at TEXT,
    resolution_admin_id INTEGER,
    resolution_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_request_log_created_at ON request_log(created_at);
CREATE INDEX IF NOT EXISTS idx_request_log_status ON request_log(status);
CREATE INDEX IF NOT EXISTS idx_media_cache_expires_at ON media_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_user_access_status ON user_access(status);
CREATE INDEX IF NOT EXISTS idx_access_request_user_id ON access_request(user_id);
CREATE INDEX IF NOT EXISTS idx_access_request_status_requested_at ON access_request(status, requested_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_access_request_one_pending_per_user
ON access_request(user_id)
WHERE status = 'pending';
"""


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path

    def init(self) -> None:
        with self.connection() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
            conn.commit()
        finally:
            conn.close()
