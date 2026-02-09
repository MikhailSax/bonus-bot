# src/handlers/admin/panel.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext

from src.keyboards.admin_kb import (
    admin_main_menu_kb,
    admin_user_list_kb,
    admin_bonuses_menu_kb,
    admin_holidays_menu_kb,
)
from src.database import AsyncSessionLocal
from src.models.user import User
from src.handlers.admin.qr_scan import QrScanFSM
from sqlalchemy import select, func

router = Router()


# ---------------------------------------------------------
# Вход в админ-панель
# ---------------------------------------------------------
@router.message(F.text == "/admin")
async def open_admin_panel(message: Message, is_admin: bool):
    if not is_admin:
        return await message.answer("⛔ У вас нет доступа!")

    await message.answer("⚙ Админ-панель", reply_markup=admin_main_menu_kb())


# ---------------------------------------------------------
# Переход в главное меню админа
# ---------------------------------------------------------
@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("⚙ Админ-панель", reply_markup=admin_main_menu_kb())
    await callback.answer()


# ---------------------------------------------------------
# Блок пользователей → показать список
# ---------------------------------------------------------
@router.callback_query(F.data == "admin_users")
async def admin_open_users(callback: CallbackQuery):
    page = 1
    await send_users_page(callback, page)


@router.callback_query(F.data.startswith("admin_users_page:"))
async def admin_users_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    await send_users_page(callback, page)


async def send_users_page(callback: CallbackQuery, page: int):
    LIMIT = 10
    offset = (page - 1) * LIMIT

    async with AsyncSessionLocal() as session:
        total = await session.scalar(select(func.count(User.id)))
        users = (
            await session.execute(
                select(User).order_by(User.id.desc()).offset(offset).limit(LIMIT)
            )
        ).scalars().all()

    total_pages = max((total + LIMIT - 1) // LIMIT, 1)

    if not users:
        await callback.message.edit_text(
            "👥 Пользователей пока нет.",
            reply_markup=admin_main_menu_kb()
        )
        return

    await callback.message.edit_text(
        f"👥 Пользователи (стр. {page}/{total_pages})",
        reply_markup=admin_user_list_kb(users, page, total_pages)
    )
    await callback.answer()


# ---------------------------------------------------------
# Меню управления бонусами
# ---------------------------------------------------------
@router.callback_query(F.data == "admin_bonuses")
async def admin_bonuses(callback: CallbackQuery):
    await callback.message.edit_text(
        "🎁 Управление бонусами",
        reply_markup=admin_bonuses_menu_kb()
    )
    await callback.answer()


# ---------------------------------------------------------
# Меню управления праздниками
# ---------------------------------------------------------
@router.callback_query(F.data == "admin_holidays")
async def admin_holidays(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "📅 Управление праздниками",
            reply_markup=admin_holidays_menu_kb()
        )
    except TelegramBadRequest as e:
        # Если повторно жмём по той же кнопке и текст/клава не меняются —
        # Телега шлёт "message is not modified". Такое просто игнорируем.
        if "message is not modified" in str(e):
            await callback.answer()
            return
        # Остальные ошибки пробрасываем дальше, чтобы их было видно.
        raise

    await callback.answer()


# ---------------------------------------------------------
# Сканирование QR-кода
# ---------------------------------------------------------
@router.callback_query(F.data == "admin_qr_scan")
async def admin_qr_scan(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QrScanFSM.waiting)
    await callback.message.edit_text(
        "📷 Отправьте QR-код (фото) для сканирования.\n"
        "После распознавания я покажу данные пользователя.",
        reply_markup=admin_main_menu_kb()
    )
    await callback.answer()
