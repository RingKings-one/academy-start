"""
Посещаемость: «Буду/Не буду» от родителя и отметки тренера.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Attendance, ScheduleInstance, User

# Дедлайн: за 3 часа до начала занятия
DEADLINE_HOURS = 3


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def parent_set_attendance(
    session: AsyncSession,
    *,
    child_id: int,
    instance_id: int,
    status: str,  # going / not_going
    parent: User,
) -> tuple[bool, str]:
    """
    Родитель жмёт «Буду» / «Не буду».
    Возвращает (ok, message).
    Проверка дедлайна — на бэке.
    """
    if status not in ("going", "not_going"):
        return False, "Некорректный статус"

    result = await session.execute(
        select(ScheduleInstance).where(ScheduleInstance.id == instance_id)
    )
    instance = result.scalar_one_or_none()
    if not instance:
        return False, "Занятие не найдено"

    if instance.status != "scheduled":
        return False, "Занятие отменено или перенесено"

    deadline = instance.starts_at - timedelta(hours=DEADLINE_HOURS)
    if _now() > deadline:
        return False, "Время вышло. Свяжитесь с администратором."

    # upsert
    stmt = (
        insert(Attendance)
        .values(
            child_id=child_id,
            instance_id=instance_id,
            status=status,
            source="parent",
            set_by_user_id=parent.id,
            set_at=_now(),
        )
        .on_conflict_do_update(
            constraint="uq_attendance_child_instance",
            set_={
                "status": status,
                "source": "parent",
                "set_by_user_id": parent.id,
                "set_at": _now(),
                "updated_at": _now(),
            },
        )
    )
    await session.execute(stmt)
    await session.flush()
    return True, "ok"


async def coach_set_attendance(
    session: AsyncSession,
    *,
    child_id: int,
    instance_id: int,
    status: str,  # attended / no_show
    coach: User,
) -> tuple[bool, str]:
    """Тренер отмечает факт присутствия."""
    if status not in ("attended", "no_show"):
        return False, "Некорректный статус"

    stmt = (
        insert(Attendance)
        .values(
            child_id=child_id,
            instance_id=instance_id,
            status=status,
            source="coach",
            set_by_user_id=coach.id,
            set_at=_now(),
        )
        .on_conflict_do_update(
            constraint="uq_attendance_child_instance",
            set_={
                "status": status,
                "source": "coach",
                "set_by_user_id": coach.id,
                "set_at": _now(),
                "updated_at": _now(),
            },
        )
    )
    await session.execute(stmt)
    await session.flush()
    return True, "ok"
