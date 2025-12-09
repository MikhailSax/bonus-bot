from aiogram import Router, F
from aiogram.types import CallbackQuery
from sqlalchemy import select, func

from src.database import AsyncSessionLocal
from src.models.user import User
from src.models.transaction import Transaction

router = Router()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        total_users = await session.scalar(select(func.count(User.id)))
        total_balance = await session.scalar(select(func.sum(User.balance)))
        total_trx = await session.scalar(select(func.count(Transaction.id)))

    text = (
        "<b>📊 Общая статистика</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"💎 Всего бонусов: <b>{total_balance or 0}</b>\n"
        f"📜 Историй операций: <b>{total_trx}</b>"
    )

    await callback.message.edit_text(text)
