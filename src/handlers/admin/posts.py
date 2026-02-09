# src/handlers/admin/posts.py

import asyncio
from io import BytesIO
from typing import Literal

from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from sqlalchemy import select

from src.database import AsyncSessionLocal
from src.models.user import User
from src.keyboards.admin_kb import admin_back_kb, admin_main_menu_kb

router = Router()


class AdminPostFSM(StatesGroup):
    text = State()
    media = State()


FileSource = str | tuple[bytes, str]


def _build_input_file(file_source: FileSource) -> str | BufferedInputFile:
    if isinstance(file_source, tuple):
        file_bytes, filename = file_source
        return BufferedInputFile(file_bytes, filename=filename)
    return file_source


async def _send_post_media(
    bot,
    tg_id: int,
    media_type: Literal["photo", "video", "animation", "document"],
    file_source: FileSource,
    text: str,
) -> bool:
    try:
        input_file = _build_input_file(file_source)
        if media_type == "photo":
            await bot.send_photo(tg_id, input_file, caption=text)
        elif media_type == "video":
            await bot.send_video(tg_id, input_file, caption=text)
        elif media_type == "animation":
            await bot.send_animation(tg_id, input_file, caption=text)
        else:
            await bot.send_document(tg_id, input_file, caption=text)
        return True
    except (TelegramForbiddenError, TelegramBadRequest):
        return False


async def _broadcast_post(
    bot,
    chat_id: int,
    users: list[int],
    media_type: Literal["photo", "video", "animation", "document"],
    file_source: FileSource,
    text: str,
):
    semaphore = asyncio.Semaphore(20)

    async def _guarded_send(tg_id: int) -> bool:
        async with semaphore:
            return await _send_post_media(bot, tg_id, media_type, file_source, text)

    results = await asyncio.gather(
        *(_guarded_send(tg_id) for tg_id in users),
        return_exceptions=False,
    )

    sent = sum(1 for ok in results if ok)
    failed = len(results) - sent

    await bot.send_message(
        chat_id,
        "✅ Пост разослан!\n"
        f"Отправлено: {sent}\n"
        f"Ошибки: {failed}",
        reply_markup=admin_main_menu_kb(),
    )


@router.callback_query(F.data == "admin_post_create")
async def admin_post_create(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        return await callback.answer("⛔ У вас нет доступа!", show_alert=True)

    await state.clear()
    await state.set_state(AdminPostFSM.text)
    await callback.message.edit_text(
        "📝 Введите текст поста:",
        reply_markup=admin_back_kb("admin_post_cancel"),
    )
    await callback.answer()


@router.callback_query(F.data == "admin_post_cancel")
async def admin_post_cancel(callback: CallbackQuery, state: FSMContext, is_admin: bool):
    if not is_admin:
        return await callback.answer("⛔ У вас нет доступа!", show_alert=True)

    await state.clear()
    await callback.message.edit_text("⚙ Админ-панель", reply_markup=admin_main_menu_kb())
    await callback.answer()


@router.message(AdminPostFSM.text)
async def admin_post_text(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await state.clear()
        return await message.answer("⛔ У вас нет доступа!")

    if not message.text or not message.text.strip():
        return await message.answer("Введите текст поста.")

    await state.update_data(text=message.text.strip())
    await state.set_state(AdminPostFSM.media)
    await message.answer(
        "📎 Теперь отправьте фото или медиафайл для поста (фото/видео лучше отправлять не как файл):",
        reply_markup=admin_back_kb("admin_post_cancel"),
    )


@router.message(AdminPostFSM.media)
async def admin_post_media(message: Message, state: FSMContext, is_admin: bool):
    if not is_admin:
        await state.clear()
        return await message.answer("⛔ У вас нет доступа!")

    data = await state.get_data()
    text = data.get("text")
    if not text:
        await state.clear()
        return await message.answer("Текст поста не найден. Попробуйте снова.")

    media_type = None
    file_source = None

    if message.photo:
        media_type = "photo"
        file_source = message.photo[-1].file_id
    elif message.video:
        media_type = "video"
        file_source = message.video.file_id
    elif message.animation:
        media_type = "animation"
        file_source = message.animation.file_id
    elif message.document:
        mime_type = message.document.mime_type or ""
        if mime_type.startswith("image/"):
            media_type = "animation" if mime_type == "image/gif" else "photo"
        elif mime_type.startswith("video/"):
            media_type = "video"
        else:
            media_type = "document"

        if media_type == "document":
            file_source = message.document.file_id
        else:
            bio = BytesIO()
            await message.bot.download(message.document, destination=bio)
            file_source = (
                bio.getvalue(),
                message.document.file_name or "media",
            )

    if not file_source:
        return await message.answer("Отправьте фото или медиафайл (видео/гиф/документ).")

    async with AsyncSessionLocal() as session:
        users = (await session.execute(select(User.telegram_id))).scalars().all()

    await state.clear()
    await message.answer("📤 Рассылка запущена, результат придет отдельным сообщением.")

    asyncio.create_task(
        _broadcast_post(
            message.bot,
            message.chat.id,
            users,
            media_type,
            file_source,
            text,
        )
    )
