"""Минимальный seed направлений — чтобы форма на сайте работала."""
import asyncio

from sqlalchemy import select

from app.db.session import async_session_maker
from app.db.models import Direction


DIRECTIONS = [
    {
        "slug": "sambo",
        "name": "Самбо / Единоборства",
        "description": "Дисциплина, характер и техника. Группы для новичков и продолжающих.",
        "age_min": 5,
        "age_max": 16,
        "sort_order": 1,
    },
    {
        "slug": "football",
        "name": "Футбол",
        "description": "Командная игра, техника и физика. Тренировки 2–3 раза в неделю.",
        "age_min": 6,
        "age_max": 14,
        "sort_order": 2,
    },
    {
        "slug": "ofp",
        "name": "ОФП",
        "description": "Общая физическая подготовка: сила, выносливость, координация.",
        "age_min": 4,
        "age_max": 15,
        "sort_order": 3,
    },
]


async def main() -> None:
    async with async_session_maker() as session:
        for item in DIRECTIONS:
            exists = await session.execute(
                select(Direction).where(Direction.slug == item["slug"])
            )
            if exists.scalar_one_or_none():
                print(f"skip {item['slug']}")
                continue
            session.add(Direction(**item, is_active=True))
            print(f"add {item['slug']}")
        await session.commit()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
