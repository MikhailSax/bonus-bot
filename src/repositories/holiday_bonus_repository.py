# src/repositories/holiday_bonus_repository.py
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import datetime, date, timedelta
from src.database import AsyncSessionLocal
from src.models.holiday_bonus import HolidayBonus, UserHolidayBonus


class HolidayBonusRepository:
    def __init__(self):
        pass

    async def get_all_holidays(self) -> List[HolidayBonus]:
        """Получить все праздники"""
        async with AsyncSessionLocal() as session:
            stmt = select(HolidayBonus).order_by(HolidayBonus.date)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_active_holidays(self) -> List[HolidayBonus]:
        """Получить активные праздники"""
        async with AsyncSessionLocal() as session:
            stmt = select(HolidayBonus).where(
                HolidayBonus.is_active == True
            ).order_by(HolidayBonus.date)
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_holiday_by_id(self, holiday_id: int) -> Optional[HolidayBonus]:
        """Получить праздник по ID"""
        async with AsyncSessionLocal() as session:
            stmt = select(HolidayBonus).where(HolidayBonus.id == holiday_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def create_holiday(self, **kwargs) -> HolidayBonus:
        """Создать новый праздник"""
        async with AsyncSessionLocal() as session:
            holiday = HolidayBonus(**kwargs)
            session.add(holiday)
            await session.commit()
            await session.refresh(holiday)
            return holiday

    async def update_holiday(self, holiday_id: int, **kwargs) -> Optional[HolidayBonus]:
        """Обновить праздник"""
        async with AsyncSessionLocal() as session:
            stmt = select(HolidayBonus).where(HolidayBonus.id == holiday_id)
            result = await session.execute(stmt)
            holiday = result.scalar_one_or_none()

            if holiday:
                for key, value in kwargs.items():
                    if hasattr(holiday, key):
                        setattr(holiday, key, value)
                await session.commit()
                await session.refresh(holiday)
                return holiday
            return None

    async def delete_holiday(self, holiday_id: int) -> bool:
        """Удалить праздник"""
        async with AsyncSessionLocal() as session:
            stmt = select(HolidayBonus).where(HolidayBonus.id == holiday_id)
            result = await session.execute(stmt)
            holiday = result.scalar_one_or_none()

            if holiday:
                await session.delete(holiday)
                await session.commit()
                return True
            return False

    async def get_upcoming_holidays(self, days: int = 7) -> List[HolidayBonus]:
        """Получить ближайшие праздники"""
        async with AsyncSessionLocal() as session:
            today = date.today()
            end_date = today + timedelta(days=days)

            stmt = select(HolidayBonus).where(
                and_(
                    HolidayBonus.is_active == True,
                    HolidayBonus.date >= today,
                    HolidayBonus.date <= end_date
                )
            ).order_by(HolidayBonus.date)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def check_and_award_holiday_bonuses(self, user_id: int) -> List[UserHolidayBonus]:
        """Проверить и начислить праздничные бонусы пользователю"""
        async with AsyncSessionLocal() as session:
            today = date.today()
            awards = []

            # Получаем все активные праздники
            stmt = select(HolidayBonus).where(HolidayBonus.is_active == True)
            result = await session.execute(stmt)
            holidays = result.scalars().all()

            for holiday in holidays:
                # Рассчитываем дату начисления (за days_before дней до праздника)
                award_date = holiday.date - timedelta(days=holiday.days_before)

                # Проверяем, нужно ли начислить сегодня
                if today >= award_date:
                    # Проверяем, не начисляли ли уже
                    check_stmt = select(UserHolidayBonus).where(
                        and_(
                            UserHolidayBonus.user_id == user_id,
                            UserHolidayBonus.holiday_id == holiday.id,
                            UserHolidayBonus.awarded_at >= datetime(award_date.year, award_date.month, award_date.day)
                        )
                    )
                    existing = (await session.execute(check_stmt)).scalar_one_or_none()

                    if not existing:
                        # Начисляем бонусы
                        expires_at = datetime.now() + timedelta(days=holiday.days_valid)

                        user_bonus = UserHolidayBonus(
                            user_id=user_id,
                            holiday_id=holiday.id,
                            amount=holiday.amount,
                            expires_at=expires_at
                        )

                        session.add(user_bonus)
                        awards.append(user_bonus)

            if awards:
                await session.commit()
                for award in awards:
                    await session.refresh(award)

            return awards

    async def get_user_holiday_bonuses(self, user_id: int, active_only: bool = True) -> List[UserHolidayBonus]:
        """Получить праздничные бонусы пользователя"""
        async with AsyncSessionLocal() as session:
            conditions = [UserHolidayBonus.user_id == user_id]

            if active_only:
                conditions.append(UserHolidayBonus.is_used == False)
                conditions.append(UserHolidayBonus.expires_at > datetime.now())

            stmt = select(UserHolidayBonus).where(
                and_(*conditions)
            ).order_by(UserHolidayBonus.expires_at)

            result = await session.execute(stmt)
            return result.scalars().all()

    async def use_holiday_bonuses(self, user_id: int, amount: int) -> bool:
        """Использовать праздничные бонусы"""
        async with AsyncSessionLocal() as session:
            # Получаем доступные бонусы
            stmt = select(UserHolidayBonus).where(
                and_(
                    UserHolidayBonus.user_id == user_id,
                    UserHolidayBonus.is_used == False,
                    UserHolidayBonus.expires_at > datetime.now()
                )
            ).order_by(UserHolidayBonus.expires_at)  # Используем те, что истекают раньше

            result = await session.execute(stmt)
            bonuses = result.scalars().all()

            remaining = amount
            used_bonuses = []

            for bonus in bonuses:
                if remaining <= 0:
                    break

                if bonus.amount <= remaining:
                    bonus.is_used = True
                    bonus.used_at = datetime.now()
                    remaining -= bonus.amount
                    used_bonuses.append(bonus)
                else:
                    # Создаем новую запись с остатком
                    new_bonus = UserHolidayBonus(
                        user_id=user_id,
                        holiday_id=bonus.holiday_id,
                        amount=bonus.amount - remaining,
                        awarded_at=bonus.awarded_at,
                        expires_at=bonus.expires_at
                    )
                    session.add(new_bonus)

                    bonus.amount = remaining
                    bonus.is_used = True
                    bonus.used_at = datetime.now()
                    used_bonuses.append(bonus)
                    remaining = 0

            if remaining == 0 and used_bonuses:
                await session.commit()
                return True

            return False