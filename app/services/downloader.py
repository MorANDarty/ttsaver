from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError as YtDlpDownloadError

from app.utils.urls import Platform


logger = logging.getLogger(__name__)


@dataclass
class DownloadedMedia:
    path: Path
    title: str | None
    platform: Platform


class DownloaderError(RuntimeError):
    def __init__(self, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


class DownloaderService:
    def __init__(self, timeout_sec: int) -> None:
        self._timeout_sec = timeout_sec

    def download(self, url: str, platform: Platform, target_dir: Path) -> DownloadedMedia:
        target_dir.mkdir(parents=True, exist_ok=True)
        output_template = str(target_dir / "media.%(ext)s")
        options = {
            "outtmpl": output_template,
            "format": "bestvideo*[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "socket_timeout": self._timeout_sec,
            "retries": 1,
        }

        try:
            with YoutubeDL(options) as ydl:
                info = ydl.extract_info(url, download=True)
                file_path = self._resolve_output_path(info, target_dir)
                return DownloadedMedia(path=file_path, title=info.get("title"), platform=platform)
        except YtDlpDownloadError as exc:
            message = str(exc).lower()
            logger.warning("yt-dlp failed for %s: %s", url, exc)
            if "private" in message or "login" in message or "not available" in message:
                raise DownloaderError("video_unavailable", "The video is unavailable or private.") from exc
            raise DownloaderError("download_failed", "Failed to download the video.") from exc
        except Exception as exc:
            logger.exception("Unexpected downloader error for %s", url)
            raise DownloaderError("download_failed", "Failed to download the video.") from exc

    def _resolve_output_path(self, info: dict, target_dir: Path) -> Path:
        requested_downloads = info.get("requested_downloads") or []
        for item in requested_downloads:
            filepath = item.get("filepath")
            if filepath:
                path = Path(filepath)
                if path.exists():
                    return path

        requested_filename = info.get("_filename")
        if requested_filename:
            path = Path(requested_filename)
            if path.exists():
                return path

        candidates = sorted(
            [path for path in target_dir.iterdir() if path.is_file()],
            key=lambda file_path: file_path.stat().st_mtime,
            reverse=True,
        )
        if not candidates:
            raise DownloaderError("download_failed", "Downloaded file not found.")
        return candidates[0]
