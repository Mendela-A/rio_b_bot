import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.config import load_config
from app.database.connection import create_pool, close_pool
from app.handlers import start, booking, cart, services, info, common

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    config = load_config()

    pool = await create_pool(config)

    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp["pool"] = pool

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
