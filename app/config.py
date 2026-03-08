from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    bot_token: str = Field(alias="BOT_TOKEN")
    allowed_user_ids_raw: str = Field(default="", alias="ALLOWED_USER_IDS")
    admin_user_ids_raw: str = Field(default="", alias="ADMIN_USER_IDS")
    temp_dir: Path = Field(default=Path("./data/temp"), alias="TEMP_DIR")
    db_path: Path = Field(default=Path("./data/app.db"), alias="DB_PATH")
    max_video_size_mb: int = Field(default=50, alias="MAX_VIDEO_SIZE_MB")
    cache_ttl_hours: int = Field(default=72, alias="CACHE_TTL_HOURS")
    requests_per_user_per_day: int = Field(default=20, alias="REQUESTS_PER_USER_PER_DAY")
    cleanup_max_age_hours: int = Field(default=12, alias="CLEANUP_MAX_AGE_HOURS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    ffmpeg_path: str = Field(default="ffmpeg", alias="FFMPEG_PATH")
    download_timeout_sec: int = Field(default=180, alias="DOWNLOAD_TIMEOUT_SEC")
    ffmpeg_timeout_sec: int = Field(default=180, alias="FFMPEG_TIMEOUT_SEC")
    health_host: str = Field(default="0.0.0.0", alias="HEALTH_HOST")
    port: int = Field(default=10000, alias="PORT")

    @field_validator("allowed_user_ids_raw", "admin_user_ids_raw", mode="before")
    @classmethod
    def validate_user_ids_raw(cls, value: object) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, set)):
            return ",".join(str(int(part)) for part in value)
        raise TypeError("User IDs must be provided as comma-separated string or list")

    @property
    def allowed_user_ids(self) -> tuple[int, ...]:
        return self._parse_user_ids(self.allowed_user_ids_raw)

    @property
    def admin_user_ids(self) -> tuple[int, ...]:
        return self._parse_user_ids(self.admin_user_ids_raw)

    def _parse_user_ids(self, value: str) -> tuple[int, ...]:
        cleaned = [part.strip() for part in value.split(",") if part.strip()]
        return tuple(int(part) for part in cleaned)

    @property
    def max_video_size_bytes(self) -> int:
        return self.max_video_size_mb * 1024 * 1024

    def ensure_directories(self) -> None:
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
