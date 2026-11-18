from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.bot.keyboards.common import (
    main_menu_kb,
    coach_instances_kb,
    groups_for_coach_kb,
    confirm_broadcast_kb,
    coach_att_kb,
)
from app.db.models import User, Group, ScheduleInstance, Enrollment, Child, Attendance
from app.services import fsm
from app.services.schedule_service import get_today_instances_for_coach, get_next_instance_for_coach, cancel_instance
from app.services.attendance_service import coach_set_attendance
from app.services.reminder_service import schedule_reminder

router = Router(name="coach")
TZ = ZoneInfo(settings.app_tz)


def _fmt(dt: datetime) -> str:
    local = dt.astimezone(TZ)
    wd = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"][local.weekday()]
    return f"{local.strftime('%d.%m')}, {wd}, {local.strftime('%H:%M')}"


def _is_coach(user: User) -> bool:
    return user.role in ("coach", "admin")


@router.callback_query(F.data == "coach:today")
async def coach_today(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    if not _is_coach(user):
        await callback.message.answer("Доступно только тренеру.")
        return

    instances = list(await get_today_instances_for_coach(session, user))
    if not instances:
        nxt = await get_next_instance_for_coach(session, user)
        if nxt:
            gname = nxt.group.name if nxt.group else "Группа"
            await callback.message.answer(
                f"Сегодня тренировок нет.\nБлижайшая: <b>{gname}</b> — {_fmt(nxt.starts_at)}",
                reply_markup=main_menu_kb(user.role),
            )
        else:
            await callback.message.answer(
                "Сегодня тренировок нет. Ближайших тоже пока нет.",
                reply_markup=main_menu_kb(user.role),
            )
        return

    def label(i: ScheduleInstance) -> str:
        gname = i.group.name if i.group else "Группа"
        return f"{gname} · {_fmt(i.starts_at)}"

    await callback.message.answer(
        "Занятия на сегодня — выберите для отметки:",
        reply_markup=coach_instances_kb(instances, label),
    )


@router.callback_query(F.data.startswith("c:inst:"))
async def coach_open_instance(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    instance_id = int(callback.data.split(":")[2])
    inst = await session.get(ScheduleInstance, instance_id)
    if not inst:
        await callback.message.answer("Занятие не найдено.")
        return

    # дети в группе (active/trial enrollments)
    result = await session.execute(
        select(Child)
        .join(Enrollment, Enrollment.child_id == Child.id)
        .where(
            Enrollment.group_id == inst.group_id,
            Enrollment.ended_at.is_(None),
            Enrollment.status.in_(["trial", "active"]),
            Child.deleted_at.is_(None),
        )
        .order_by(Child.name)
    )
    children = list(result.scalars().all())

    # текущие отметки
    att_map = {}
    if children:
        att_res = await session.execute(
            select(Attendance).where(
                Attendance.instance_id == instance_id,
                Attendance.child_id.in_([c.id for c in children]),
            )
        )
        for a in att_res.scalars().all():
            att_map[a.child_id] = a.status

    if not children:
        await callback.message.answer(
            "В группе пока нет детей с enrollment. Добавьте через seed или запись."
        )
        return

    rows = []
    for c in children:
        rows.append(coach_att_kb(c.id, instance_id, att_map.get(c.id)))
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="coach:today")])
    g = await session.get(Group, inst.group_id)
    await callback.message.answer(
        f"<b>{g.name if g else 'Группа'}</b> · {_fmt(inst.starts_at)}\nОтметьте присутствующих:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("co:y:") | F.data.startswith("co:n:"))
async def coach_mark(callback: CallbackQuery, session: AsyncSession, user: User):
    parts = callback.data.split(":")
    # co:y:child:instance
    status = "attended" if parts[1] == "y" else "no_show"
    child_id = int(parts[2])
    instance_id = int(parts[3])
    ok, msg = await coach_set_attendance(
        session,
        child_id=child_id,
        instance_id=instance_id,
        status=status,
        coach=user,
    )
    if not ok:
        await callback.answer(msg, show_alert=True)
        return
    await callback.answer("Сохранено")

    # no-show → планируем сообщение родителю через 2ч (для демо можно сразу короткий delay)
    if status == "no_show":
        child = await session.get(Child, child_id)
        if child:
            parent = await session.get(User, child.parent_user_id)
            if parent:
                from datetime import timedelta
                await schedule_reminder(
                    session,
                    target_user_id=parent.id,
                    type_="noshow_2h",
                    send_at=datetime.now(timezone.utc) + timedelta(seconds=30),  # демо: почти сразу
                    payload={
                        "text": (
                            f"Вы не пришли на занятие ({child.name}).\n"
                            "Хотите перенести пробное/занятие? Напишите администратору или откройте меню записи."
                        ),
                        "child_id": child.id,
                        "instance_id": instance_id,
                    },
                    entity_id=f"{instance_id}:{child.id}",
                )

    await callback.message.answer(f"Отметка сохранена: <b>{'пришёл' if status=='attended' else 'не пришёл'}</b>")


# ---------- Рассылка ----------

@router.callback_query(F.data == "coach:broadcast")
async def coach_broadcast_start(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    if not _is_coach(user):
        return
    result = await session.execute(
        select(Group).where(Group.coach_user_id == user.id, Group.is_active.is_(True))
    )
    groups = list(result.scalars().all())
    # admin видит все группы
    if user.role == "admin" and not groups:
        result = await session.execute(select(Group).where(Group.is_active.is_(True)))
        groups = list(result.scalars().all())
    if not groups:
        await callback.message.answer("Нет групп для рассылки.")
        return
    await fsm.set_state(session, user, {"step": "bc_choose_group"})
    await callback.message.answer("Выберите группу:", reply_markup=groups_for_coach_kb(groups))


@router.callback_query(F.data.startswith("c:grp:"))
async def coach_bc_group(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    await fsm.set_state(session, user, {"step": "bc_text", "broadcast_group_id": group_id})
    await callback.message.answer("Введите текст рассылки одним сообщением:")



@router.callback_query(F.data == "c:bc:yes")
async def coach_bc_yes(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    state = await fsm.get_state(session, user)
    if state.get("step") != "bc_confirm":
        await callback.message.answer("Сессия истекла.")
        return
    parent_ids = state.get("broadcast_parent_ids") or []
    text = state.get("broadcast_text") or ""
    group_id = state.get("broadcast_group_id")
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    for pid in parent_ids:
        await schedule_reminder(
            session,
            target_user_id=pid,
            type_="broadcast",
            send_at=now,
            payload={"text": f"📢 Сообщение от тренера:\n\n{text}"},
            entity_id=f"{group_id}:{pid}:{int(now.timestamp())}",
        )
    await fsm.clear_state(session, user)
    await callback.message.answer(
        f"Рассылка поставлена в очередь: {len(parent_ids)} сообщений.",
        reply_markup=main_menu_kb(user.role),
    )


@router.callback_query(F.data == "c:bc:no")
async def coach_bc_no(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer("Отменено")
    await fsm.clear_state(session, user)
    await callback.message.answer("Рассылка отменена.", reply_markup=main_menu_kb(user.role))


# ---------- Отмена занятия ----------

@router.callback_query(F.data == "coach:manage")
async def coach_manage(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    if not _is_coach(user):
        return
    now = datetime.now(timezone.utc)
    q = (
        select(ScheduleInstance)
        .join(Group, Group.id == ScheduleInstance.group_id)
        .where(
            ScheduleInstance.starts_at > now,
            ScheduleInstance.status == "scheduled",
        )
        .options(selectinload(ScheduleInstance.group))
        .order_by(ScheduleInstance.starts_at)
        .limit(10)
    )
    if user.role == "coach":
        q = q.where(Group.coach_user_id == user.id)
    result = await session.execute(q)
    instances = list(result.scalars().all())
    if not instances:
        await callback.message.answer("Нет будущих занятий для отмены.")
        return

    rows = []
    for i in instances:
        gname = i.group.name if i.group else "Группа"
        rows.append([
            InlineKeyboardButton(
                text=f"{gname} · {_fmt(i.starts_at)}",
                callback_data=f"c:cancel:{i.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="« Меню", callback_data="p:menu")])
    await callback.message.answer(
        "Выберите занятие для отмены:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("c:cancel:"))
async def coach_cancel_pick(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    instance_id = int(callback.data.split(":")[2])
    await fsm.set_state(session, user, {"step": "cancel_reason", "cancel_instance_id": instance_id})
    await callback.message.answer("Укажите причину отмены одним сообщением:")


