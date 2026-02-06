# src/handlers/admin/users.py

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from sqlalchemy import select
from src.database import AsyncSessionLocal

from src.models.user import User
from src.models.transaction import Transaction

from src.keyboards.admin_kb import (
    admin_user_actions_kb,
    admin_back_to_users_kb,
    admin_confirm_action_kb,
)

router = Router()


# ==============================
#   FSM для изменения баланса
# ==============================

class EditBalanceFSM(StatesGroup):
    waiting_amount = State()
    action = State()
    user_id = State()


# ==============================
#   Список пользователей
# ==============================

@router.callback_query(F.data == "admin_users")
async def admin_users_list(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        users = (
            await session.execute(select(User).order_by(User.id).limit(200))
        ).scalars().all()

    if not users:
        return await callback.message.edit_text(
            "👥 Пользователей нет.",
            reply_markup=admin_back_to_users_kb()
        )

    text = "👥 Список пользователей:\n\n"
    for u in users:
        text += f"ID: {u.id} | 💳 Баланс: {u.balance} | @{u.username or '-'}\n"

    if len(users) == 200:
        text += "\nПоказаны первые 200 пользователей."

    await callback.message.edit_text(
        text,
        reply_markup=admin_back_to_users_kb()
    )


# ==============================
#   Открыть профиль пользователя
# ==============================

@router.callback_query(F.data.startswith("open_user:"))
async def open_user(callback: CallbackQuery):
    uid = int(callback.data.split(":")[1])

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.id == uid))).scalar_one_or_none()

        if not user:
            return await callback.answer("❌ Пользователь не найден")

    text = (
        f"👤 *Пользователь*\n\n"
        f"ID: {user.id}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Имя: {user.first_name} {user.last_name or ''}\n"
        f"Телефон: {user.phone or '-'}\n"
        f"Баланс: {user.balance}\n"
        f"Роль: {user.role}\n"
    )

    await callback.message.edit_text(
        text,
        reply_markup=admin_user_actions_kb(user.id),
        parse_mode="Markdown"
    )


# ==============================
#   Начислить / Списать бонусы
# ==============================

@router.callback_query(F.data.startswith(("user_bonus_add", "user_bonus_sub")))
async def start_balance_edit(callback: CallbackQuery, state: FSMContext):
    action, uid = callback.data.split(":")
    uid = int(uid)

    await state.update_data(action=action, user_id=uid)
    await state.set_state(EditBalanceFSM.waiting_amount)

    await callback.message.edit_text(
        "Введите сумму:",
        reply_markup=admin_back_to_users_kb()
    )


@router.message(EditBalanceFSM.waiting_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Введите положительное число!")

    await state.update_data(amount=amount)
    data = await state.get_data()

    action = data["action"]
    uid = data["user_id"]

    msg = f"Подтвердите {'начисление' if 'add' in action else 'списание'} {amount} баллов пользователю ID {uid}"

    await message.answer(
        msg,
        reply_markup=admin_confirm_action_kb()
    )


# ==============================
#   Подтверждение операции
# ==============================

@router.callback_query(F.data == "confirm_action")
async def confirm_balance_edit(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()

    uid = data["user_id"]
    amount = data["amount"]
    action = data["action"]

    async with AsyncSessionLocal() as session:
        user = (await session.execute(select(User).where(User.id == uid))).scalar_one_or_none()

        if not user:
            return await callback.answer("❌ Пользователь не найден")

        if "add" in action:
            user.balance += amount
            text = f"➕ Начислено {amount} баллов"
        else:
            user.balance -= amount
            if user.balance < 0:
                user.balance = 0
            text = f"➖ Списано {amount} баллов"

        # История транзакций (если используется)
        tr = Transaction(
            user_id=user.id,
            amount=amount if "add" in action else -amount,
            description="Admin operation"
        )
        session.add(tr)

        await session.commit()

    await state.clear()
    await callback.message.edit_text(text)
    await callback.answer("Готово")


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Действие отменено.",
        reply_markup=admin_back_to_users_kb()
    )
