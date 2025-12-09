# src/database/__init__.py
from .base import Base
from .session import AsyncSessionLocal, engine, get_session, get_db

# Экспортируем все необходимое
__all__ = [
    'Base',
    'AsyncSessionLocal',
    'engine',
    'get_session',
    'get_db'
]


# Функции для работы с БД
async def create_tables():
    """Создать все таблицы"""
    from src.models.user import User
    from src.models.transaction import Transaction
    from src.models.admin_action import AdminAction

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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