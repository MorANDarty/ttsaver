from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app import texts
from app.handlers.access_utils import build_access_denied_text
from app.services.auth import AuthService
from app.services.cache import CacheService


def build_commands_router(auth_service: AuthService, cache_service: CacheService) -> Router:
    router = Router(name="commands")

    @router.message(Command("start"))
    async def start_handler(message: Message) -> None:
        if not message.from_user or not auth_service.is_allowed(message.from_user.id):
            await message.answer(
                texts.REQUEST_ACCESS_PROMPT_TEXT
                if not message.from_user
                else build_access_denied_text(auth_service, message.from_user.id)
            )
            return
        await message.answer(texts.START_TEXT)

    @router.message(Command("help"))
    async def help_handler(message: Message) -> None:
        if not message.from_user or not auth_service.is_allowed(message.from_user.id):
            await message.answer(
                texts.REQUEST_ACCESS_PROMPT_TEXT
                if not message.from_user
                else build_access_denied_text(auth_service, message.from_user.id)
            )
            return
        await message.answer(texts.HELP_TEXT)

    @router.message(Command("stats"))
    async def stats_handler(message: Message) -> None:
        if not message.from_user or not auth_service.is_admin(message.from_user.id):
            await message.answer(texts.NOT_ALLOWED_TEXT)
            return

        stats = cache_service.get_stats_snapshot()
        failures = "\n".join(stats.recent_failures) if stats.recent_failures else "No recent failures."
        text = (
            f"Total requests: {stats.total_requests}\n"
            f"Success: {stats.success_count}\n"
            f"Failures: {stats.failure_count}\n"
            f"Cache hits: {stats.cache_hit_count}\n\n"
            f"Recent failures:\n{failures}"
        )
        await message.answer(text)

    @router.message(F.text.startswith("/"))
    async def unknown_command_handler(message: Message) -> None:
        if not message.from_user or not auth_service.is_allowed(message.from_user.id):
            await message.answer(
                texts.REQUEST_ACCESS_PROMPT_TEXT
                if not message.from_user
                else build_access_denied_text(auth_service, message.from_user.id)
            )
            return
        await message.answer(texts.HELP_TEXT)

    return router
