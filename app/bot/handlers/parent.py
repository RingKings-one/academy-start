from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.bot.keyboards.common import (
    main_menu_kb,
    directions_kb,
    groups_kb,
    instances_kb,
    medcert_kb,
    children_kb,
    child_actions_kb,
    attendance_kb,
)
from app.db.models import User, Direction, Group, ScheduleInstance, Attendance, Application
from app.services import fsm
from app.services.application_service import create_application
from app.services.child_service import list_children, create_child, set_active_child, get_child
from app.services.attendance_service import parent_set_attendance
from app.services.reminder_service import schedule_reminder

router = Router(name="parent")
TZ = ZoneInfo(settings.app_tz)


def _fmt_dt(dt: datetime) -> str:
    local = dt.astimezone(TZ)
    weekdays = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    wd = weekdays[local.weekday()]
    return f"{local.strftime('%d.%m')}, {wd}, {local.strftime('%H:%M')}"


@router.callback_query(F.data == "p:menu")
async def back_menu(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    await fsm.clear_state(session, user)
    await callback.message.answer("Главное меню:", reply_markup=main_menu_kb(user.role))


# ---------- Запись на пробное (FSM) ----------

@router.callback_query(F.data == "parent:apply")
async def parent_apply(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    result = await session.execute(
        select(Direction).where(Direction.is_active.is_(True)).order_by(Direction.sort_order)
    )
    directions = list(result.scalars().all())
    if not directions:
        await callback.message.answer("Направления пока не настроены. Напишите администратору.")
        return
    await fsm.set_state(session, user, {"step": "choose_direction"})
    await callback.message.answer("Выберите направление:", reply_markup=directions_kb(directions))


@router.callback_query(F.data.startswith("p:dir:"))
async def choose_direction(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    dir_id = int(callback.data.split(":")[2])
    result = await session.execute(
        select(Group).where(Group.direction_id == dir_id, Group.is_active.is_(True))
    )
    groups = list(result.scalars().all())
    await fsm.set_state(session, user, {"step": "choose_group", "direction_id": dir_id})
    if not groups:
        await callback.message.answer("В этом направлении пока нет групп.")
        return
    await callback.message.answer("Выберите группу:", reply_markup=groups_kb(groups))


@router.callback_query(F.data.startswith("p:grp:"))
async def choose_group(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    group_id = int(callback.data.split(":")[2])
    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(ScheduleInstance)
        .where(
            ScheduleInstance.group_id == group_id,
            ScheduleInstance.starts_at > now,
            ScheduleInstance.status == "scheduled",
        )
        .order_by(ScheduleInstance.starts_at)
        .limit(8)
    )
    instances = list(result.scalars().all())
    await fsm.update_state(session, user, step="choose_instance", group_id=group_id)
    if not instances:
        await callback.message.answer(
            "Ближайших занятий нет. Заявка будет без точного времени — администратор свяжется."
        )
        await fsm.update_state(session, user, step="enter_child", trial_instance_id=None)
        await callback.message.answer("Введите имя и возраст ребёнка одним сообщением:\n<code>Артём 8</code>")
        return

    def label(i: ScheduleInstance) -> str:
        return _fmt_dt(i.starts_at)

    await callback.message.answer(
        "Выберите время пробного:",
        reply_markup=instances_kb(instances, label),
    )


@router.callback_query(F.data.startswith("p:inst:"))
async def choose_instance(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    inst_id = int(callback.data.split(":")[2])
    await fsm.update_state(session, user, step="enter_child", trial_instance_id=inst_id)
    await callback.message.answer(
        "Введите имя и возраст ребёнка одним сообщением:\n<code>Артём 8</code>"
    )



@router.callback_query(F.data.startswith("p:med:"))
async def choose_medcert(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    med = callback.data.split(":")[2]
    state = await fsm.get_state(session, user)
    if state.get("step") != "medcert":
        await callback.message.answer("Сессия истекла. Начните запись заново.", reply_markup=main_menu_kb(user.role))
        return

    name = state.get("child_name")
    age = int(state.get("child_age") or 8)
    direction_id = int(state.get("direction_id"))
    group_id = state.get("group_id")
    trial_instance_id = state.get("trial_instance_id")
    birth = date(date.today().year - age, 1, 1)

    phone = user.phone or "+70000000000"
    # создаём child если нужно
    children = await list_children(session, user)
    child = next((c for c in children if c.name.lower() == name.lower()), None)
    if not child:
        child = await create_child(session, user, name=name, birth_date=birth)

    app = await create_application(
        session,
        source="bot",
        child_name=name,
        phone=phone,
        direction_id=direction_id,
        pd_consent=True,
        parent_user=user,
        child_id=child.id,
        child_birth_date=birth,
        group_id=int(group_id) if group_id else None,
        trial_instance_id=int(trial_instance_id) if trial_instance_id else None,
        medcert=med,
    )
    app.status = "confirmed"
    await session.flush()

    # планируем напоминания если есть занятие
    if trial_instance_id:
        inst = await session.get(ScheduleInstance, int(trial_instance_id))
        if inst:
            for typ, delta in (("reminder_24h", timedelta(hours=24)), ("reminder_2h", timedelta(hours=2))):
                send_at = inst.starts_at - delta
                if send_at > datetime.now(timezone.utc):
                    await schedule_reminder(
                        session,
                        target_user_id=user.id,
                        type_=typ,
                        send_at=send_at,
                        payload={
                            "text": (
                                f"Напоминание: {child.name}, занятие {_fmt_dt(inst.starts_at)}.\n"
                                f"Будете?"
                            ),
                            "child_id": child.id,
                            "instance_id": inst.id,
                            "buttons": [
                                {"code": f"att:y:{inst.id}", "label": "Буду"},
                                {"code": f"att:n:{inst.id}", "label": "Не буду"},
                            ],
                        },
                        entity_id=f"{inst.id}:{child.id}",
                    )

    await fsm.clear_state(session, user)
    when = ""
    if trial_instance_id:
        inst = await session.get(ScheduleInstance, int(trial_instance_id))
        if inst:
            when = f"\nВремя: <b>{_fmt_dt(inst.starts_at)}</b>"
    await callback.message.answer(
        f"✅ Заявка #{app.id} создана!\n"
        f"Ребёнок: <b>{name}</b>{when}\n"
        f"Медсправка: {'есть' if med == 'has' else 'нужна помощь'}\n\n"
        "Пришлём напоминание заранее. Можно ответить «Буду» / «Не буду».",
        reply_markup=main_menu_kb(user.role),
    )


# ---------- Дети ----------

@router.callback_query(F.data == "parent:children")
async def parent_children(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    children = await list_children(session, user)
    if not children:
        await callback.message.answer(
            "Пока нет детей. Добавьте первого:",
            reply_markup=children_kb([], user.active_child_id),
        )
        return
    await callback.message.answer(
        "Ваши дети (✓ — активный для «Буду» и расписания):",
        reply_markup=children_kb(list(children), user.active_child_id),
    )


@router.callback_query(F.data == "p:add_child")
async def add_child_start(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    await fsm.set_state(session, user, {"step": "add_child_name"})
    await callback.message.answer("Введите имя и возраст:\n<code>Мия 6</code>")


@router.callback_query(F.data.startswith("p:child:"))
async def child_card(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    child_id = int(callback.data.split(":")[2])
    child = await get_child(session, child_id, user)
    if not child:
        await callback.message.answer("Ребёнок не найден.")
        return
    age = date.today().year - child.birth_date.year
    await callback.message.answer(
        f"<b>{child.name}</b>, ~{age} лет",
        reply_markup=child_actions_kb(child.id),
    )


@router.callback_query(F.data.startswith("p:act:"))
async def activate_child(callback: CallbackQuery, session: AsyncSession, user: User):
    child_id = int(callback.data.split(":")[2])
    ok = await set_active_child(session, user, child_id)
    await callback.answer("Активный ребёнок обновлён" if ok else "Ошибка", show_alert=not ok)
    if ok:
        children = await list_children(session, user)
        await callback.message.edit_reply_markup(
            reply_markup=children_kb(list(children), user.active_child_id)
        )


@router.callback_query(F.data.startswith("p:hist:"))
async def child_history(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    child_id = int(callback.data.split(":")[2])
    result = await session.execute(
        select(Attendance)
        .where(Attendance.child_id == child_id)
        .order_by(Attendance.set_at.desc())
        .limit(10)
    )
    rows = list(result.scalars().all())
    if not rows:
        await callback.message.answer("Истории посещений пока нет.")
        return
    lines = [f"• {r.status} (instance #{r.instance_id}, {r.source})" for r in rows]
    await callback.message.answer("<b>Последние отметки:</b>\n" + "\n".join(lines))


# ---------- Расписание ----------

@router.callback_query(F.data == "parent:schedule")
async def parent_schedule(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    if not user.active_child_id:
        children = await list_children(session, user)
        if not children:
            await callback.message.answer("Сначала добавьте ребёнка в «Мои дети».")
            return
        await set_active_child(session, user, children[0].id)

    now = datetime.now(timezone.utc)
    result = await session.execute(
        select(ScheduleInstance)
        .where(
            ScheduleInstance.starts_at > now - timedelta(hours=2),
            ScheduleInstance.status == "scheduled",
        )
        .options(selectinload(ScheduleInstance.group))
        .order_by(ScheduleInstance.starts_at)
        .limit(6)
    )
    instances = list(result.scalars().all())
    if not instances:
        await callback.message.answer("Ближайших занятий нет.")
        return

    child = await get_child(session, user.active_child_id, user)
    cname = child.name if child else "ребёнка"
    lines = [f"Расписание (для <b>{cname}</b>):\n"]
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    rows = []
    for i in instances:
        gname = i.group.name if i.group else "Группа"
        lines.append(f"• {gname}: {_fmt_dt(i.starts_at)}")
        rows.append([
            InlineKeyboardButton(
                text=f"Буду/Не буду · {_fmt_dt(i.starts_at)}",
                callback_data=f"att:menu:{i.id}",
            )
        ])
    rows.append([InlineKeyboardButton(text="« Меню", callback_data="p:menu")])
    await callback.message.answer(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=rows),
    )


@router.callback_query(F.data.startswith("att:menu:"))
async def att_menu(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    instance_id = int(callback.data.split(":")[2])
    await callback.message.answer(
        "Отметьте присутствие:",
        reply_markup=attendance_kb(instance_id),
    )


@router.callback_query(F.data.startswith("att:y:") | F.data.startswith("att:n:"))
async def parent_attendance(callback: CallbackQuery, session: AsyncSession, user: User):
    parts = callback.data.split(":")
    status = "going" if parts[1] == "y" else "not_going"
    instance_id = int(parts[2])
    if not user.active_child_id:
        await callback.answer("Сначала выберите ребёнка в «Мои дети»", show_alert=True)
        return
    ok, msg = await parent_set_attendance(
        session,
        child_id=user.active_child_id,
        instance_id=instance_id,
        status=status,
        parent=user,
    )
    if not ok:
        await callback.answer(msg, show_alert=True)
        return
    label = "Буду" if status == "going" else "Не буду"
    await callback.answer(f"Отмечено: {label}")
    await callback.message.answer(
        f"✅ Для активного ребёнка: <b>{label}</b> (занятие #{instance_id})",
        reply_markup=main_menu_kb(user.role),
    )


# ---------- Помощь ----------

@router.callback_query(F.data == "parent:help")
async def parent_help(callback: CallbackQuery, session: AsyncSession, user: User):
    await callback.answer()
    await fsm.set_state(session, user, {"step": "help_admin"})
    await callback.message.answer("Напишите вопрос одним сообщением — передадим администратору.")
