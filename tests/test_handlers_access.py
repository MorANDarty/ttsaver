from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path

from aiogram import Bot, Dispatcher
from aiogram.types import Update

from app import texts
from app.handlers.access import build_access_router
from app.handlers.commands import build_commands_router
from app.services.access import AccessService
from app.services.auth import AuthService
from app.services.cache import CacheService
from app.storage.db import Database


class RecordingBot(Bot):
    def __init__(self) -> None:
        super().__init__(token="42:TEST")
        self.calls: list[object] = []

    async def __call__(self, method: object, request_timeout: int | None = None) -> object:
        self.calls.append(method)
        return True


def test_req_permission_sends_admin_buttons_and_user_confirmation(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    auth_service = AuthService(access_service=access_service, admin_user_ids={900}, legacy_allowed_user_ids=set())
    bot = RecordingBot()

    run_with_dispatcher(
        lambda: build_access_only_dispatcher(auth_service, access_service),
        bot,
        [
            build_message_update(
                text="/req_permission",
                user_id=100,
                username="alice",
                first_name="Alice",
            )
        ],
    )

    send_calls = [call for call in bot.calls if call.__class__.__name__ == "SendMessage"]
    assert len(send_calls) == 2

    admin_call = next(call for call in send_calls if call.chat_id == 900)
    user_call = next(call for call in send_calls if call.chat_id == 100)

    assert "Пользователь @alice хочет использовать вашего бота." in admin_call.text
    assert admin_call.reply_markup is not None
    buttons = admin_call.reply_markup.inline_keyboard[0]
    assert buttons[0].text == "Согласиться"
    assert buttons[0].callback_data == "access_request:approve:1"
    assert buttons[1].text == "Отказать"
    assert buttons[1].callback_data == "access_request:reject:1"
    assert user_call.text == texts.ACCESS_REQUEST_CREATED_TEXT


def test_req_permission_repeats_pending_text_without_duplicate_request(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    auth_service = AuthService(access_service=access_service, admin_user_ids={900}, legacy_allowed_user_ids=set())
    bot = RecordingBot()

    run_with_dispatcher(
        lambda: build_access_only_dispatcher(auth_service, access_service),
        bot,
        [
            build_message_update(text="/req_permission", user_id=100),
            build_message_update(text="/req_permission", user_id=100, message_id=2),
        ],
    )

    send_calls = [call for call in bot.calls if call.__class__.__name__ == "SendMessage" and call.chat_id == 100]
    assert send_calls[0].text == texts.ACCESS_REQUEST_CREATED_TEXT
    assert send_calls[1].text == texts.ACCESS_REQUEST_PENDING_TEXT

    snapshot = access_service.get_snapshot(100)
    assert snapshot.pending_request is not None
    assert snapshot.pending_request.id == 1


def test_approve_callback_updates_request_and_notifies_user(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    created = access_service.create_request(
        user_id=100,
        username="alice",
        first_name="Alice",
        now=datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
    )
    assert created.request is not None

    auth_service = AuthService(access_service=access_service, admin_user_ids={900}, legacy_allowed_user_ids=set())
    bot = RecordingBot()

    run_with_dispatcher(
        lambda: build_access_only_dispatcher(auth_service, access_service),
        bot,
        [
            build_callback_update(
                data=f"access_request:approve:{created.request.id}",
                from_user_id=900,
                message_chat_id=900,
            )
        ],
    )

    call_names = [call.__class__.__name__ for call in bot.calls]
    assert "EditMessageText" in call_names
    assert "AnswerCallbackQuery" in call_names
    send_calls = [call for call in bot.calls if call.__class__.__name__ == "SendMessage"]
    assert any(call.chat_id == 100 and call.text == texts.ACCESS_GRANTED_TEXT for call in send_calls)

    edit_call = next(call for call in bot.calls if call.__class__.__name__ == "EditMessageText")
    answer_call = next(call for call in bot.calls if call.__class__.__name__ == "AnswerCallbackQuery")
    assert "Статус: одобрено администратором 900" in edit_call.text
    assert answer_call.text == texts.ACCESS_APPROVED_BY_ADMIN_TEXT
    assert access_service.is_allowed(100) is True


def test_repeated_callback_returns_already_processed_text(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    created = access_service.create_request(
        user_id=100,
        username="alice",
        first_name="Alice",
        now=datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
    )
    assert created.request is not None
    access_service.approve_request(
        request_id=created.request.id,
        admin_user_id=900,
        now=datetime(2026, 3, 14, 10, 1, tzinfo=timezone.utc),
    )

    auth_service = AuthService(access_service=access_service, admin_user_ids={900}, legacy_allowed_user_ids=set())
    bot = RecordingBot()

    run_with_dispatcher(
        lambda: build_access_only_dispatcher(auth_service, access_service),
        bot,
        [
            build_callback_update(
                data=f"access_request:reject:{created.request.id}",
                from_user_id=900,
                message_chat_id=900,
            )
        ],
    )

    answer_call = next(call for call in bot.calls if call.__class__.__name__ == "AnswerCallbackQuery")
    assert answer_call.text == texts.ACCESS_REQUEST_ALREADY_PROCESSED_TEXT


def test_start_for_unapproved_user_shows_request_prompt(tmp_path: Path) -> None:
    db = Database(tmp_path / "app.db")
    db.init()
    access_service = AccessService(db=db, request_cooldown_hours=24)
    auth_service = AuthService(access_service=access_service, admin_user_ids={900}, legacy_allowed_user_ids=set())
    cache_service = CacheService(db=db, ttl_hours=24)
    bot = RecordingBot()

    run_with_dispatcher(
        lambda: build_commands_only_dispatcher(auth_service, cache_service),
        bot,
        [build_message_update(text="/start", user_id=100)],
    )

    send_call = next(call for call in bot.calls if call.__class__.__name__ == "SendMessage")
    assert send_call.chat_id == 100
    assert send_call.text == texts.ACCESS_REQUEST_PROMPT_TEXT


def build_message_update(
    *,
    text: str,
    user_id: int,
    username: str = "alice",
    first_name: str = "Alice",
    chat_id: int | None = None,
    message_id: int = 1,
) -> Update:
    return Update.model_validate(
        {
            "update_id": message_id,
            "message": {
                "message_id": message_id,
                "date": datetime(2026, 3, 14, 10, 0, tzinfo=timezone.utc),
                "chat": {"id": chat_id or user_id, "type": "private"},
                "from": {
                    "id": user_id,
                    "is_bot": False,
                    "first_name": first_name,
                    "username": username,
                },
                "text": text,
            },
        }
    )


def build_callback_update(*, data: str, from_user_id: int, message_chat_id: int, message_id: int = 50) -> Update:
    return Update.model_validate(
        {
            "update_id": message_id,
            "callback_query": {
                "id": f"cbq-{message_id}",
                "from": {
                    "id": from_user_id,
                    "is_bot": False,
                    "first_name": "Admin",
                    "username": "admin",
                },
                "chat_instance": "instance",
                "data": data,
                "message": {
                    "message_id": message_id,
                    "date": datetime(2026, 3, 14, 10, 2, tzinfo=timezone.utc),
                    "chat": {"id": message_chat_id, "type": "private"},
                    "from": {
                        "id": 42,
                        "is_bot": True,
                        "first_name": "TTSaverBot",
                        "username": "ttsaver_bot",
                    },
                    "text": "admin request",
                },
            },
        }
    )


def build_access_only_dispatcher(auth_service: AuthService, access_service: AccessService) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(
        build_access_router(
            auth_service=auth_service,
            access_service=access_service,
            admin_user_ids=(900,),
        )
    )
    return dispatcher


def build_commands_only_dispatcher(auth_service: AuthService, cache_service: CacheService) -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(build_commands_router(auth_service, cache_service))
    return dispatcher


def run_with_dispatcher(
    dispatcher_factory: object,
    bot: RecordingBot,
    updates: list[Update],
) -> None:
    loop = asyncio.new_event_loop()
    try:
        asyncio.set_event_loop(loop)
        dispatcher = dispatcher_factory()
        for update in updates:
            loop.run_until_complete(dispatcher.feed_update(bot, update))
    finally:
        asyncio.set_event_loop(None)
        loop.close()
