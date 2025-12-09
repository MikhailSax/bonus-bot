# src/handlers/admin/commands.py

from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from sqlalchemy import select, func

from src.database import AsyncSessionLocal
from src.models.user import User

# корректный импорт новой клавиатуры
from src.keyboards.admin_kb import admin_main_menu_kb

router = Router()


# ---------------------------------------------------------
# Проверка роли администратора
# ---------------------------------------------------------
async def is_admin(tg_id: int) -> bool:
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(User).where(User.telegram_id == tg_id))
        u = res.scalar_one_or_none()
        return bool(u and u.role == "admin")


# ---------------------------------------------------------
# Команда: статистика
# ---------------------------------------------------------
@router.message(Command("stats"))
async def admin_stats(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")

    async with AsyncSessionLocal() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        total_balance = await session.scalar(select(func.sum(User.balance)))

    total_balance = total_balance or 0

    text = (
        "<b>📊 Статистика системы</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"💎 Всего бонусов: <b>{total_balance}</b>\n"
    )

    await message.answer(text, reply_markup=admin_main_menu_kb())


# ---------------------------------------------------------
# Команда: начислить бонусы по Telegram ID
# ---------------------------------------------------------
@router.message(Command("addbonus"))
async def add_bonus_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")

    parts = message.text.split()
    if len(parts) != 3:
        return await message.answer("Используйте: /addbonus <telegram_id> <amount>")

    try:
        tg_id = int(parts[1])
        amount = int(parts[2])
    except ValueError:
        return await message.answer("ID и сумма должны быть числами")

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == tg_id)
        res = await session.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            return await message.answer("❌ Пользователь не найден")

        old_balance = user.balance
        user.balance += amount
        await session.commit()

        await message.answer(
            f"✅ Бонусы начислены!\n\n"
            f"👤 {user.first_name}\n"
            f"💎 Было: {old_balance}\n"
            f"💎 Стало: {user.balance}"
        )


# ---------------------------------------------------------
# Нормализация телефона
# ---------------------------------------------------------
def normalize_phone(phone: str) -> str:
    digits = "".join(filter(str.isdigit, phone))
    if len(digits) == 10:
        return "7" + digits
    if len(digits) == 11 and digits.startswith(("7", "8")):
        return "7" + digits[-10:]
    return digits


# ---------------------------------------------------------
# Команда: поиск пользователя по телефону
# ---------------------------------------------------------
@router.message(Command("findphone"))
async def find_phone_cmd(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        return await message.answer("Используйте: /findphone <номер телефона>")

    search = normalize_phone(args[1])

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.phone.ilike(f"%{search}%"))
        users = (await session.execute(stmt)).scalars().all()

    if not users:
        return await message.answer("❌ Пользователь не найден")

    text = "<b>📱 Найденные пользователи:</b>\n\n"
    for u in users:
        text += (
            f"👤 {u.first_name}\n"
            f"📞 {u.phone or 'нет'}\n"
            f"💎 {u.balance} бонусов\n\n"
        )

    await message.answer(text)


# ---------------------------------------------------------
# Команда: список пользователей
# ---------------------------------------------------------
@router.message(Command("users"))
async def list_users(message: Message):
    if not await is_admin(message.from_user.id):
        return await message.answer("⛔ Нет доступа")

    async with AsyncSessionLocal() as session:
        stmt = select(User).order_by(User.created_at.desc())
        users = (await session.execute(stmt)).scalars().all()

    text = "<b>👥 Список пользователей</b>\n\n"
    for u in users[:30]:
        text += f"{u.first_name} — {u.balance} 💎\n"

    await message.answer(text, reply_markup=admin_main_menu_kb())
