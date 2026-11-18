from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu_kb(role: str) -> InlineKeyboardMarkup:
    if role == "admin":
        buttons = [
            [InlineKeyboardButton(text="📊 Дайджест", callback_data="admin:digest")],
            [InlineKeyboardButton(text="🚨 Проблемные заявки", callback_data="admin:problems")],
            [InlineKeyboardButton(text="👦 Как родитель (меню)", callback_data="admin:as_parent")],
        ]
    elif role == "coach":
        buttons = [
            [InlineKeyboardButton(text="📋 Занятия сегодня", callback_data="coach:today")],
            [InlineKeyboardButton(text="📢 Рассылка группе", callback_data="coach:broadcast")],
            [InlineKeyboardButton(text="⚙️ Отменить занятие", callback_data="coach:manage")],
        ]
    else:
        buttons = [
            [InlineKeyboardButton(text="🟢 Записаться на пробное", callback_data="parent:apply")],
            [InlineKeyboardButton(text="👦 Мои дети", callback_data="parent:children")],
            [InlineKeyboardButton(text="📅 Расписание", callback_data="parent:schedule")],
            [InlineKeyboardButton(text="✉️ Вопрос администратору", callback_data="parent:help")],
        ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def directions_kb(directions: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=d.name, callback_data=f"p:dir:{d.id}")]
        for d in directions
    ]
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="p:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def groups_kb(groups: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=g.name, callback_data=f"p:grp:{g.id}")]
        for g in groups
    ]
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="parent:apply")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def instances_kb(instances: list, label_fn) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label_fn(i), callback_data=f"p:inst:{i.id}")]
        for i in instances
    ]
    rows.append([InlineKeyboardButton(text="« Назад", callback_data="parent:apply")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def medcert_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Есть", callback_data="p:med:has"),
                InlineKeyboardButton(text="Нужна помощь", callback_data="p:med:needs"),
            ],
            [InlineKeyboardButton(text="« Отмена", callback_data="p:menu")],
        ]
    )


def children_kb(children: list, active_id: int | None) -> InlineKeyboardMarkup:
    rows = []
    for c in children:
        mark = "✓ " if c.id == active_id else ""
        rows.append(
            [InlineKeyboardButton(text=f"{mark}{c.name}", callback_data=f"p:child:{c.id}")]
        )
    rows.append([InlineKeyboardButton(text="➕ Добавить ребёнка", callback_data="p:add_child")])
    rows.append([InlineKeyboardButton(text="« Меню", callback_data="p:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def child_actions_kb(child_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сделать активным", callback_data=f"p:act:{child_id}")],
            [InlineKeyboardButton(text="История посещений", callback_data=f"p:hist:{child_id}")],
            [InlineKeyboardButton(text="« К списку", callback_data="parent:children")],
        ]
    )


def attendance_kb(instance_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Буду", callback_data=f"att:y:{instance_id}"),
                InlineKeyboardButton(text="❌ Не буду", callback_data=f"att:n:{instance_id}"),
            ]
        ]
    )


def coach_instances_kb(instances: list, label_fn) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label_fn(i), callback_data=f"c:inst:{i.id}")]
        for i in instances
    ]
    rows.append([InlineKeyboardButton(text="« Меню", callback_data="p:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def coach_att_kb(child_id: int, instance_id: int, current: str | None = None) -> list:
    """Одна строка кнопок для ребёнка."""
    yes = "☑️ Пришёл" if current == "attended" else "✅ Пришёл"
    no = "☑️ Не пришёл" if current == "no_show" else "❌ Не пришёл"
    return [
        InlineKeyboardButton(text=yes, callback_data=f"co:y:{child_id}:{instance_id}"),
        InlineKeyboardButton(text=no, callback_data=f"co:n:{child_id}:{instance_id}"),
    ]


def confirm_broadcast_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Да, отправить", callback_data="c:bc:yes"),
                InlineKeyboardButton(text="Отмена", callback_data="c:bc:no"),
            ]
        ]
    )


def groups_for_coach_kb(groups: list) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=g.name, callback_data=f"c:grp:{g.id}")]
        for g in groups
    ]
    rows.append([InlineKeyboardButton(text="« Меню", callback_data="p:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
