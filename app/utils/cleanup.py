from __future__ import annotations

import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def cleanup_old_temp_files(temp_dir: Path, max_age_hours: int) -> int:
    if not temp_dir.exists():
        return 0

    removed = 0
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    for item in temp_dir.iterdir():
        try:
            modified = datetime.fromtimestamp(item.stat().st_mtime, tz=timezone.utc)
        except FileNotFoundError:
            continue
        if modified < cutoff:
            remove_path(item)
            removed += 1
    return removed
