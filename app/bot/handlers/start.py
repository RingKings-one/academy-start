from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards.common import main_menu_kb
from app.db.models import User
from app.services.application_service import bind_application_by_token
from app.services import fsm

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    user: User,
):
    token = (command.args or "").strip()

    if token:
        app = await bind_application_by_token(session, token, user)
        if app:
            await fsm.clear_state(session, user)
            # подтягиваем телефон из заявки
            if app.phone and not user.phone:
                user.phone = app.phone
            role_title = {"admin": "Админ", "coach": "Тренер", "parent": "Родитель"}.get(user.role, "")
            await message.answer(
                f"✅ Заявка с сайта найдена!\n"
                f"Ребёнок: <b>{app.child_name}</b>\n"
                f"Телефон: {app.phone}\n"
                f"Статус: {app.status}\n\n"
                f"Администратор подтвердит время занятия. "
                f"Вы также можете записаться ещё раз или посмотреть меню.",
                reply_markup=main_menu_kb(user.role),
            )
            return
        await message.answer(
            "Заявка не найдена или ссылка устарела.\n"
            "Можно записаться заново через меню.",
            reply_markup=main_menu_kb(user.role),
        )
        return

    role_title = {
        "admin": "Администратор",
        "coach": "Тренер",
        "parent": "Родитель",
    }.get(user.role, "Пользователь")

    await message.answer(
        f"Привет, {message.from_user.first_name or 'друг'}!\n"
        f"Роль: <b>{role_title}</b>\n\n"
        "Академия «Старт» — запись на пробное, напоминания и посещаемость в одном боте.",
        reply_markup=main_menu_kb(user.role),
    )
