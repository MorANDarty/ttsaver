from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

from app.bot import build_bot, build_dispatcher, build_services
from app.config import get_settings
from app.services.health_server import run_health_server
from app.storage.db import Database
from app.utils.cleanup import cleanup_old_temp_files
from app.utils.logging import setup_logging


async def main() -> None:
    settings = get_settings()
    settings.ensure_directories()
    setup_logging(settings.log_level)

    logger = logging.getLogger(__name__)
    logger.info(
        "Starting bot with temp_dir=%s db_path=%s legacy_allowed_users=%d admins=%d health=%s:%d",
        settings.temp_dir,
        settings.db_path,
        len(settings.allowed_user_ids),
        len(settings.admin_user_ids),
        settings.health_host,
        settings.port,
    )

    db = Database(settings.db_path)
    db.init()

    removed = cleanup_old_temp_files(settings.temp_dir, settings.cleanup_max_age_hours)
    logger.info("Removed %d stale temp entries during startup cleanup", removed)

    services = build_services(settings, db)
    services.cache.cleanup_expired()

    bot = build_bot(settings)
    dispatcher = build_dispatcher(settings, services)
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, request_stop)

    try:
        polling_task = asyncio.create_task(dispatcher.start_polling(bot), name="telegram-polling")
        health_task = asyncio.create_task(
            run_health_server(settings.health_host, settings.port, stop_event),
            name="health-server",
        )

        done, pending = await asyncio.wait(
            {polling_task, health_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in done:
            exc = task.exception()
            if exc:
                raise exc

        for task in pending:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
    finally:
        stop_event.set()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
