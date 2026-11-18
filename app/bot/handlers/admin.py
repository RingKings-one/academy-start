from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import main_menu_kb
from app.db.models import User, Application, Payment, Enrollment
from app.core.config import settings

router = Router(name="admin")


def _is_admin(user: User) -> bool:
    return user.role == "admin" or user.telegram_id in settings.admin_ids


@router.callback_query(F.data == "admin:digest")
async def admin_digest(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    if not _is_admin(user):
        await callback.message.answer("Нет доступа.")
        return

    async def count_status(status: str) -> int:
        r = await session.execute(
            select(func.count()).select_from(Application).where(Application.status == status)
        )
        return int(r.scalar() or 0)

    new_c = await count_status("new")
    conf = await count_status("confirmed")
    attended = await count_status("attended")
    converted = await count_status("converted")
    no_show = await count_status("no_show")

    overdue = await session.execute(
        select(func.count()).select_from(Payment).where(Payment.status == "overdue")
    )
    overdue_n = int(overdue.scalar() or 0)

    await callback.message.answer(
        "<b>Дайджест воронки</b>\n"
        f"• Новые заявки: <b>{new_c}</b>\n"
        f"• Подтверждены: <b>{conf}</b>\n"
        f"• Дошли (attended): <b>{attended}</b>\n"
        f"• Купили (converted): <b>{converted}</b>\n"
        f"• No-show: <b>{no_show}</b>\n"
        f"• Должников (overdue): <b>{overdue_n}</b>\n\n"
        "Подробности — в мини-админке (в следующей итерации).",
        reply_markup=main_menu_kb(user.role),
    )


@router.callback_query(F.data == "admin:problems")
async def admin_problems(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    if not _is_admin(user):
        return
    result = await session.execute(
        select(Application)
        .where(Application.status.in_(["new", "no_show"]))
        .order_by(Application.created_at.desc())
        .limit(15)
    )
    apps = list(result.scalars().all())
    if not apps:
        await callback.message.answer("Проблемных заявок нет 👍", reply_markup=main_menu_kb(user.role))
        return
    lines = ["<b>Проблемные / новые заявки:</b>\n"]
    for a in apps:
        lines.append(
            f"• #{a.id} {a.child_name} | {a.status} | {a.phone} | {a.source}"
        )
    await callback.message.answer("\n".join(lines), reply_markup=main_menu_kb(user.role))


@router.callback_query(F.data == "admin:as_parent")
async def admin_as_parent(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    await callback.message.answer(
        "Меню родителя (для проверки сценария):",
        reply_markup=main_menu_kb("parent"),
    )
