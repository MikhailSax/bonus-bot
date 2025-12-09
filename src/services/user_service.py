# src/services/user_service.py

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.models.user import User
from src.models.holiday_bonus import UserHolidayBonus
from src.services.holiday_bonus_service import HolidayBonusService


class UserService:
    """
    Универсальный сервис для работы с пользователями.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============================================================
    #                         ПОЛУЧЕНИЕ
    # ============================================================

    async def get_user_by_id(self, user_id: int):
        stmt = select(User).where(User.id == user_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_by_tg_id(self, telegram_id: int):
        stmt = select(User).where(User.telegram_id == telegram_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_user_by_phone(self, phone: str):
        stmt = select(User).where(User.phone == phone)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_all_users(self, limit=200):
        stmt = select(User).limit(limit)
        res = await self.session.execute(stmt)
        return res.scalars().all()

    async def get_user_by_telegram_id(self, tg_id: int):
        return await self.get_user_by_tg_id(tg_id)

    # ============================================================
    #                         РЕГИСТРАЦИЯ / СОЗДАНИЕ
    # ============================================================

    async def get_or_create_user(
            self,
            tg_id: int,
            username: str = None,
            first_name: str = None,
            last_name: str = None,
            birth_date=None,
            phone: str = None
    ):
        """
        Возвращает пользователя или создаёт нового.
        """

        stmt = select(User).where(User.telegram_id == tg_id)
        res = await self.session.execute(stmt)
        user = res.scalar_one_or_none()

        if user:
            return user, False

        new_user = User(
            telegram_id=tg_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            phone=phone,
            balance=200  # приветственный бонус
        )

        self.session.add(new_user)
        await self.session.commit()
        await self.session.refresh(new_user)

        return new_user, True

    async def create_user(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        birth_date=None,
        phone: str | None = None,
        role: str = "user",
    ):
        """
        Явное создание пользователя.
        Используется в хендлерах регистрации (start.py).
        Если пользователь уже есть — просто вернёт его.
        """

        # если уже есть в базе — возвращаем
        existing = await self.get_user_by_tg_id(telegram_id)
        if existing:
            return existing

        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            birth_date=birth_date,
            phone=phone,
            role=role,
            balance=200,  # приветственный бонус, как в get_or_create_user
        )

        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)

        return user


    # ============================================================
    #                        ОБНОВЛЕНИЕ ДАННЫХ
    # ============================================================

    async def update_birth_date(self, user_id: int, birth_date):
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        user.birth_date = birth_date
        await self.session.commit()
        return user

    async def update_phone(self, user_id: int, phone: str):
        user = await self.get_user_by_id(user_id)
        if not user:
            return None

        user.phone = phone
        await self.session.commit()
        return user

    # ============================================================
    #                          УДАЛЕНИЕ
    # ============================================================

    async def delete_user_by_id(self, user_id: int) -> bool:
        user = await self.get_user_by_id(user_id)
        if not user:
            return False

        await self.session.delete(user)
        await self.session.commit()
        return True

    # ============================================================
    #                    ПРАЗДНИЧНЫЕ БОНУСЫ
    # ============================================================

    async def check_and_award_holiday_bonuses(self, user_id: int):
        """Проверка начисления ДР и праздничных бонусов"""
        holiday_service = HolidayBonusService(self.session)
        return await holiday_service.check_and_award_user_bonuses(user_id)

    async def get_user_holiday_bonuses_info(self, user_id: int):
        """Информация о бонусах пользователя"""

        stmt = select(UserHolidayBonus).where(UserHolidayBonus.user_id == user_id)
        res = await self.session.execute(stmt)
        bonuses = res.scalars().all()

        now = datetime.now()
        active = []

        for b in bonuses:
            if b.expires_at and b.expires_at > now:
                active.append({
                    "id": b.id,
                    "amount": b.amount,
                    "expires_at": b.expires_at.strftime("%d.%m.%Y"),
                    "days_left": (b.expires_at - now).days
                })

        return {
            "total": len(active),
            "bonuses": active
        }
