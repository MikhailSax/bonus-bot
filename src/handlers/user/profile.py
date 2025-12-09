# src/handlers/user/profile.py

from io import BytesIO

import qrcode
from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from src.models.user import User
from src.services.user_service import UserService
from src.keyboards.user_kb import get_user_main_menu, get_back_to_menu

router = Router()


# =========================
#  Мой профиль
# =========================
@router.message(F.text == "👤 Мой профиль")
async def user_profile(message: Message, session):
    """
    Показывает профиль пользователя.
    session приходит из DBSessionMiddleware (data["session"])
    """
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "❌ Вы ещё не зарегистрированы. Нажмите /start",
                reply_markup=get_user_main_menu(),
            )
            return

        # обновляем праздничные бонусы (ДР, праздники, сгорание)
        user_service = UserService(session)
        await user_service.check_and_award_holiday_bonuses(user.id)
        await session.refresh(user)

        phone = getattr(user, "phone", None) or "-"
        birth_date = getattr(user, "birth_date", None)
        if birth_date:
            birth_str = birth_date.strftime("%d.%m.%Y")
        else:
            birth_str = "-"

        age_str = "-"
        # если у модели User есть метод age() — используем
        if hasattr(user, "age"):
            try:
                age_val = user.age()
                if age_val is not None:
                    age_str = f"{age_val} лет"
            except Exception:
                pass

        balance = getattr(user, "balance", 0)

    except SQLAlchemyError:
        await message.answer(
            "❌ Ошибка обращения к базе. Сообщите администратору.",
            reply_markup=get_back_to_menu(),
        )
        return

    text = (
        "👤 *Ваш профиль*\n\n"
        f"ID: `{user.id}`\n"
        f"Имя: {user.first_name or ''} {user.last_name or ''}\n"
        f"Телефон: {phone}\n"
        f"Дата рождения: {birth_str}\n"
        f"Возраст: {age_str}\n"
        f"Баланс: *{balance}* бонусов\n"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=get_back_to_menu(),
    )


# =========================
#  Показать QR-код
# =========================
@router.message(F.text == "📱 Показать QR-код")
async def user_qr(message: Message, session):
    """
    Генерирует и отправляет QR-код пользователя.
    """
    try:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "❌ Вы ещё не зарегистрированы. Нажмите /start",
                reply_markup=get_user_main_menu(),
            )
            return

        # строка, которую шифруем в QR
        qr_data = f"user:{user.telegram_id}"   # <<< вот так

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(qr_data)
        qr.make(fit=True)


        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)

        photo = BufferedInputFile(
            buffer.getvalue(),
            filename=f"user_{user.id}_qr.png",
        )

    except SQLAlchemyError:
        await message.answer(
            "❌ Ошибка обращения к базе. Сообщите администратору.",
            reply_markup=get_back_to_menu(),
        )
        return

    await message.answer_photo(
        photo=photo,
        caption="Покажите этот QR-код на кассе для начисления или списания бонусов.",
        reply_markup=get_back_to_menu(),
    )
