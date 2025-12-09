from typing import Any, Optional
from datetime import datetime


def format_datetime(dt: datetime, format_str: str = "%d.%m.%Y %H:%M") -> str:
    """Форматирование даты и времени"""
    return dt.strftime(format_str) if dt else "Не указано"


def format_balance(amount: int) -> str:
    """Форматирование суммы бонусов"""
    return f"{amount:,}".replace(",", " ")


def safe_get(obj: Any, attr: str, default: Any = None) -> Any:
    """Безопасное получение атрибута"""
    try:
        return getattr(obj, attr, default)
    except (AttributeError, TypeError):
        return default


def truncate_text(text: str, max_length: int = 100) -> str:
    """Обрезать текст до максимальной длины"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."