from aiogram import Router
from aiogram.types import ErrorEvent
import logging

router = Router()
logger = logging.getLogger(__name__)


@router.error()
async def error_handler(event: ErrorEvent):
    """Глобальный обработчик ошибок"""
    logger.error(
        f"Update: {event.update}\n"
        f"Exception: {event.exception}\n"
        f"Traceback: {event.exception.__traceback__}",
        exc_info=True
    )

    # Можно добавить отправку ошибок админам
    # или запись в отдельный лог-файл

    return True  # Подавляем ошибку, чтобы бот не падал