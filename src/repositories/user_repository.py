# src/repositories/user_repository.py

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, user_id: int):
        stmt = select(User).where(User.id == user_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_telegram_id(self, telegram_id: int):
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100):
        stmt = select(User).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def delete(self, user: User):
        """Удаление пользователя"""
        await self.session.delete(user)

async def get_by_phone(self, phone: str):
    stmt = select(User).where(User.phone == phone)
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
