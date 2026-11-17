"""API записи на пробное с сайта."""

from __future__ import annotations

import re
import time
from collections import defaultdict, deque
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_session
from app.db.models import Direction
from app.services.application_service import create_application

router = APIRouter(prefix="/api", tags=["trial"])

_RATE: dict[str, deque] = defaultdict(deque)
_RATE_LIMIT = 3
_RATE_WINDOW = 3600


def _check_rate(ip: str) -> None:
    now = time.time()
    q = _RATE[ip]
    while q and now - q[0] > _RATE_WINDOW:
        q.popleft()
    if len(q) >= _RATE_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Слишком много заявок с вашего адреса. Попробуйте позже или напишите в Telegram.",
        )
    q.append(now)


def normalize_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    if digits.startswith("7") and len(digits) == 11:
        return f"+{digits}"
    if len(digits) == 10:
        return f"+7{digits}"
    raise ValueError("Укажите телефон в формате +7XXXXXXXXXX")


class TrialRequest(BaseModel):
    parent_name: str = Field(..., min_length=2, max_length=100)
    phone: str = Field(..., min_length=10, max_length=20)
    child_name: str = Field(..., min_length=2, max_length=100)
    child_age: int = Field(..., ge=3, le=18)
    direction_slug: str = Field(..., min_length=2, max_length=50)
    medcert: str = Field(..., pattern="^(has|needs)$")
    pd_consent: bool

    @field_validator("pd_consent")
    @classmethod
    def must_consent(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Нужно согласие на обработку персональных данных")
        return v


class TrialResponse(BaseModel):
    ok: bool
    application_id: int
    deep_link: str
    message: str


@router.post("/trial", response_model=TrialResponse)
async def submit_trial(
    body: TrialRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    ip = request.client.host if request.client else "unknown"
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        ip = fwd.split(",")[0].strip()
    _check_rate(ip)

    try:
        phone = normalize_phone(body.phone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    result = await session.execute(
        select(Direction).where(
            Direction.slug == body.direction_slug,
            Direction.is_active.is_(True),
        )
    )
    direction = result.scalar_one_or_none()
    if not direction:
        result = await session.execute(
            select(Direction).where(Direction.is_active.is_(True)).order_by(Direction.id).limit(1)
        )
        direction = result.scalar_one_or_none()
        if not direction:
            raise HTTPException(
                status_code=400,
                detail="Направления ещё не настроены. Запустите seed на сервере.",
            )

    today = date.today()
    birth = date(today.year - body.child_age, 1, 1)

    app = await create_application(
        session,
        source="site",
        child_name=body.child_name.strip(),
        phone=phone,
        direction_id=direction.id,
        pd_consent=True,
        child_birth_date=birth,
        medcert=body.medcert,
    )

    token = app.deep_link_token or ""
    username = (settings.bot_username or "").lstrip("@")
    if token and username:
        deep_link = f"https://t.me/{username}?start={token}"
    elif username:
        deep_link = f"https://t.me/{username}"
    else:
        deep_link = "https://t.me/"

    return TrialResponse(
        ok=True,
        application_id=app.id,
        deep_link=deep_link,
        message="Заявка принята! Откройте бота, чтобы подтвердить запись.",
    )


@router.get("/directions")
async def list_directions(session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(Direction)
        .where(Direction.is_active.is_(True))
        .order_by(Direction.sort_order, Direction.id)
    )
    rows = result.scalars().all()
    return [
        {
            "id": d.id,
            "slug": d.slug,
            "name": d.name,
            "description": d.description,
            "age_min": d.age_min,
            "age_max": d.age_max,
        }
        for d in rows
    ]
