import asyncio
from io import BytesIO

import numpy as np
import cv2
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.user import User
from src.keyboards.admin_kb import admin_user_actions_kb
from src.handlers.admin.posts import AdminPostFSM

router = Router()


def _decode_qr_code(image_bytes: bytes) -> str | None:
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if img is None:
        return None

    detector = cv2.QRCodeDetector()
    data, _, _ = detector.detectAndDecode(img)
    return data or None


@router.message(F.photo | F.document)
async def scan_qr_code(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state in {AdminPostFSM.text.state, AdminPostFSM.media.state}:
        return

    # --- проверяем, что это админ ---
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == message.from_user.id)
        )
        admin = result.scalar_one_or_none()

    if not admin or admin.role != "admin":
        return  # игнорируем, если не админ

    if message.photo:
        file = message.photo[-1]
    elif (
        message.document
        and message.document.mime_type
        and message.document.mime_type.startswith("image/")
    ):
        file = message.document
    else:
        await message.answer("📷 Пришлите изображение с QR-кодом.")
        return

    bio = BytesIO()
    await message.bot.download(file, destination=bio)
    image_bytes = bio.getvalue()

    data = await asyncio.to_thread(_decode_qr_code, image_bytes)

    if not data:
        await message.answer("📷 QR-код не найден на фото")
        return

    # ожидаем формат user:<telegram_id>
    if not data.startswith("user:"):
        await message.answer("⚠ QR-код не является кодом пользователя")
        return

    try:
        tg_id = int(data.split(":", 1)[1])
    except ValueError:
        await message.answer("❌ Некорректные данные в QR-коде")
        return

    # --- ищем пользователя ---
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == tg_id)
        )
        user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден в базе")
        return

    text = (
        f"👤 *Пользователь найден!*\n\n"
        f"ID: {user.id}\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Имя: {user.first_name} {user.last_name or ''}\n"
        f"Телефон: {user.phone or '-'}\n"
        f"Баланс: {user.balance}\n"
    )

    await message.answer(
        text,
        parse_mode="Markdown",
        reply_markup=admin_user_actions_kb(user.id),
    )
