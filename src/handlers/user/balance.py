# src/handlers/user/balance.py

import logging

from aiogram import Router, F
from aiogram.types import Message
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.database import AsyncSessionLocal, ensure_schema
from src.models.user import User
from src.models.transaction import Transaction
from src.services.user_service import UserService
from src.keyboards.user_kb import get_user_main_menu, get_back_to_menu

router = Router()
logger = logging.getLogger(__name__)


# =========================
#  Мой баланс
# =========================
@router.message(F.text == "💰 Мой баланс")
async def user_balance(message: Message):
    try:
        await ensure_schema()
        async with AsyncSessionLocal() as session:
            # находим пользователя по telegram_id
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                await message.answer("❌ Вы ещё не зарегистрированы. Нажмите /start")
                return

            # обновляем праздничные бонусы (НГ, ДР и т.п.)
            user_service = UserService(session)
            await user_service.check_and_award_holiday_bonuses(user.id)
            await session.refresh(user)

            balance = user.balance
            holiday_balance = user.holiday_balance
            holiday_info = await user_service.get_user_holiday_bonuses_info(user.id)

    except SQLAlchemyError:
        logger.exception("Ошибка при получении баланса пользователя")
        await message.answer("❌ Ошибка обращения к базе. Сообщите администратору.")
        return

    text_lines = [
        f"💰 Обычные бонусы: *{balance}*",
        f"🎉 Праздничные бонусы: *{holiday_balance}*",
        f"💎 Всего бонусов: *{balance + holiday_balance}*",
    ]

    if holiday_info["total"]:
        text_lines.append("")
        text_lines.append("🎉 Праздничные бонусы:")
        for bonus in holiday_info["bonuses"]:
            text_lines.append(
                f"• {bonus['holiday']}: {bonus['amount']} бонусов "
                f"(до {bonus['expires_at']}, осталось {bonus['days_left']} дн.)"
            )

    await message.answer(
        "\n".join(text_lines),
        parse_mode="Markdown",
        reply_markup=get_back_to_menu(),
    )


# =========================
#  История операций
# =========================
@router.message(F.text == "📊 История операций")
async def user_history(message: Message):
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()

            if not user:
                await message.answer("❌ Вы ещё не зарегистрированы. Нажмите /start")
                return

            # можно тоже обновить праздничные бонусы при входе в историю
            user_service = UserService(session)
            await user_service.check_and_award_holiday_bonuses(user.id)
            await session.refresh(user)

            tr_result = await session.execute(
                select(Transaction)
                .where(Transaction.user_id == user.id)
                .order_by(Transaction.id.desc())
                .limit(10)
            )
            transactions = tr_result.scalars().all()

    except SQLAlchemyError:
        logger.exception("Ошибка при получении истории операций")
        await message.answer("❌ Ошибка при получении истории операций.")
        return

    if not transactions:
        await message.answer(
            "📊 Пока нет операций по вашему аккаунту.",
            reply_markup=get_back_to_menu(),
        )
        return

    lines = ["📊 *Последние операции:*", ""]
    for t in transactions:
        sign = "➕" if t.amount > 0 else "➖"
        lines.append(f"{sign} {abs(t.amount)} — {t.description or ''}")

    await message.answer(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=get_back_to_menu(),
    )


# =========================
#  Назад в меню
# =========================
@router.message(F.text == "⬅️ Назад в меню")
async def back_to_menu(message: Message):
    await message.answer(
        "Главное меню:",
        reply_markup=get_user_main_menu(),
    )
