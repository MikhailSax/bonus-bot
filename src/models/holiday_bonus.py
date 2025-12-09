# src/models/holiday_bonus.py

from datetime import date as date_type
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from src.database import Base


class HolidayBonus(Base):
    """
    Таблица с описанием праздников.

    Под имеющуюся БД поля ожидаются такие:
    id | name | date | amount | days_before | days_valid | is_active
    """

    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    # дата праздника (год не важен, важны месяц/день; можно 2000)
    date = Column(Date, nullable=True)

    # сколько бонусов начислять
    amount = Column(Integer, nullable=False, default=0)

    # за сколько дней до праздника начать начислять
    days_before = Column(Integer, nullable=True, default=0)

    # сколько дней бонус считается "праздничным" после даты
    days_valid = Column(Integer, nullable=True, default=14)

    is_active = Column(Boolean, nullable=False, default=True)

    user_bonuses = relationship(
        "UserHolidayBonus",
        back_populates="holiday",
        cascade="all, delete-orphan",
    )

    def get_date_for_year(self, year: int) -> date_type | None:
        """Вернуть дату этого праздника для конкретного года."""
        if self.date is None:
            return None
        return date_type(year, self.date.month, self.date.day)


class UserHolidayBonus(Base):
    """
    Конкретный праздничный бонус пользователя.

    Таблица: user_holiday_bonuses

    user_id    — кому выдали
    holiday_id — от какого праздника (может быть NULL, напр. для ДР)
    amount     — сколько выдали
    created_at — когда выдали
    expires_at — когда сгорит
    is_active  — активен ли ещё
    """

    __tablename__ = "user_holiday_bonuses"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    holiday_id = Column(
        Integer,
        ForeignKey("holidays.id", ondelete="SET NULL"),
        nullable=True,
    )

    amount = Column(Integer, nullable=False)

    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True)

    # связи
    user = relationship("User", back_populates="holiday_bonuses")
    holiday = relationship("HolidayBonus", back_populates="user_bonuses")
