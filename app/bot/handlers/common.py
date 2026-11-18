from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User, Reminder

router = Router(name="common")


@router.message(Command("debug"))
async def cmd_debug(message: Message, session: AsyncSession, user: User):
    if user.role != "admin" and user.telegram_id not in settings.admin_ids:
        await message.answer("Нет доступа.")
        return

    # последние reminders
    result = await session.execute(
        select(Reminder)
        .where(Reminder.target_user_id == user.id)
        .order_by(Reminder.id.desc())
        .limit(5)
    )
    reminders = result.scalars().all()

    lines = [
        f"<b>Debug info</b>",
        f"telegram_id: <code>{user.telegram_id}</code>",
        f"role: <code>{user.role}</code>",
        f"active_child_id: <code>{user.active_child_id}</code>",
        f"bot_blocked: <code>{user.bot_blocked}</code>",
        f"state: <code>{user.state}</code>",
        "",
        "<b>Last 5 reminders:</b>",
    ]
    if not reminders:
        lines.append("— пусто —")
    else:
        for r in reminders:
            lines.append(
                f"• #{r.id} {r.type} | {r.status} | send_at={r.send_at}"
            )

    await message.answer("\n".join(lines))
