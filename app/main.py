from __future__ import annotations

import asyncio
import logging

from app.bot import build_bot, build_dispatcher, build_services
from app.config import get_settings
from app.storage.db import Database
from app.utils.cleanup import cleanup_old_temp_files
from app.utils.logging import setup_logging


async def main() -> None:
    settings = get_settings()
    settings.ensure_directories()
    setup_logging(settings.log_level)

    logger = logging.getLogger(__name__)
    logger.info(
        "Starting bot with temp_dir=%s db_path=%s allowed_users=%d admins=%d",
        settings.temp_dir,
        settings.db_path,
        len(settings.allowed_user_ids),
        len(settings.admin_user_ids),
    )

    db = Database(settings.db_path)
    db.init()

    removed = cleanup_old_temp_files(settings.temp_dir, settings.cleanup_max_age_hours)
    logger.info("Removed %d stale temp entries during startup cleanup", removed)

    services = build_services(settings, db)
    services.cache.cleanup_expired()

    bot = build_bot(settings)
    dispatcher = build_dispatcher(settings, services)

    try:
        await dispatcher.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
