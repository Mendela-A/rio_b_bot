import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, MenuButtonCommands

from app import texts
from app.config import load_config
from app.database.connection import create_pool, close_pool
from app.handlers import start, booking, cart, services, info, common, admin
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

    await bot.set_my_commands([
        BotCommand(command="start", description="Запустити бота"),
        BotCommand(command="menu",  description="Головне меню"),
    ])
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(booking.router)
    dp.include_router(cart.router)
    dp.include_router(services.router)
    dp.include_router(info.router)
    dp.include_router(common.router)

    WEBHOOK_PATH = "/webhook"

    if config.webhook_url:
        from aiohttp import web
        from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

        async def on_startup(bot: Bot) -> None:
            await bot.set_webhook(
                url=f"{config.webhook_url}{WEBHOOK_PATH}",
                secret_token=config.webhook_secret,
            )
            logger.info("Webhook set: %s%s", config.webhook_url, WEBHOOK_PATH)

        async def on_shutdown(bot: Bot) -> None:
            await bot.delete_webhook()
            await close_pool(pool)
            await bot.session.close()
            logger.info("Bot stopped (webhook)")

        dp.startup.register(on_startup)
        dp.shutdown.register(on_shutdown)

        aio_app = web.Application()
        SimpleRequestHandler(
            dispatcher=dp,
            bot=bot,
            secret_token=config.webhook_secret,
        ).register(aio_app, path=WEBHOOK_PATH)
        setup_application(aio_app, dp, bot=bot)

        runner = web.AppRunner(aio_app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8081)
        await site.start()
        logger.info("Bot started (webhook mode, port 8081)")
        await asyncio.Event().wait()
    else:
        logger.info("Bot started (polling mode)")
        try:
            await dp.start_polling(bot)
        finally:
            await close_pool(pool)
            await bot.session.close()
            logger.info("Bot stopped")


if __name__ == "__main__":
    asyncio.run(main())
