import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app import texts
from app.config import load_config
from app.database.connection import create_pool, close_pool
from app.handlers import start, booking, cart, services, info, common
from app.middleware.throttling import ThrottlingMiddleware

if os.getenv("LOG_FORMAT", "text") == "json":
    from pythonjsonlogger import jsonlogger
    _handler = logging.StreamHandler()
    _handler.setFormatter(
        jsonlogger.JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    logging.root.addHandler(_handler)
    logging.root.setLevel(logging.INFO)
else:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    pool = await create_pool(config)
    await texts.init(pool)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["pool"] = pool

    dp.message.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())

    dp.include_router(start.router)
    dp.include_router(booking.router)
    dp.include_router(cart.router)
    dp.include_router(services.router)
    dp.include_router(info.router)
    dp.include_router(common.router)

    logger.info("Bot started")
    try:
        await dp.start_polling(bot)
    finally:
        await close_pool(pool)
        await bot.session.close()
        logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
