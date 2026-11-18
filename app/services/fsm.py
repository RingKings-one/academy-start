"""
FSM-состояние пользователя.

Сейчас храним в users.state (JSONB).
Позже можно заменить реализацию на Redis без правок хендлеров.
"""

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User

DEFAULT_TTL_MINUTES = 15


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_state(session: AsyncSession, user: User) -> dict[str, Any]:
    """Вернуть текущий state. Если протух — очистить и вернуть {}."""
    state = user.state or {}
    expires_at = state.get("expires_at")

    if expires_at:
        try:
            exp = datetime.fromisoformat(expires_at)
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            if _now() > exp:
                await clear_state(session, user)
                return {}
        except (ValueError, TypeError):
            await clear_state(session, user)
            return {}

    return state


async def set_state(
    session: AsyncSession,
    user: User,
    data: dict[str, Any],
    ttl_minutes: int = DEFAULT_TTL_MINUTES,
) -> None:
    """
    Установить/обновить state.
    data обычно: {"step": "enter_child_name", "direction_id": 1, ...}
    """
    payload = dict(data)
    payload["expires_at"] = (_now() + timedelta(minutes=ttl_minutes)).isoformat()
    user.state = payload
    await session.flush()


async def update_state(
    session: AsyncSession,
    user: User,
    **kwargs: Any,
) -> dict[str, Any]:
    """Частично обновить state (сохраняя expires_at и остальные поля)."""
    state = await get_state(session, user)
    state.update(kwargs)
    # продлеваем TTL при каждом обновлении
    state["expires_at"] = (_now() + timedelta(minutes=DEFAULT_TTL_MINUTES)).isoformat()
    user.state = state
    await session.flush()
    return state


async def clear_state(session: AsyncSession, user: User) -> None:
    """Сбросить state в пустой объект."""
    user.state = {}
    await session.flush()


async def get_step(session: AsyncSession, user: User) -> str | None:
    """Короткий хелпер: текущий step или None."""
    state = await get_state(session, user)
    return state.get("step")
