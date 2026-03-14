from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app import texts
from app.services.access import AccessService
from app.services.auth import AuthService
from app.storage.models import (
    AccessRequestCreateStatus,
    AccessRequestDecisionStatus,
    AccessRequestRecord,
    AccessRequestStatus,
)


logger = logging.getLogger(__name__)

CALLBACK_PREFIX = "access_request"


def build_access_router(
    *,
    auth_service: AuthService,
    access_service: AccessService,
    admin_user_ids: tuple[int, ...],
) -> Router:
    router = Router(name="access")

    @router.message(Command("req_permission"))
    async def request_permission_handler(message: Message) -> None:
        user = message.from_user
        if not user:
            await message.answer(texts.REQUEST_ACCESS_PROMPT_TEXT)
            return
        if not admin_user_ids:
            logger.error("Access request flow is unavailable because no admins are configured")
            await message.answer(texts.ACCESS_REQUESTS_UNAVAILABLE_TEXT)
            return

        result = access_service.create_request(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
        )
        if result.status == AccessRequestCreateStatus.ALREADY_ALLOWED:
            await message.answer(texts.ACCESS_ALREADY_GRANTED_TEXT)
            return
        if result.status == AccessRequestCreateStatus.ALREADY_PENDING:
            await message.answer(texts.ACCESS_REQUEST_PENDING_TEXT)
            return
        if result.status == AccessRequestCreateStatus.COOLDOWN:
            await message.answer(texts.build_access_request_cooldown_text(result.retry_after_seconds))
            return
        if not result.request:
            await message.answer(texts.INTERNAL_ERROR_TEXT)
            return

        await _notify_admins(message, result.request, admin_user_ids)
        await message.answer(texts.ACCESS_REQUEST_CREATED_TEXT)

    @router.callback_query(F.data.startswith(f"{CALLBACK_PREFIX}:"))
    async def access_request_callback_handler(callback: CallbackQuery) -> None:
        user = callback.from_user
        if not user or not auth_service.is_admin(user.id):
            await callback.answer(texts.ADMIN_ONLY_ACTION_TEXT, show_alert=True)
            return

        action, request_id = _parse_callback_data(callback.data or "")
        if action is None or request_id is None:
            await callback.answer(texts.STALE_ACCESS_REQUEST_TEXT, show_alert=True)
            return

        if action == "approve":
            result = access_service.approve_request(request_id=request_id, admin_user_id=user.id)
        else:
            result = access_service.reject_request(request_id=request_id, admin_user_id=user.id)

        if result.status == AccessRequestDecisionStatus.NOT_FOUND:
            await callback.answer(texts.STALE_ACCESS_REQUEST_TEXT, show_alert=True)
            return

        if not result.request:
            await callback.answer(texts.STALE_ACCESS_REQUEST_TEXT, show_alert=True)
            return

        await _refresh_admin_message(callback, result.request)

        if result.status == AccessRequestDecisionStatus.ALREADY_RESOLVED:
            await callback.answer(texts.ACCESS_REQUEST_ALREADY_PROCESSED_TEXT, show_alert=False)
            return

        if result.request.status == AccessRequestStatus.APPROVED:
            await _notify_user(callback, result.request.user_id, texts.ACCESS_GRANTED_TEXT)
            await callback.answer(texts.ACCESS_APPROVED_BY_ADMIN_TEXT)
            return

        await _notify_user(callback, result.request.user_id, texts.ACCESS_REJECTED_TEXT)
        await callback.answer(texts.ACCESS_REJECTED_BY_ADMIN_TEXT)

    return router


def _build_admin_keyboard(request_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Согласиться",
                    callback_data=f"{CALLBACK_PREFIX}:approve:{request_id}",
                ),
                InlineKeyboardButton(
                    text="Отказать",
                    callback_data=f"{CALLBACK_PREFIX}:reject:{request_id}",
                ),
            ]
        ]
    )


async def _notify_admins(message: Message, request: AccessRequestRecord, admin_user_ids: tuple[int, ...]) -> None:
    text = _build_admin_request_text(request)
    keyboard = _build_admin_keyboard(request.id)
    delivered = 0
    for admin_user_id in admin_user_ids:
        try:
            await message.bot.send_message(admin_user_id, text, reply_markup=keyboard)
            delivered += 1
        except TelegramForbiddenError:
            logger.warning("Admin %s has blocked the bot; access request %s was not delivered", admin_user_id, request.id)
        except TelegramBadRequest:
            logger.warning("Failed to deliver access request %s to admin %s", request.id, admin_user_id)

    if delivered == 0:
        logger.error("Access request %s was created but not delivered to any admin", request.id)


async def _refresh_admin_message(callback: CallbackQuery, request: AccessRequestRecord) -> None:
    if not callback.message:
        return
    try:
        await callback.message.edit_text(_build_admin_request_text(request), reply_markup=None)
    except TelegramBadRequest:
        logger.debug("Admin message for access request %s could not be updated", request.id)


async def _notify_user(callback: CallbackQuery, user_id: int, text: str) -> None:
    try:
        await callback.bot.send_message(user_id, text)
    except TelegramForbiddenError:
        logger.warning("User %s could not be notified about access decision", user_id)
    except TelegramBadRequest:
        logger.warning("Telegram rejected access decision notification for user %s", user_id)


def _build_admin_request_text(request: AccessRequestRecord) -> str:
    username = f"@{request.username_snapshot}" if request.username_snapshot else "без username"
    first_name = request.first_name_snapshot or "без имени"
    lines = [
        f"Пользователь {username} хочет использовать вашего бота.",
        f"user_id: {request.user_id}",
        f"Имя: {first_name}",
        f"Заявка: #{request.id}",
    ]
    if request.status == AccessRequestStatus.APPROVED:
        admin_id = request.resolution_admin_id or "unknown"
        lines.append(f"Статус: одобрено администратором {admin_id}")
    elif request.status == AccessRequestStatus.REJECTED:
        admin_id = request.resolution_admin_id or "unknown"
        lines.append(f"Статус: отклонено администратором {admin_id}")
    else:
        lines.append("Статус: ожидает решения")
    return "\n".join(lines)


def _parse_callback_data(data: str) -> tuple[str | None, int | None]:
    parts = data.split(":")
    if len(parts) != 3 or parts[0] != CALLBACK_PREFIX:
        return None, None
    try:
        return parts[1], int(parts[2])
    except ValueError:
        return None, None
