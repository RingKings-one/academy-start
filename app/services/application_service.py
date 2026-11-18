"""
Заявки на пробное занятие.
"""

from __future__ import annotations

import secrets
from datetime import date, datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Application, Child, User


def _generate_token() -> str:
    return secrets.token_urlsafe(24)


async def create_application(
    session: AsyncSession,
    *,
    source: str,  # site / bot
    child_name: str,
    phone: str,
    direction_id: int,
    pd_consent: bool,
    parent_user: Optional[User] = None,
    child_id: Optional[int] = None,
    child_birth_date: Optional[date] = None,
    group_id: Optional[int] = None,
    trial_instance_id: Optional[int] = None,
    medcert: Optional[str] = None,  # has / needs
) -> Application:
    """
    Создать заявку. Если source=site — генерируем deep_link_token.
    """
    app = Application(
        parent_user_id=parent_user.id if parent_user else None,
        child_id=child_id,
        child_name=child_name,
        child_birth_date=child_birth_date,
        phone=phone,
        direction_id=direction_id,
        group_id=group_id,
        trial_instance_id=trial_instance_id,
        status="new",
        source=source,
        medcert=medcert,
        pd_consent=pd_consent,
        deep_link_token=_generate_token() if source == "site" else None,
    )
    session.add(app)
    await session.flush()
    return app


async def bind_application_by_token(
    session: AsyncSession,
    token: str,
    parent_user: User,
) -> Optional[Application]:
    """
    Deep-link: привязать заявку с сайта к пользователю бота.
    Токен одноразовый — после использования обнуляем.
    """
    result = await session.execute(
        select(Application).where(
            Application.deep_link_token == token,
            Application.status == "new",
        )
    )
    app = result.scalar_one_or_none()
    if not app:
        return None

    app.parent_user_id = parent_user.id
    app.deep_link_token = None  # one-time
    # если ребёнка ещё нет — создадим позже в сценарии
    await session.flush()
    return app


async def get_application(session: AsyncSession, application_id: int) -> Optional[Application]:
    result = await session.execute(
        select(Application).where(Application.id == application_id)
    )
    return result.scalar_one_or_none()


async def update_status(
    session: AsyncSession,
    application: Application,
    status: str,
) -> Application:
    application.status = status
    application.updated_at = datetime.now(timezone.utc)
    await session.flush()
    return application
