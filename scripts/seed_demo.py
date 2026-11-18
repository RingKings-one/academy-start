"""
Полный seed для демо-презентации.
Запуск: python -m scripts.seed_demo
или:    python scripts/seed_demo.py
"""
from __future__ import annotations

import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# чтобы импорты app.* работали при запуске из корня
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import delete, select, text

from app.core.config import settings
from app.db.session import async_session_maker, engine
from app.db.base import Base
from app.db.models import (
    User,
    CoachProfile,
    Child,
    Direction,
    Group,
    ScheduleInstance,
    Application,
    Enrollment,
    Attendance,
    Reminder,
    Payment,
)

TZ = ZoneInfo(settings.app_tz)


def utc_at_local(d: date, hour: int, minute: int = 0) -> datetime:
    local = datetime(d.year, d.month, d.day, hour, minute, tzinfo=TZ)
    return local.astimezone(timezone.utc)


async def reset_and_create_tables() -> None:
    async with engine.begin() as conn:
        # мягкий вариант: не дропаем всё если уже есть миграции
        await conn.run_sync(Base.metadata.create_all)


async def clear_demo_data(session) -> None:
    for table in (
        Payment,
        Reminder,
        Attendance,
        Enrollment,
        Application,
        ScheduleInstance,
        Group,
        CoachProfile,
        Child,
        Direction,
    ):
        await session.execute(delete(table))
    # users оставляем реальных (с telegram_id с сервера), чистим только демо-user с отрицательными id-логикой
    # удаляем users без telegram из seed — мы создадим seed-тренеров с фиктивными telegram_id
    await session.execute(
        delete(User).where(User.telegram_id < 0)
    )
    await session.commit()


