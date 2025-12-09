# middleware/admin_middleware.py
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from src.database import AsyncSessionLocal
from sqlalchemy import select
from src.models.user import User


class AdminMiddleware(BaseMiddleware):
    """Middleware для проверки прав администратора"""

    async def __call__(
            self,
            handler: Callable,
            event: Message | CallbackQuery,
            data: Dict[str, Any]
    ) -> Any:
        # ВСЕГДА проверяем права для любого сообщения/колбэка
        user_id = event.from_user.id

        # Проверяем права администратора
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user and user.role == "admin":
                # Ключевой момент: добавляем is_admin в data
                data["is_admin"] = True
                data["admin_user"] = user
            else:
                data["is_admin"] = False
                data["admin_user"] = None

        # Если команда /admin и не админ - блокируем
        if isinstance(event, Message) and event.text and event.text.startswith('/admin'):
            if not data.get("is_admin"):
                await event.answer("⛔ У вас нет доступа к админ-панели!")
                return None

        # Для админских колбэков проверяем права
        if isinstance(event, CallbackQuery):
            callback_data = event.data or ""
            # Список всех админских колбэков
            admin_callbacks = [
                'admin_', 'add_bonus_', 'subtract_', 'search_',
                'phone_', 'change_', 'history_'
            ]

            is_admin_callback = any(callback_data.startswith(prefix) for prefix in admin_callbacks)

            if is_admin_callback and not data.get("is_admin"):
                await event.answer("⛔ Нет доступа!", show_alert=True)
                return None

        # Продолжаем обработку
        return await handler(event, data)