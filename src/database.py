# src/models/user.py

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from src.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=True)
    first_name = Column(String(100))
    last_name = Column(String(100), nullable=True)

    # Дата рождения
    birth_date = Column(Date, nullable=True)

    # Контакты
    phone = Column(String(20), nullable=True, index=True)

    # Роль
    role = Column(String(20), default="user")
    is_active = Column(Boolean, default=True)

    # Баланс
    balance = Column(Integer, default=0)

    # Таймстемпы
    last_activity = Column(DateTime, server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # 🔥 КАСКАДНОЕ УДАЛЕНИЕ ВСЕХ ТРАНЗАКЦИЙ ПОЛЬЗОВАТЕЛЯ
    transactions = relationship(
        "Transaction",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True     # <- критично важно, запрещает SQLAlchemy делать UPDATE user_id=NULL
    )

    # 🔥 Праздничные бонусы (также удаляются вместе с пользователем)
    holiday_bonuses = relationship(
        "UserHolidayBonus",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True
    )

    def __repr__(self):
        return f"<User {self.telegram_id} ({self.first_name}) balance={self.balance}>"

    # ----- Форматирование -----

    @property
    def formatted_phone(self):
        """Человекочитаемый формат номера телефона"""
        if not self.phone:
            return None
        digits = ''.join(filter(str.isdigit, self.phone))
        if len(digits) == 11 and digits.startswith('7'):
            return f"+7 ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:]}"
        elif len(digits) == 10:
            return f"+7 ({digits[0:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}"
        return self.phone

    @property
    def formatted_birth_date(self):
        """Дата рождения в формате ДД.ММ.ГГГГ"""
        if not self.birth_date:
            return None
        return self.birth_date.strftime("%d.%m.%Y")

    @property
    def age(self):
        """Возраст пользователя"""
        if not self.birth_date:
            return None

        from datetime import date
        today = date.today()

        age = today.year - self.birth_date.year
        if (today.month, today.day) < (self.birth_date.month, self.birth_date.day):
            age -= 1
        return age
