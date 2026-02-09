# src/main.py
import asyncio
import logging
import os
from typing import Dict, Any

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message
from aiogram.filters import Command
from dotenv import load_dotenv

from sqlalchemy import select

# --- DATABASE ---
from src.database import AsyncSessionLocal, create_tables

# --- MODELS ---
from src.models.user import User

# --- USER ROUTERS ---
from src.handlers.user.start import router as user_start_router
from src.handlers.user.balance import router as user_balance_router
from src.handlers.user.profile import router as user_profile_router

# --- ADMIN ROUTERS ---
from src.handlers.admin.panel import router as admin_panel_router
from src.handlers.admin.commands import router as admin_commands_router
from src.handlers.admin.users import router as admin_users_router
from src.handlers.admin.bonuses import router as admin_bonuses_router
from src.handlers.admin.holidays import router as admin_holidays_router
from src.handlers.admin.qr_scan import router as admin_qr_router
from src.handlers.admin.stats import router as admin_stats_router
from src.handlers.admin.posts import router as admin_posts_router

# --- SERVICES ---
from src.services.holiday_bonus_service import HolidayBonusService


load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bonus_bot")


# ----------------------------------------------------------
# DB SESSION MIDDLEWARE
# ----------------------------------------------------------
class DBSessionMiddleware(BaseMiddleware):
    """Передаёт session каждому хендлеру через data['session']"""

    async def __call__(self, handler, event, data):
        async with AsyncSessionLocal() as session:
            data["session"] = session
            return await handler(event, data)


# ----------------------------------------------------------
# ADMIN MIDDLEWARE
# ----------------------------------------------------------
class AdminMiddleware(BaseMiddleware):
    """Проверка прав администратора"""

    async def __call__(self, handler, event, data: Dict[str, Any]):
        if not hasattr(event, "from_user"):
            return await handler(event, data)

        user_id = event.from_user.id

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == user_id)
            )
            db_user = result.scalar_one_or_none()

            is_admin = bool(db_user and db_user.role == "admin")

            data["is_admin"] = is_admin
            data["admin_user"] = db_user if is_admin else None

        # запрет на доступ к админ-командам
        if isinstance(event, Message):
            if event.text and event.text.startswith("/admin") and not is_admin:
                await event.answer("⛔ У вас нет доступа!")
                return

        return await handler(event, data)


# ----------------------------------------------------------
# DATABASE INIT
# ----------------------------------------------------------
async def init_database():
    logger.info("🔄 Создание таблиц...")
    await create_tables()
    logger.info("✅ Таблицы готовы!")


# ----------------------------------------------------------
# HOLIDAY INIT
# ----------------------------------------------------------
async def init_holidays():
    try:
        holiday_service = HolidayBonusService()
        await holiday_service.initialize_default_holidays()
        logger.info("🎉 Праздники загружены!")
    except Exception as e:
        logger.warning(f"⚠ Не удалось загрузить праздники: {e}")


# ----------------------------------------------------------
# MAIN
# ----------------------------------------------------------
async def main():
    if not TOKEN:
        logger.error("❌ BOT_TOKEN отсутствует в .env файле")
        exit(1)

    # init DB tables
    await init_database()

    # init holidays
    await init_holidays()

    bot = Bot(TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    bot_info = await bot.get_me()
    logger.info(f"🤖 Запущен бот @{bot_info.username}")

    # Middleware
    db_mw = DBSessionMiddleware()
    admin_mw = AdminMiddleware()

    # Подключение Middleware строго в таком порядке
    dp.update.middleware(db_mw)
    dp.message.middleware(db_mw)
    dp.callback_query.middleware(db_mw)

    dp.message.middleware(admin_mw)
    dp.callback_query.middleware(admin_mw)

    # Routers — пользовательские
    dp.include_router(user_start_router)
    dp.include_router(user_balance_router)
    dp.include_router(user_profile_router)

    # Routers — админские
    dp.include_router(admin_commands_router)
    dp.include_router(admin_panel_router)
    dp.include_router(admin_users_router)
    dp.include_router(admin_bonuses_router)
    dp.include_router(admin_holidays_router)
    dp.include_router(admin_qr_router)
    dp.include_router(admin_stats_router)
    dp.include_router(admin_posts_router)

    # Start polling
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("🚀 Polling zapushchen.")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("🧹 Сессия закрыта.")


if __name__ == "__main__":
    asyncio.run(main())
