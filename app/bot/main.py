import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.core.config import settings
from app.bot.handlers import setup_routers
from app.bot.middlewares.db import DbSessionMiddleware
from app.bot.middlewares.user import UserMiddleware
from app.bot.middlewares.callback_log import CallbackLogMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


async def main() -> None:
    if not settings.bot_token or settings.bot_token.startswith("123456"):
        logger.error("BOT_TOKEN не задан. Укажи реальный токен в .env")
        return

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.update.middleware(DbSessionMiddleware())
    dp.update.middleware(UserMiddleware())
    dp.callback_query.middleware(CallbackLogMiddleware())

    # Routers
    setup_routers(dp)

    logger.info("Bot starting (polling)...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
