from __future__ import annotations

import logging
import uuid
from pathlib import Path

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, Message

from app import texts
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.services.downloader import DownloaderError, DownloaderService
from app.services.media import MediaProcessingError, MediaService
from app.services.rate_limit import RateLimitService
from app.utils.cleanup import cleanup_old_temp_files, remove_path
from app.utils.urls import UrlValidationError, extract_first_url, parse_media_url


logger = logging.getLogger(__name__)


def build_links_router(
    *,
    auth_service: AuthService,
    cache_service: CacheService,
    downloader_service: DownloaderService,
    media_service: MediaService,
    rate_limit_service: RateLimitService,
    temp_dir: Path,
    cleanup_max_age_hours: int,
) -> Router:
    router = Router(name="links")

    @router.message(F.text)
    async def link_handler(message: Message) -> None:
        user = message.from_user
        text = message.text or ""
        original_url: str | None = None
        normalized_url: str | None = None
        workspace_dir: Path | None = None

        if message.chat.type != "private":
            await message.answer(texts.PRIVATE_CHAT_ONLY_TEXT)
            return

        if not user or not auth_service.is_allowed(user.id):
            await message.answer(texts.NOT_ALLOWED_TEXT)
            return

        original_url = extract_first_url(text)
        if not original_url:
            await message.answer(texts.NO_URL_TEXT)
            return

        try:
            parsed_url = parse_media_url(original_url)
            normalized_url = parsed_url.normalized_url
        except UrlValidationError:
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=None,
                status="failed:validation",
                error_code="unsupported_url",
            )
            await message.answer(texts.UNSUPPORTED_URL_TEXT)
            return

        if not rate_limit_service.try_acquire_active_request(user.id):
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=normalized_url,
                status="failed:active_request",
                error_code="active_request",
            )
            await message.answer(texts.ACTIVE_REQUEST_TEXT)
            return

        limit = rate_limit_service.check_and_increment(user.id)
        if not limit.allowed:
            rate_limit_service.release_active_request(user.id)
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=normalized_url,
                status="failed:rate_limit",
                error_code="rate_limit",
            )
            await message.answer(texts.RATE_LIMIT_TEXT)
            return

        processing_message = await message.answer(texts.PROCESSING_TEXT)
        try:
            cached = cache_service.get_cached_media(normalized_url)
            if cached:
                try:
                    await message.answer_video(cached.telegram_file_id)
                    cache_service.log_request(
                        user_id=user.id,
                        username=user.username,
                        original_url=original_url,
                        normalized_url=normalized_url,
                        status="cache_hit",
                    )
                    await processing_message.delete()
                    return
                except TelegramBadRequest:
                    cache_service.delete(normalized_url)

            workspace_dir = temp_dir / uuid.uuid4().hex
            downloaded = downloader_service.download(parsed_url.original_url, parsed_url.platform, workspace_dir)
            prepared = media_service.prepare_for_telegram(downloaded.path, workspace_dir)
            caption = (downloaded.title or "").strip()[:1024] or None

            sent_message = await message.answer_video(
                FSInputFile(prepared.path),
                supports_streaming=True,
                caption=caption,
            )

            if not sent_message.video:
                raise RuntimeError("Telegram did not return a video object")

            cache_service.save_media(
                normalized_url=normalized_url,
                original_url=original_url,
                platform=parsed_url.platform,
                telegram_file_id=sent_message.video.file_id,
                file_size_bytes=prepared.file_size_bytes,
            )
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=normalized_url,
                status="success",
            )
            await processing_message.delete()
        except DownloaderError as exc:
            logger.warning("Download failure for %s: %s", original_url, exc.code)
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=normalized_url,
                status="failed:download",
                error_code=exc.code,
            )
            await processing_message.edit_text(
                texts.VIDEO_UNAVAILABLE_TEXT if exc.code == "video_unavailable" else texts.DOWNLOAD_FAILED_TEXT
            )
        except MediaProcessingError as exc:
            logger.warning("Media failure for %s: %s", original_url, exc.code)
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=normalized_url,
                status="failed:media",
                error_code=exc.code,
            )
            message_text = texts.TOO_LARGE_TEXT if exc.code == "file_too_large" else texts.INTERNAL_ERROR_TEXT
            await processing_message.edit_text(message_text)
        except Exception:
            logger.exception("Unhandled processing error for %s", original_url)
            cache_service.log_request(
                user_id=user.id,
                username=user.username,
                original_url=original_url,
                normalized_url=normalized_url,
                status="failed:internal",
                error_code="internal_error",
            )
            await processing_message.edit_text(texts.INTERNAL_ERROR_TEXT)
        finally:
            rate_limit_service.release_active_request(user.id)
            if workspace_dir:
                remove_path(workspace_dir)
            cleanup_old_temp_files(temp_dir, cleanup_max_age_hours)

    return router
