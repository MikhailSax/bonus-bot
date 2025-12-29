from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


# -------------------------------------------------------------------
# Главное меню администратора
# -------------------------------------------------------------------
def admin_main_menu_kb():
    kb = [
        [InlineKeyboardButton(text="📝 Создать пост", callback_data="admin_post_create")],
        [InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton(text="🎁 Бонусы", callback_data="admin_bonuses")],
        [InlineKeyboardButton(text="📅 Праздники", callback_data="admin_holidays")],
        [InlineKeyboardButton(text="📷 Сканировать QR", callback_data="admin_qr_scan")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# -------------------------------------------------------------------
# Список пользователей + пагинация
# -------------------------------------------------------------------
def admin_user_list_kb(users, page: int, total_pages: int):
    keyboard = []

    for u in users:
        full_name = f"{u.first_name or ''} {u.last_name or ''}".strip()
        label = full_name or "Без имени"
        label += f" (ID {u.telegram_id})"

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=label,
                    callback_data=f"open_user:{u.id}",  # важно: совпадает с хендлером open_user
                )
            ]
        )

    nav_row = []
    if page > 1:
        nav_row.append(
            InlineKeyboardButton(
                text="⬅ Назад", callback_data=f"admin_users_page:{page - 1}"
            )
        )
    if page < total_pages:
        nav_row.append(
            InlineKeyboardButton(
                text="Вперед ➡", callback_data=f"admin_users_page:{page + 1}"
            )
        )

    if nav_row:
        keyboard.append(nav_row)

    keyboard.append(
        [InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# -------------------------------------------------------------------
# Кнопки действий над пользователем
# -------------------------------------------------------------------
def admin_user_actions_kb(user_id: int):
    """
    Кнопки внутри карточки пользователя.
    Привязаны к бонусным хендлерам из bonuses.py.
    """
    kb = [
        [
            InlineKeyboardButton(
                text="➕ Начислить", callback_data=f"bonus_add_user:{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="➖ Списать", callback_data=f"bonus_sub_user:{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="5% от покупки", callback_data=f"bonus_percent_user:{user_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ К списку пользователей", callback_data="admin_users"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# -------------------------------------------------------------------
# Подтверждение действия (старые хендлеры из users.py)
# -------------------------------------------------------------------
def admin_confirm_action_kb():
    """
    Используется в users.py для confirm_action / cancel_action.
    Если не пользуешься — можно не трогать, но так всё будет совпадать.
    """
    keyboard = [
        [
            InlineKeyboardButton(text="✔ Подтвердить", callback_data="confirm_action"),
            InlineKeyboardButton(text="✖ Отмена", callback_data="cancel_action"),
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# -------------------------------------------------------------------
# Кнопка «Назад к пользователю» / «Назад к списку»
# -------------------------------------------------------------------
def admin_back_to_users_kb(user_id: int | None = None):
    """
    Если user_id передан — вернёмся к карточке пользователя через bonus_back_user.
    Если нет — просто в список пользователей.
    """
    if user_id is None:
        cb = "admin_users"
    else:
        cb = f"bonus_back_user:{user_id}"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data=cb)]
        ]
    )


# -------------------------------------------------------------------
# Меню управления бонусами (если захочешь отдельный раздел)
# -------------------------------------------------------------------
def admin_bonuses_menu_kb():
    kb = [
        [
            InlineKeyboardButton(
                text="👥 Пользователи", callback_data="admin_users"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ В главное меню", callback_data="admin_menu"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# -------------------------------------------------------------------
# Меню управления праздниками
# -------------------------------------------------------------------
def admin_holidays_menu_kb():
    """
    Экран, который открывается при нажатии на «📅 Праздники» в админ-меню.
    Тут важно, чтобы callback_data совпадали с хендлерами в holidays.py:
      - admin_holiday_add   -> создание праздника
      - admin_holiday_list  -> список праздников
    """
    kb = [
        [
            InlineKeyboardButton(
                text="➕ Добавить праздник", callback_data="admin_holiday_add"
            )
        ],
        [
            InlineKeyboardButton(
                text="📋 Список праздников", callback_data="admin_holiday_list"
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ Назад", callback_data="admin_menu"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# -------------------------------------------------------------------
# Универсальная кнопка "Назад" (используется в holidays.py)
# -------------------------------------------------------------------
def admin_back_kb(callback_data: str):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅ Назад", callback_data=callback_data)]
        ]
    )


# -------------------------------------------------------------------
# Список праздников (для holidays.py)
# -------------------------------------------------------------------
def admin_holidays_list_kb(holidays):
    keyboard = []

    for h in holidays:
        keyboard.append(
            [
                InlineKeyboardButton(
                    text=f"{h.name} (+{h.amount})",
                    callback_data=f"holiday_give:{h.id}",
                ),
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=f"holiday_delete:{h.id}",
                ),
            ]
        )

    keyboard.append(
        [
            InlineKeyboardButton(
                text="➕ Добавить праздник",
                callback_data="admin_holiday_add",  # ✅ тут тоже хендлер из holidays.py
            )
        ]
    )
    keyboard.append(
        [InlineKeyboardButton(text="🏠 В меню", callback_data="admin_menu")]
    )

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# -------------------------------------------------------------------
# Действия над конкретным праздником (на будущее)
# -------------------------------------------------------------------
def admin_holiday_actions_kb(holiday_id: int):
    kb = [
        [
            InlineKeyboardButton(
                text="🎁 Начислить всем",
                callback_data=f"holiday_give:{holiday_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑 Удалить праздник",
                callback_data=f"holiday_delete:{holiday_id}",
            )
        ],
        [
            InlineKeyboardButton(
                text="⬅ Назад", callback_data="admin_holiday_list"
            )
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
