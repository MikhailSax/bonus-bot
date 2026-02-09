# src/database/session.py
import os
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# Используем SQLite
DATABASE_URL = "sqlite+aiosqlite:///./bonus_bot.db"

def _parse_bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


SQLALCHEMY_ECHO = _parse_bool(os.getenv("SQLALCHEMY_ECHO"))

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=SQLALCHEMY_ECHO,
    connect_args={"check_same_thread": False}
)

# Фабрика сессий
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)


async def get_session() -> AsyncSession:
    """Dependency для получения сессии"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db():
    """Async context manager для работы с БД"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
