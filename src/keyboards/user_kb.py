from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder


def get_user_main_menu() -> ReplyKeyboardMarkup:
    """Главное меню пользователя"""
    builder = ReplyKeyboardBuilder()

    builder.add(
        KeyboardButton(text="👤 Мой профиль"),
        KeyboardButton(text="💰 Мой баланс"),
        KeyboardButton(text="📊 История операций"),
        KeyboardButton(text="📱 Показать QR-код"),
    )

    builder.adjust(2, 2)

    return builder.as_markup(resize_keyboard=True)


def get_back_to_menu() -> ReplyKeyboardMarkup:
    """Кнопка возврата в главное меню"""
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="⬅️ Назад в меню"))
    return builder.as_markup(resize_keyboard=True)
