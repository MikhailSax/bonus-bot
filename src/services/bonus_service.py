# src/services/bonus_service.py

from sqlalchemy import select
from src.database import AsyncSessionLocal
from src.models.user import User
from src.models.transaction import Transaction


class BonusService:

    # =========================
    #   Начислить бонусы
    # =========================
    @staticmethod
    async def add_bonus(user_id: int, amount: int, description: str = "Admin add"):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        async with AsyncSessionLocal() as session:
            user = (await session.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            user.balance += amount

            tr = Transaction(
                user_id=user.id,
                amount=amount,
                description=description
            )
            session.add(tr)

            await session.commit()

            return user.balance

    # =========================
    #   Списать бонусы
    # =========================
    @staticmethod
    async def subtract_bonus(user_id: int, amount: int, description: str = "Admin subtract"):
        if amount <= 0:
            raise ValueError("Amount must be positive")

        async with AsyncSessionLocal() as session:
            user = (await session.execute(
                select(User).where(User.id == user_id)
            )).scalar_one_or_none()

            if not user:
                raise ValueError("User not found")

            user.balance -= amount
            if user.balance < 0:
                user.balance = 0

            tr = Transaction(
                user_id=user.id,
                amount=-amount,
                description=description
            )
            session.add(tr)

            await session.commit()

            return user.balance

    # =========================
    #   Получить историю
    # =========================
    @staticmethod
    async def get_user_transactions(user_id: int, limit=20):
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(Transaction.created_at.desc())
                .limit(limit)
            )
            return result.scalars().all()