async def seed() -> None:
    await reset_and_create_tables()
    async with async_session_maker() as session:
        await clear_demo_data(session)

        # --- directions ---
        dirs = [
            Direction(slug="sambo", name="Самбо / Единоборства", description="Дисциплина и техника", age_min=5, age_max=16, sort_order=1),
            Direction(slug="football", name="Футбол", description="Командная игра", age_min=6, age_max=14, sort_order=2),
            Direction(slug="ofp", name="ОФП", description="Общая физподготовка", age_min=4, age_max=15, sort_order=3),
        ]
        session.add_all(dirs)
        await session.flush()

        # --- coaches (фиктивные telegram_id < 0, чтобы не пересекаться с реальными) ---
        coach1 = User(telegram_id=-1001, role="coach", first_name="Алексей", username="coach_alex")
        coach2 = User(telegram_id=-1002, role="coach", first_name="Игорь", username="coach_igor")
        session.add_all([coach1, coach2])
        await session.flush()

        session.add_all([
            CoachProfile(user_id=coach1.id, display_name="Алексей Морозов", achievements="МС по самбо, 9 лет с детьми", bio="Спокойный подход к новичкам", sort_order=1),
            CoachProfile(user_id=coach2.id, display_name="Игорь Соколов", achievements="Футбол, акцент на технику", bio="Игра и дисциплина", sort_order=2),
        ])

        # --- groups ---
        g_sambo = Group(direction_id=dirs[0].id, coach_user_id=coach1.id, name="Самбо 7–9, новички", age_min=7, age_max=9, capacity=12, branch="Зал 1", is_active=True)
        g_foot = Group(direction_id=dirs[1].id, coach_user_id=coach2.id, name="Футбол 8–11", age_min=8, age_max=11, capacity=14, branch="Поле", is_active=True)
        g_ofp = Group(direction_id=dirs[2].id, coach_user_id=coach1.id, name="ОФП 5–8", age_min=5, age_max=8, capacity=10, branch="Зал 2", is_active=True)
        session.add_all([g_sambo, g_foot, g_ofp])
        await session.flush()

        # --- schedule: сегодня, завтра, + несколько дней ---
        today = datetime.now(TZ).date()
        instances = []
        plan = [
            (g_sambo, today, 18, 0, 60),
            (g_foot, today, 19, 0, 60),
            (g_ofp, today + timedelta(days=1), 17, 0, 45),
            (g_sambo, today + timedelta(days=1), 18, 0, 60),
            (g_foot, today + timedelta(days=2), 19, 0, 60),
            (g_sambo, today + timedelta(days=3), 18, 0, 60),
        ]
        for group, d, h, m, dur in plan:
            start = utc_at_local(d, h, m)
            end = start + timedelta(minutes=dur)
            inst = ScheduleInstance(group_id=group.id, starts_at=start, ends_at=end, status="scheduled", created_by=coach1.id)
            session.add(inst)
            instances.append(inst)
        await session.flush()

        # --- demo parent (фиктивный) + children ---
        parent = User(telegram_id=-2001, role="parent", first_name="Анна", phone="+79001234567")
        session.add(parent)
        await session.flush()

        children = [
            Child(parent_user_id=parent.id, name="Артём", birth_date=date(today.year - 8, 3, 12)),
            Child(parent_user_id=parent.id, name="Мия", birth_date=date(today.year - 6, 7, 1)),
        ]
        session.add_all(children)
        await session.flush()
        parent.active_child_id = children[0].id

        # enrollments
        session.add_all([
            Enrollment(child_id=children[0].id, group_id=g_sambo.id, status="active"),
            Enrollment(child_id=children[1].id, group_id=g_ofp.id, status="trial"),
        ])

        # attendance history
        session.add(
            Attendance(
                child_id=children[0].id,
                instance_id=instances[0].id,
                status="going",
                source="parent",
                set_by_user_id=parent.id,
            )
        )

        # applications at different funnel stages
        session.add_all([
            Application(
                parent_user_id=parent.id,
                child_id=children[1].id,
                child_name="Мия",
                child_birth_date=children[1].birth_date,
                phone="+79001234567",
                direction_id=dirs[2].id,
                group_id=g_ofp.id,
                trial_instance_id=instances[2].id,
                status="confirmed",
                source="bot",
                medcert="has",
                pd_consent=True,
            ),
            Application(
                child_name="Кирилл",
                child_birth_date=date(today.year - 9, 1, 15),
                phone="+79007654321",
                direction_id=dirs[0].id,
                status="new",
                source="site",
                medcert="needs",
                pd_consent=True,
                deep_link_token="demo_token_kirill_001",
            ),
            Application(
                child_name="София",
                phone="+79001112233",
                direction_id=dirs[1].id,
                status="converted",
                source="bot",
                medcert="has",
                pd_consent=True,
            ),
        ])

        # sample payment overdue
        enr = (await session.execute(select(Enrollment).where(Enrollment.child_id == children[0].id))).scalar_one()
        session.add(
            Payment(
                enrollment_id=enr.id,
                amount=4500,
                period_from=today.replace(day=1),
                period_to=today,
                status="overdue",
            )
        )

        
        # Привязка реальных coach/admin из .env к группам (для живого демо)
        from app.core.config import settings as _s
        real_coach_ids = _s.coach_ids or _s.admin_ids
        if real_coach_ids:
            real_tid = real_coach_ids[0]
            existing = (await session.execute(select(User).where(User.telegram_id == real_tid))).scalar_one_or_none()
            if existing:
                g_sambo.coach_user_id = existing.id
                g_ofp.coach_user_id = existing.id
                g_foot.coach_user_id = existing.id
                print(f"  groups bound to real user telegram_id={real_tid}")

        await session.commit()
        print("OK: seed demo data loaded")
        print(f"  directions: 3, groups: 3, instances: {len(instances)}")
        print(f"  coaches telegram_id: -1001, -1002 (подставь реальные в .env COACH_TELEGRAM_IDS)")
        print(f"  today instances for coach1 (sambo 18:00, ofp linked)")


if __name__ == "__main__":
    asyncio.run(seed())
