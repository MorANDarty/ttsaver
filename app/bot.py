from __future__ import annotations

from dataclasses import dataclass

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from app.config import Settings
from app.handlers.commands import build_commands_router
from app.handlers.links import build_links_router
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.downloader import DownloaderService
from app.services.media import MediaService
from app.services.rate_limit import RateLimitService
from app.storage.db import Database


@dataclass
class AppServices:
    auth: AuthService
    cache: CacheService
    downloader: DownloaderService
    media: MediaService
    rate_limit: RateLimitService


def build_services(settings: Settings, db: Database) -> AppServices:
    auth_service = AuthService(set(settings.allowed_user_ids), set(settings.admin_user_ids))
    cache_service = CacheService(db=db, ttl_hours=settings.cache_ttl_hours)
    downloader_service = DownloaderService(timeout_sec=settings.download_timeout_sec)
    media_service = MediaService(
        ffmpeg_path=settings.ffmpeg_path,
        max_size_bytes=settings.max_video_size_bytes,
        ffmpeg_timeout_sec=settings.ffmpeg_timeout_sec,
    )
    rate_limit_service = RateLimitService(db=db, daily_limit=settings.requests_per_user_per_day)
    return AppServices(
        auth=auth_service,
        cache=cache_service,
        downloader=downloader_service,
        media=media_service,
        rate_limit=rate_limit_service,
    )


def build_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(),
    )


def build_dispatcher(settings: Settings, services: AppServices) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(build_commands_router(services.auth, services.cache))
    dispatcher.include_router(
        build_links_router(
            auth_service=services.auth,
            cache_service=services.cache,
            downloader_service=services.downloader,
            media_service=services.media,
            rate_limit_service=services.rate_limit,
            temp_dir=settings.temp_dir,
            cleanup_max_age_hours=settings.cleanup_max_age_hours,
        )
    )
    return dispatcher
