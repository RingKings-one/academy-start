import asyncio
import logging
from datetime import datetime, timedelta, timezone

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import async_session_maker
from app.db.models import Reminder, User

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("worker")

POLL_INTERVAL = 15
BATCH_SIZE = 30
SENDING_TIMEOUT_MINUTES = 5


async def process_stuck_sending(session: AsyncSession) -> None:
    threshold = datetime.now(timezone.utc) - timedelta(minutes=SENDING_TIMEOUT_MINUTES)
    result = await session.execute(
        update(Reminder)
        .where(
            Reminder.status == "sending",
            Reminder.locked_at < threshold,
        )
        .values(status="failed", last_error="stuck in sending after restart")
    )
    if result.rowcount:
        logger.warning("Marked %s stuck reminders as failed", result.rowcount)


async def fetch_pending(session: AsyncSession) -> list[Reminder]:
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(Reminder)
        .where(
            Reminder.status == "pending",
            Reminder.send_at <= now,
        )
        .order_by(Reminder.send_at)
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    return list(result.scalars().all())


def build_keyboard(payload: dict) -> InlineKeyboardMarkup | None:
    buttons = payload.get("buttons") or []
    if not buttons:
        return None
    row = [
        InlineKeyboardButton(text=b.get("label") or b.get("code"), callback_data=b["code"])
        for b in buttons
        if b.get("code")
    ]
    if not row:
        return None
    return InlineKeyboardMarkup(inline_keyboard=[row])


async def send_reminder(bot: Bot, session: AsyncSession, reminder: Reminder) -> None:
    reminder.status = "sending"
    reminder.locked_at = datetime.now(timezone.utc)
    reminder.attempts += 1
    await session.flush()

    user = None
    try:
        user_result = await session.execute(
            select(User).where(User.id == reminder.target_user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise ValueError(f"User id={reminder.target_user_id} not found")

        if user.bot_blocked:
            reminder.status = "failed"
            reminder.last_error = "bot_blocked"
            return

        payload = reminder.payload or {}
        text = payload.get("text") or f"Напоминание ({reminder.type})"
        kb = build_keyboard(payload)

        await bot.send_message(
            chat_id=user.telegram_id,
            text=text,
            reply_markup=kb,
        )

        reminder.status = "sent"
        reminder.sent_at = datetime.now(timezone.utc)
        reminder.last_error = None
        logger.info(
            "SENT reminder id=%s type=%s to user=%s",
            reminder.id,
            reminder.type,
            user.telegram_id,
        )

    except TelegramForbiddenError:
        if user:
            user.bot_blocked = True
        reminder.status = "failed"
        reminder.last_error = "403 Forbidden (bot blocked)"
        logger.warning("User %s blocked the bot", reminder.target_user_id)

    except TelegramRetryAfter as e:
        reminder.status = "pending"
        reminder.last_error = f"RetryAfter {e.retry_after}s"
        logger.warning("Rate limited, retry after %ss", e.retry_after)
        await asyncio.sleep(min(e.retry_after, 5))

    except Exception as e:
        logger.exception("Failed to send reminder %s", reminder.id)
        reminder.status = "failed"
        reminder.last_error = str(e)[:500]


async def worker_loop() -> None:
    if not settings.bot_token or settings.bot_token.startswith("123456") or settings.bot_token == "REPLACE_WITH_REAL_TOKEN":
        logger.error("BOT_TOKEN не задан. Worker не запущен.")
        return

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )

    logger.info("Worker started (interval=%ss)", POLL_INTERVAL)
    try:
        while True:
            try:
                async with async_session_maker() as session:
                    await process_stuck_sending(session)
                    pending = await fetch_pending(session)
                    for rem in pending:
                        await send_reminder(bot, session, rem)
                        await asyncio.sleep(0.05)
                    await session.commit()
            except Exception:
                logger.exception("Worker iteration failed")
            await asyncio.sleep(POLL_INTERVAL)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(worker_loop())
