# src/database/__init__.py
from sqlalchemy import inspect, text

from .base import Base
from .session import AsyncSessionLocal, engine, get_session, get_db

# Экспортируем все необходимое
__all__ = [
    'Base',
    'AsyncSessionLocal',
    'engine',
    'get_session',
    'get_db',
    'create_tables',
    'ensure_schema',
]


# Функции для работы с БД
def _ensure_user_columns(sync_conn):
    inspector = inspect(sync_conn)
    if "users" not in inspector.get_table_names():
        return

    columns = {col["name"] for col in inspector.get_columns("users")}
    if "holiday_balance" not in columns:
        sync_conn.execute(
            text(
                "ALTER TABLE users "
                "ADD COLUMN holiday_balance INTEGER DEFAULT 0"
            )
        )


async def ensure_schema():
    """Проверить и обновить схему без миграций (SQLite)."""
    from src.models.user import User
    from src.models.transaction import Transaction
    from src.models.admin_action import AdminAction
    from src.models.holiday_bonus import HolidayBonus, UserHolidayBonus

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_user_columns)
        await conn.execute(
            text(
                "UPDATE users "
                "SET holiday_balance = 0 "
                "WHERE holiday_balance IS NULL"
            )
        )


async def create_tables():
    """Создать все таблицы и обновить схему."""
    from src.models.user import User
    from src.models.transaction import Transaction
    from src.models.admin_action import AdminAction

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.run_sync(_ensure_user_columns)
        await conn.execute(
            text(
                "UPDATE users "
                "SET holiday_balance = 0 "
                "WHERE holiday_balance IS NULL"
            )
        )
    print("✅ Таблицы созданы в SQLite!")


async def check_connection():
    """Проверить подключение"""
    try:
        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        print("✅ Подключение к SQLite успешно!")
        return True
    except Exception as e:
        print(f"❌ Ошибка подключения: {e}")
        return False
