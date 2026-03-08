from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PreparedMedia:
    path: Path
    file_size_bytes: int
    compressed: bool


class MediaProcessingError(RuntimeError):
    def __init__(self, code: str, user_message: str) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message


class MediaService:
    def __init__(self, ffmpeg_path: str, max_size_bytes: int, ffmpeg_timeout_sec: int) -> None:
        self._ffmpeg_path = ffmpeg_path
        self._max_size_bytes = max_size_bytes
        self._ffmpeg_timeout_sec = ffmpeg_timeout_sec

    def prepare_for_telegram(self, source_path: Path, workspace_dir: Path) -> PreparedMedia:
        original_size = source_path.stat().st_size
        if original_size <= self._max_size_bytes:
            return PreparedMedia(path=source_path, file_size_bytes=original_size, compressed=False)

        if original_size > self._max_size_bytes * 4:
            raise MediaProcessingError("file_too_large", "The file is too large to compress safely.")

        output_path = workspace_dir / "compressed.mp4"
        command = [
            self._ffmpeg_path,
            "-y",
            "-i",
            str(source_path),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "30",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]

        try:
            subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=self._ffmpeg_timeout_sec,
            )
        except FileNotFoundError as exc:
            raise MediaProcessingError("ffmpeg_missing", "ffmpeg is not installed on the host.") from exc
        except subprocess.TimeoutExpired as exc:
            raise MediaProcessingError("ffmpeg_timeout", "Compression timed out.") from exc
        except subprocess.CalledProcessError as exc:
            raise MediaProcessingError("ffmpeg_failed", exc.stderr.strip() or "Compression failed.") from exc

        final_size = output_path.stat().st_size
        if final_size > self._max_size_bytes:
            raise MediaProcessingError("file_too_large", "Compressed file is still too large.")

        return PreparedMedia(path=output_path, file_size_bytes=final_size, compressed=True)
