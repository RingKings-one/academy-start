from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User as TgUser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User


class UserMiddleware(BaseMiddleware):
    """
    Создаёт / обновляет пользователя и определяет роль.
    Приоритет: admin > coach > parent
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        tg_user: TgUser | None = data.get("event_from_user")
        if not tg_user:
            return await handler(event, data)

        session: AsyncSession = data["session"]

        result = await session.execute(
            select(User).where(User.telegram_id == tg_user.id)
        )
        user = result.scalar_one_or_none()

        # Определяем роль
        if tg_user.id in settings.admin_ids:
            role = "admin"
        elif tg_user.id in settings.coach_ids:
            role = "coach"
        else:
            role = "parent"

        if user is None:
            user = User(
                telegram_id=tg_user.id,
                role=role,
                first_name=tg_user.first_name,
                username=tg_user.username,
            )
            session.add(user)
            await session.flush()
        else:
            # обновляем базовые поля и роль (если поменяли в конфиге)
            user.first_name = tg_user.first_name
            user.username = tg_user.username
            if user.role != role and (role in ("admin", "coach") or user.role == "parent"):
                user.role = role

        data["user"] = user
        return await handler(event, data)
