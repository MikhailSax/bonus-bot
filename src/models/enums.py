# src/models/enums.py
from enum import Enum


class OperationType(Enum):
    """Типы операций с бонусами"""
    REGISTRATION = "registration"  # Регистрация
    PURCHASE = "purchase"  # За покупку
    REVIEW = "review"  # За отзыв
    REFERRAL = "referral"  # За реферала
    ADMIN_ADD = "admin_add"  # Админ добавил
    ADMIN_SUBTRACT = "admin_subtract"  # Админ убрал
    SPENDING = "spending"  # Потратил бонусы
    BONUS = "bonus"  # Бонусные начисления
    CORRECTION = "correction"  # Корректировка


class UserRole(Enum):
    """Роли пользователей"""
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"