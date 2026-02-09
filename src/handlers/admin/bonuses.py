# src/handlers/admin/bonuses.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.user import User
from src.services.holiday_bonus_service import HolidayBonusService
from src.keyboards.admin_kb import (
    admin_back_to_users_kb,
    admin_user_actions_kb,
)

router = Router()


# ============================================================
# FSM для работы с бонусами
# ============================================================

class BonusFSM(StatesGroup):
    add = State()
    subtract = State()
    percent = State()


# ============================================================
# Вернуться к карточке пользователя
# ============================================================

@router.callback_query(F.data.startswith("bonus_back_user:"))
async def bonus_back_user(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    if not user:
        await callback.message.edit_text("❌ Пользователь не найден")
        await state.clear()
        await callback.answer()
        return

    text = (
        f"👤 *Пользователь*\n\n"
        f"ID: {user.id}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Имя: {user.first_name or ''} {user.last_name or ''}\n"
        f"Телефон: {user.phone or '-'}\n"
        f"Обычные бонусы: {user.balance}\n"
        f"Праздничные бонусы: {user.holiday_balance}\n"
        f"Всего бонусов: {user.total_balance}\n"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_user_actions_kb(user.id),
    )
    await state.clear()
    await callback.answer()


# ============================================================
# Начисление бонусов (ручной ввод)
# ============================================================

@router.callback_query(F.data.startswith("bonus_add_user:"))
async def admin_bonus_add(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await state.update_data(user_id=user.id)
    await state.set_state(BonusFSM.add)

    await callback.message.edit_text(
        "💰 Введите количество бонусов для начисления:",
        reply_markup=admin_back_to_users_kb(user_id),
    )
    await callback.answer()


@router.message(BonusFSM.add)
async def admin_bonus_add_finish(message: Message, state: FSMContext):
    try:
        if message.text is None:
            raise ValueError
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Введите корректное положительное число!")

    data = await state.get_data()
    user_id = data["user_id"]

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one()

        user.balance += amount
        await session.commit()

    await message.answer(
        f"✅ Пользователю начислено *{amount}* бонусов.",
        parse_mode="Markdown",
    )
    await state.clear()


# ============================================================
# Списание бонусов (ручной ввод)
# ============================================================

@router.callback_query(F.data.startswith("bonus_sub_user:"))
async def admin_bonus_sub(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await state.update_data(user_id=user.id)
    await state.set_state(BonusFSM.subtract)

    await callback.message.edit_text(
        "💳 Введите количество бонусов для списания:",
        reply_markup=admin_back_to_users_kb(user_id),
    )
    await callback.answer()


@router.message(BonusFSM.subtract)
async def admin_bonus_sub_finish(message: Message, state: FSMContext):
    try:
        if message.text is None:
            raise ValueError
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Введите корректное положительное число!")

    data = await state.get_data()
    user_id = data["user_id"]

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one()

        if user.total_balance < amount:
            return await message.answer(
                "❌ Недостаточно бонусов для списания!"
            )

        holiday_service = HolidayBonusService(session)
        used_holiday = await holiday_service.apply_holiday_bonus_spend(user.id, amount)
        remaining = amount - used_holiday
        if remaining > 0:
            user.balance -= remaining
            if user.balance < 0:
                user.balance = 0
        await session.commit()

    await message.answer(
        f"🧾 С пользователя списано *{amount}* бонусов.",
        parse_mode="Markdown",
    )
    await state.clear()


# ============================================================
# Начисление 5% от суммы покупки
# ============================================================

@router.callback_query(F.data.startswith("bonus_percent_user:"))
async def admin_bonus_percent(callback: CallbackQuery, state: FSMContext):
    user_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    if not user:
        await callback.answer("Пользователь не найден", show_alert=True)
        return

    await state.update_data(user_id=user.id)
    await state.set_state(BonusFSM.percent)

    await callback.message.edit_text(
        "💳 Введите сумму покупки (в рублях):",
        reply_markup=admin_back_to_users_kb(user_id),
    )
    await callback.answer()


@router.message(BonusFSM.percent)
async def admin_bonus_percent_finish(message: Message, state: FSMContext):
    try:
        if message.text is None:
            raise ValueError
        purchase_amount = float(message.text.replace(",", "."))
        if purchase_amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Введите корректную сумму!")

    bonus = int(purchase_amount * 0.05)

    data = await state.get_data()
    user_id = data["user_id"]

    async with AsyncSessionLocal() as session:
        user = (
            await session.execute(select(User).where(User.id == user_id))
        ).scalar_one()

        user.balance += bonus
        await session.commit()

    await message.answer(
        f"💸 Покупка: *{purchase_amount}₽*\n"
        f"➕ Начислено 5% = *{bonus} бонусов*",
        parse_mode="Markdown",
    )
    await state.clear()
