# src/handlers/admin/holidays.py

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.holiday_bonus import HolidayBonus, UserHolidayBonus
from src.models.user import User
from src.keyboards.admin_kb import (
    admin_back_kb,
    admin_holiday_actions_kb,
    admin_holidays_list_kb,
)

router = Router()


# =====================================================
# FSM для создания праздника
# =====================================================

class HolidayFSM(StatesGroup):
    name = State()
    amount = State()


# =====================================================
# Просмотр списка праздников
# =====================================================

@router.callback_query(F.data == "admin_holiday_list")
async def admin_holiday_list(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        holidays = (await session.execute(select(HolidayBonus))).scalars().all()

    if not holidays:
        text = "🎉 Список праздников пока пуст."
    else:
        text = "🎉 Праздники:\n\n"
        for h in holidays:
            text += f"📌 *{h.name}* — {h.amount} бонусов\n"

    await callback.message.edit_text(
        text,
        reply_markup=admin_holidays_list_kb(holidays),
        parse_mode="Markdown"
    )
    await callback.answer()


# =====================================================
# Открытие одного праздника
# =====================================================

@router.callback_query(F.data.startswith("admin_holiday_open:"))
async def admin_holiday_open(callback: CallbackQuery):
    holiday_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        holiday = (
            await session.execute(
                select(HolidayBonus).where(HolidayBonus.id == holiday_id)
            )
        ).scalar_one_or_none()

    if not holiday:
        await callback.answer("Ошибка: праздник не найден", show_alert=True)
        return

    text = (
        f"🎉 *{holiday.name}*\n\n"
        f"Бонус: {holiday.amount}\n"
        f"Активен: {'✅' if holiday.is_active else '❌'}\n"
    )

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=admin_holiday_actions_kb(holiday_id),
    )
    await callback.answer()


# =====================================================
# Создание нового праздника — шаг 1 (название)
# =====================================================

@router.callback_query(F.data == "admin_holiday_add")
async def holiday_create(callback: CallbackQuery, state: FSMContext):
    await state.set_state(HolidayFSM.name)

    await callback.message.edit_text(
        "Введите название праздника:",
        reply_markup=admin_back_kb("admin_holiday_list")
    )
    await callback.answer()


@router.message(HolidayFSM.name)
async def holiday_set_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым. Введите ещё раз:")
        return

    await state.update_data(name=name)
    await state.set_state(HolidayFSM.amount)

    await message.answer("Введите количество бонусов за этот праздник (целое число):")


# =====================================================
# Создание нового праздника — шаг 2 (бонусы)
# =====================================================

@router.message(HolidayFSM.amount)
async def holiday_set_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Введите положительное целое число!")
        return

    data = await state.get_data()
    name = data["name"]

    async with AsyncSessionLocal() as session:
        holiday = HolidayBonus(name=name, amount=amount)
        session.add(holiday)
        await session.commit()

    await message.answer(
        f"🎉 Праздник *{name}* создан! Бонус: {amount}",
        parse_mode="Markdown"
    )

    await state.clear()


# =====================================================
# Удаление праздника
# =====================================================

@router.callback_query(F.data.startswith("holiday_delete:"))
async def holiday_delete(callback: CallbackQuery):
    holiday_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        holiday = (
            await session.execute(
                select(HolidayBonus).where(HolidayBonus.id == holiday_id)
            )
        ).scalar_one_or_none()

        if not holiday:
            await callback.answer("Ошибка: праздник не найден", show_alert=True)
            return

        await session.delete(holiday)
        await session.commit()

    await callback.message.edit_text("🗑 Праздник удалён!")
    await callback.answer()


# =====================================================
# Начисление бонусов всем пользователям за праздник
# =====================================================

@router.callback_query(F.data.startswith("holiday_give:"))
async def holiday_give(callback: CallbackQuery):
    holiday_id = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        holiday = (
            await session.execute(
                select(HolidayBonus).where(HolidayBonus.id == holiday_id)
            )
        ).scalar_one_or_none()

        if not holiday:
            await callback.answer("Ошибка: праздник не найден", show_alert=True)
            return

        users = (await session.execute(select(User))).scalars().all()

        for user in users:
            user.balance += holiday.amount

            session.add(
                UserHolidayBonus(
                    user_id=user.id,
                    holiday_id=holiday.id,
                    amount=holiday.amount,
                )
            )

        await session.commit()

    await callback.message.edit_text(
        f"🎁 Всем пользователям начислено {holiday.amount} бонусов за *{holiday.name}*!",
        parse_mode="Markdown"
    )
    await callback.answer()
