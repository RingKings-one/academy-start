"""
Планирование исходящих сообщений (reminders).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Reminder


def _make_key(type_: str, target_user_id: int, entity_id: str | int) -> str:
    return f"{type_}:{target_user_id}:{entity_id}"


async def schedule_reminder(
    session: AsyncSession,
    *,
    target_user_id: int,
    type_: str,
    send_at: datetime,
    payload: dict[str, Any],
    entity_id: str | int,
) -> Optional[Reminder]:
    """
    Создать reminder с idempotency_key.
    Если такой ключ уже есть — ничего не делаем (ON CONFLICT DO NOTHING).
    """
    key = _make_key(type_, target_user_id, entity_id)

    stmt = (
        insert(Reminder)
        .values(
            target_user_id=target_user_id,
            type=type_,
            payload=payload,
            send_at=send_at,
            status="pending",
            idempotency_key=key,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
        .returning(Reminder)
    )
    result = await session.execute(stmt)
    reminder = result.scalar_one_or_none()
    await session.flush()
    return reminder


async def cancel_reminders_by_prefix(
    session: AsyncSession,
    target_user_id: int,
    type_prefix: str,
    entity_id: str | int,
) -> int:
    """
    Отменить pending-reminders (например followup, если уже нажали «Перенести»).
    """
    from sqlalchemy import update

    key_like = f"{type_prefix}:{target_user_id}:{entity_id}"
    result = await session.execute(
        update(Reminder)
        .where(
            Reminder.idempotency_key == key_like,
            Reminder.status == "pending",
        )
        .values(status="cancelled")
    )
    await session.flush()
    return result.rowcount or 0
