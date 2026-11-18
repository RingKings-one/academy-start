"""Единая точка для текстовых шагов FSM (чтобы не конфликтовали роутеры)."""

from __future__ import annotations

from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.bot.keyboards.common import main_menu_kb, medcert_kb, confirm_broadcast_kb
from app.db.models import User, Child, ScheduleInstance, Attendance
from app.services import fsm
from app.services.child_service import create_child
from app.services.schedule_service import cancel_instance
from app.services.reminder_service import schedule_reminder

router = Router(name="text_fsm")
TZ = ZoneInfo(settings.app_tz)


def _fmt(dt: datetime) -> str:
    local = dt.astimezone(TZ)
    wd = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"][local.weekday()]
    return f"{local.strftime('%d.%m')}, {wd}, {local.strftime('%H:%M')}"


@router.message(F.text)
async def any_text(message: Message, session: AsyncSession, user: User):
    state = await fsm.get_state(session, user)
    step = state.get("step")
    if not step:
        return

    text = (message.text or "").strip()

    # --- parent: имя ребёнка при записи ---
    if step == "enter_child":
        parts = text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            await message.answer("Формат: <code>Имя Возраст</code>, например <code>Артём 8</code>")
            return
        age = int(parts[-1])
        name = " ".join(parts[:-1])
        if age < 3 or age > 18:
            await message.answer("Возраст должен быть от 3 до 18.")
            return
        await fsm.update_state(session, user, step="medcert", child_name=name, child_age=age)
        await message.answer("Есть ли медсправка?", reply_markup=medcert_kb())
        return

    if step == "add_child_name":
        parts = text.split()
        if len(parts) < 2 or not parts[-1].isdigit():
            await message.answer("Формат: <code>Имя Возраст</code>")
            return
        age = int(parts[-1])
        name = " ".join(parts[:-1])
        birth = date(date.today().year - age, 1, 1)
        child = await create_child(session, user, name=name, birth_date=birth)
        await fsm.clear_state(session, user)
        await message.answer(
            f"Ребёнок <b>{child.name}</b> добавлен и выбран активным.",
            reply_markup=main_menu_kb(user.role),
        )
        return

    if step == "help_admin":
        await fsm.clear_state(session, user)
        await message.answer(
            "Сообщение принято. Администратор ответит в ближайшее время.\n"
            f"Ваш текст: <i>{text[:500]}</i>",
            reply_markup=main_menu_kb(user.role),
        )
        return

    # --- coach broadcast text ---
    if step == "bc_text":
        if len(text) < 2:
            await message.answer("Слишком короткий текст.")
            return
        group_id = int(state["broadcast_group_id"])
        result = await session.execute(
            select(User.id)
            .join(Child, Child.parent_user_id == User.id)
            .join(Child.enrollments)
            .where(
                Child.enrollments.any(),
            )
        )
        # проще через Enrollment
        from app.db.models import Enrollment
        result = await session.execute(
            select(User.id)
            .join(Child, Child.parent_user_id == User.id)
            .join(Enrollment, Enrollment.child_id == Child.id)
            .where(Enrollment.group_id == group_id, Enrollment.ended_at.is_(None))
            .distinct()
        )
        parent_ids = [r[0] for r in result.all()]
        await fsm.set_state(
            session,
            user,
            {
                "step": "bc_confirm",
                "broadcast_group_id": group_id,
                "broadcast_text": text,
                "broadcast_parent_ids": parent_ids,
            },
        )
        await message.answer(
            f"Отправить это <b>{len(parent_ids)}</b> родителям?\n\n<i>{text[:400]}</i>",
            reply_markup=confirm_broadcast_kb(),
        )
        return

    if step == "cancel_reason":
        reason = text
        instance_id = int(state["cancel_instance_id"])
        inst = await session.get(ScheduleInstance, instance_id)
        if not inst:
            await message.answer("Занятие не найдено.")
            await fsm.clear_state(session, user)
            return
        await cancel_instance(session, inst, reason, user)
        att_res = await session.execute(
            select(Attendance).where(
                Attendance.instance_id == instance_id,
                Attendance.status == "going",
            )
        )
        now = datetime.now(timezone.utc)
        for att in att_res.scalars().all():
            child = await session.get(Child, att.child_id)
            if not child:
                continue
            await schedule_reminder(
                session,
                target_user_id=child.parent_user_id,
                type_="cancel_notice",
                send_at=now,
                payload={
                    "text": (
                        f"⚠️ Занятие {_fmt(inst.starts_at)} отменено.\n"
                        f"Причина: {reason}\n"
                        "Мы предложим другое время — следите за ботом."
                    )
                },
                entity_id=f"{instance_id}:{child.parent_user_id}",
            )
        await fsm.clear_state(session, user)
        await message.answer(
            f"Занятие #{instance_id} отменено. Уведомления поставлены в очередь.",
            reply_markup=main_menu_kb(user.role),
        )
        return
