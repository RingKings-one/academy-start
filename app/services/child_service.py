"""
Дети родителя.
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Child, User


async def list_children(session: AsyncSession, parent: User) -> Sequence[Child]:
    result = await session.execute(
        select(Child)
        .where(
            Child.parent_user_id == parent.id,
            Child.deleted_at.is_(None),
        )
        .order_by(Child.id)
    )
    return result.scalars().all()


async def get_child(session: AsyncSession, child_id: int, parent: User) -> Optional[Child]:
    result = await session.execute(
        select(Child).where(
            Child.id == child_id,
            Child.parent_user_id == parent.id,
            Child.deleted_at.is_(None),
        )
    )
    return result.scalar_one_or_none()


async def create_child(
    session: AsyncSession,
    parent: User,
    name: str,
    birth_date: date,
    notes: Optional[str] = None,
) -> Child:
    child = Child(
        parent_user_id=parent.id,
        name=name,
        birth_date=birth_date,
        notes=notes,
    )
    session.add(child)
    await session.flush()

    # если активного ребёнка нет — ставим этого
    if parent.active_child_id is None:
        parent.active_child_id = child.id
        await session.flush()

    return child


async def set_active_child(session: AsyncSession, parent: User, child_id: int) -> bool:
    child = await get_child(session, child_id, parent)
    if not child:
        return False
    parent.active_child_id = child.id
    await session.flush()
    return True
