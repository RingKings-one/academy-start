"""
Расписание: занятия на сегодня, ближайшие, отмена/перенос.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Optional, Sequence
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.db.models import Group, ScheduleInstance, User


def _tz() -> ZoneInfo:
    return ZoneInfo(settings.app_tz)


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def get_today_instances_for_coach(
    session: AsyncSession,
    coach: User,
) -> Sequence[ScheduleInstance]:
    """Занятия тренера на сегодня (в TZ школы)."""
    tz = _tz()
    now_local = _now_utc().astimezone(tz)
    day_start = datetime.combine(now_local.date(), time.min, tzinfo=tz).astimezone(timezone.utc)
    day_end = datetime.combine(now_local.date(), time.max, tzinfo=tz).astimezone(timezone.utc)

    result = await session.execute(
        select(ScheduleInstance)
        .join(Group, Group.id == ScheduleInstance.group_id)
        .where(
            Group.coach_user_id == coach.id,
            ScheduleInstance.starts_at >= day_start,
            ScheduleInstance.starts_at <= day_end,
            ScheduleInstance.status == "scheduled",
        )
        .options(selectinload(ScheduleInstance.group))
        .order_by(ScheduleInstance.starts_at)
    )
    return result.scalars().all()


async def get_next_instance_for_coach(
    session: AsyncSession,
    coach: User,
) -> Optional[ScheduleInstance]:
    """Ближайшее будущее занятие тренера (для empty state)."""
    result = await session.execute(
        select(ScheduleInstance)
        .join(Group, Group.id == ScheduleInstance.group_id)
        .where(
            Group.coach_user_id == coach.id,
            ScheduleInstance.starts_at > _now_utc(),
            ScheduleInstance.status == "scheduled",
        )
        .options(selectinload(ScheduleInstance.group))
        .order_by(ScheduleInstance.starts_at)
        .limit(1)
    )
    return result.scalar_one_or_none()


async def cancel_instance(
    session: AsyncSession,
    instance: ScheduleInstance,
    reason: str,
    cancelled_by: User,
) -> ScheduleInstance:
    instance.status = "cancelled"
    instance.cancel_reason = reason
    instance.created_by = cancelled_by.id  # кто изменил
    instance.updated_at = _now_utc()
    await session.flush()
    return instance
