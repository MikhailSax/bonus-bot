# src/services/holiday_bonus_service.py

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Optional, List, Dict

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.user import User
from src.models.holiday_bonus import HolidayBonus, UserHolidayBonus
from src.models.transaction import Transaction


class HolidayBonusService:
    """
    Сервис, который:

    - создаёт дефолтные праздники (НГ, 23 февраля, Сагаалган);
    - при заходе юзера в профиль/баланс:
        1) сжигает просроченные праздничные бонусы;
        2) начисляет бонус ко дню рождения;
        3) начисляет бонусы по праздникам из таблицы holidays.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    # ------------------------------------------------------------------
    # Инициализация дефолтных праздников (вызывается в main.py)
    # ------------------------------------------------------------------
    async def initialize_default_holidays(self):
        """
        Создаёт в таблице holidays базовый набор праздников,
        если их ещё нет.
        """
        async def _impl(session: AsyncSession):
            defaults: List[Dict] = [
                {
                    "name": "Новый год",
                    "date": date(2000, 1, 1),
                    "amount": 500,
                    "days_before": 3,
                    "days_valid": 14,
                },
                {
                    "name": "23 февраля",
                    "date": date(2000, 2, 23),
                    "amount": 500,
                    "days_before": 3,
                    "days_valid": 14,
                },
                {
                    "name": "Сагаалган",
                    # дату можешь потом поправить в БД
                    "date": date(2000, 2, 28),
                    "amount": 500,
                    "days_before": 3,
                    "days_valid": 14,
                },
            ]

            for cfg in defaults:
                stmt = select(HolidayBonus).where(HolidayBonus.name == cfg["name"])
                res = await session.execute(stmt)
                existing = res.scalar_one_or_none()
                if existing:
                    continue

                holiday = HolidayBonus(
                    name=cfg["name"],
                    date=cfg["date"],
                    amount=cfg["amount"],
                    days_before=cfg["days_before"],
                    days_valid=cfg["days_valid"],
                    is_active=True,
                )
                session.add(holiday)

            await session.commit()

        if self.session is None:
            async with AsyncSessionLocal() as s:
                await _impl(s)
        else:
            await _impl(self.session)

    # ------------------------------------------------------------------
    # Основной метод — вызывать для конкретного пользователя
    # ------------------------------------------------------------------
    async def check_and_award_user_bonuses(self, user_id: int):
        """
        Вызываем, когда пользователь открывает баланс/профиль.

        Делает:
        1) Сжигает просроченные праздничные бонусы.
        2) Начисляет бонус ко ДР, если сегодня его день рождения
           и в этом году ещё не начисляли.
        3) Начисляет бонусы по праздникам (holidays), если
           сегодня попадаем в окно:
           [date - days_before; date + days_valid].

        Возвращает список активных праздничных бонусов (для отображения).
        """
        if self.session is None:
            raise RuntimeError(
                "HolidayBonusService(check_and_award_user_bonuses) требует AsyncSession. "
                "Создавай через HolidayBonusService(session)."
            )

        now = datetime.now()

        user = await self.session.get(User, user_id)
        if not user:
            return []

        # 1. Сжигаем просроченные
        await self._expire_old_bonuses(user, now)

        # 2. Бонус ко дню рождения
        await self._check_birthday_bonus(user, now)

        # 3. Календарные праздники из таблицы holidays
        await self._check_calendar_holidays(user, now)

        await self.session.commit()

        # Собираем активные праздничные бонусы
        stmt = select(UserHolidayBonus).where(
            UserHolidayBonus.user_id == user.id,
            UserHolidayBonus.is_active == True,
            UserHolidayBonus.expires_at != None,
            UserHolidayBonus.expires_at > now,
        )
        res = await self.session.execute(stmt)
        bonuses = res.scalars().all()

        return [
            {
                "id": b.id,
                "amount": b.amount,
                "expires_at": b.expires_at,
                "days_left": (b.expires_at - now).days,
                "holiday": b.holiday.name if b.holiday else "День рождения",
            }
            for b in bonuses
        ]

    async def apply_holiday_bonus_spend(self, user_id: int, amount: int) -> int:
        """
        Списывает сумму из активных праздничных бонусов пользователя.
        Возвращает сколько списали из праздничных бонусов.
        """
        if self.session is None:
            raise RuntimeError(
                "HolidayBonusService(apply_holiday_bonus_spend) требует AsyncSession. "
                "Создавай через HolidayBonusService(session)."
            )

        if amount <= 0:
            return 0

        now = datetime.now()

        stmt = (
            select(UserHolidayBonus)
            .where(
                UserHolidayBonus.user_id == user_id,
                UserHolidayBonus.is_active == True,
                UserHolidayBonus.expires_at != None,
                UserHolidayBonus.expires_at > now,
            )
            .order_by(UserHolidayBonus.expires_at)
        )
        res = await self.session.execute(stmt)
        bonuses = res.scalars().all()

        remaining = amount
        used = 0

        for bonus in bonuses:
            if remaining <= 0:
                break

            use_amount = min(remaining, bonus.amount)
            bonus.amount -= use_amount
            remaining -= use_amount
            used += use_amount

            if bonus.amount == 0:
                bonus.is_active = False

        if used > 0:
            await self.session.flush()

        return used

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------
    async def _expire_old_bonuses(self, user: User, now: datetime):
        """Сжигаем просроченные праздничные бонусы и уменьшаем баланс."""
        stmt = select(UserHolidayBonus).where(
            UserHolidayBonus.user_id == user.id,
            UserHolidayBonus.is_active == True,
            UserHolidayBonus.expires_at != None,
            UserHolidayBonus.expires_at <= now,
        )
        res = await self.session.execute(stmt)
        expired = res.scalars().all()

        for b in expired:
            # Списываем, но не даём уйти в минус
            to_sub = min(user.balance, b.amount)
            if to_sub > 0:
                user.balance -= to_sub
                self.session.add(
                    Transaction(
                        user_id=user.id,
                        amount=-to_sub,
                        description=(
                            f"Сгорание праздничного бонуса "
                            f"({b.holiday.name if b.holiday else 'День рождения'})"
                        ),
                    )
                )

            b.is_active = False

    async def _check_birthday_bonus(self, user: User, now: datetime):
        """Бонус ко дню рождения: +500, действует 7 дней."""
        if not user.birth_date:
            return

        today = now.date()
        bd_this_year = date(today.year, user.birth_date.month, user.birth_date.day)

        # Бонус даём в сам день рождения
        if today != bd_this_year:
            return

        year_start = datetime(today.year, 1, 1)
        year_end = datetime(today.year, 12, 31, 23, 59, 59)

        # Проверяем, не выдавали ли уже в этом году
        stmt = select(UserHolidayBonus).where(
            UserHolidayBonus.user_id == user.id,
            UserHolidayBonus.holiday_id == None,  # для ДР holiday_id = NULL
            UserHolidayBonus.created_at >= year_start,
            UserHolidayBonus.created_at <= year_end,
        )
        res = await self.session.execute(stmt)
        if res.scalar_one_or_none():
            return  # уже начисляли

        amount = 500
        expires_at = now + timedelta(days=7)

        user.balance += amount

        bonus = UserHolidayBonus(
            user_id=user.id,
            holiday_id=None,
            amount=amount,
            expires_at=expires_at,
            is_active=True,
        )
        self.session.add(bonus)

        self.session.add(
            Transaction(
                user_id=user.id,
                amount=amount,
                description="Праздничный бонус ко дню рождения",
            )
        )

    async def _check_calendar_holidays(self, user: User, now: datetime):
        """Проверка и начисление по праздникам из holidays."""
        today = now.date()

        stmt = select(HolidayBonus).where(HolidayBonus.is_active == True)
        res = await self.session.execute(stmt)
        holidays = res.scalars().all()

        for holiday in holidays:
            if holiday.date is None:
                # этот праздник не участвует в автоначислении
                continue

            hdate = holiday.get_date_for_year(today.year)
            if hdate is None:
                continue

            days_before = holiday.days_before or 0
            days_valid = holiday.days_valid or 0

            start_give = hdate - timedelta(days=days_before)
            expire_date = hdate + timedelta(days=days_valid)

            # если сегодня не в окне начисления — пропускаем
            if not (start_give <= today <= expire_date):
                continue

            # уже начисляли в этом году этот конкретный праздник?
            year_start = datetime(today.year, 1, 1)
            year_end = datetime(today.year, 12, 31, 23, 59, 59)

            stmt = select(UserHolidayBonus).where(
                UserHolidayBonus.user_id == user.id,
                UserHolidayBonus.holiday_id == holiday.id,
                UserHolidayBonus.created_at >= year_start,
                UserHolidayBonus.created_at <= year_end,
            )
            res = await self.session.execute(stmt)
            if res.scalar_one_or_none():
                continue  # уже есть

            amount = holiday.amount
            user.balance += amount

            bonus = UserHolidayBonus(
                user_id=user.id,
                holiday_id=holiday.id,
                amount=amount,
                expires_at=datetime.combine(expire_date, datetime.min.time()),
                is_active=True,
            )
            self.session.add(bonus)

            self.session.add(
                Transaction(
                    user_id=user.id,
                    amount=amount,
                    description=f"Праздничный бонус: {holiday.name}",
                )
            )
