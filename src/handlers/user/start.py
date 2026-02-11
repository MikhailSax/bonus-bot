# src/handlers/user/start.py

from pathlib import Path
from datetime import datetime

from aiogram import Router, F
from aiogram.types import (
    Message,
    KeyboardButton,
    ReplyKeyboardMarkup,
    FSInputFile,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.exceptions import TelegramBadRequest

from src.services.user_service import UserService
from src.keyboards.user_kb import get_user_main_menu

router = Router()

# ==============================
#  FSM регистрации
# ==============================

class RegistrationFSM(StatesGroup):
    full_name = State()
    birth_date = State()
    phone = State()


# ==============================
#  НАСТРОЙКИ ПРИВЕТСТВИЯ
# ==============================

BASE_DIR = Path(__file__).resolve().parent.parent.parent
WELCOME_IMAGE_PATH = BASE_DIR / "img" / "welcome_image.jpg"

WELCOME_TEXT = (
    "Привет! 👋\n"
    "С вами команда *Prime Store* и мы приглашаем вас "
    "зарегистрироваться в нашей системе лояльности для накопления бонусов.\n\n"
    "Сначала заполним анкету (ФИО и дата рождения), а потом вы отправите номер телефона."
)

PD_AGREEMENT_TEXT = (
    "Отправляя свои персональные данные, вы подтверждаете согласие на их обработку "
    "командой *Prime Store* в целях участия в программе лояльности."

)

AFTER_REGISTER_TEXT = (
    "Поздравляем! 🎉\n"
    "вы стали участником нашей программы лояльности — за это дарим "
    "*200 приветственных бонусов*.\n\n"
    "Как работает программа:\n"
    "• начисляем 5% с каждой покупки;\n"
    "• можно списывать до 30% от суммы чека бонусами;\n"
    "• в день рождения начисляем 500 бонусов на неделю — потом они сгорают;\n"
    "• на праздники 23 февраля, Новый год и Сагаалган начисляем по 500 бонусов — "
    "они действуют две недели и начисляются за 3 дня до праздника. \n"
    "А также необходимо подписаться на наш телеграмм-канал https://t.me/primestoreuu \n"
)


def get_request_phone_kb() -> ReplyKeyboardMarkup:
    """Клава с кнопкой отправки номера на финальном шаге"""
    return ReplyKeyboardMarkup(
        resize_keyboard=True,
        keyboard=[
            [KeyboardButton(text="📱 Отправить номер", request_contact=True)]
        ]
    )


# ==============================
#   /start
# ==============================

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session):
    """
    Новый пользователь:
      1) приветствие (картинка + текст + ПД),
      2) ставим state = full_name и просим ФИО.
    Зарегистрированный — сразу меню.
    """
    user_service = UserService(session)
    tg_id = message.from_user.id

    user = await user_service.get_user_by_tg_id(tg_id)

    if user:
        await state.clear()
        await message.answer(
            "👋 Вы уже зарегистрированы!",
            reply_markup=get_user_main_menu()
        )
        return

    await state.clear()
    await state.set_state(RegistrationFSM.full_name)

    # Приветствие с картинкой
    if WELCOME_IMAGE_PATH.exists():
        try:
            photo = FSInputFile(WELCOME_IMAGE_PATH)
            await message.answer_photo(
                photo=photo,
                caption=WELCOME_TEXT,
                parse_mode="Markdown",
            )
        except TelegramBadRequest:
            await message.answer(WELCOME_TEXT, parse_mode="Markdown")
    else:
        await message.answer(WELCOME_TEXT, parse_mode="Markdown")

    # Согласие на ПД
    await message.answer(PD_AGREEMENT_TEXT, parse_mode="Markdown")

    # Просим ФИО
    await message.answer(
        "Для начала напишите, пожалуйста, *ФИО полностью* (пример: Иванов Иван Иванович):",
        parse_mode="Markdown",
    )


# ==============================
#   Шаг 1: ФИО
# ==============================

@router.message(RegistrationFSM.full_name)
async def reg_full_name(message: Message, state: FSMContext):
    full_name = message.text.strip()

    if not full_name or len(full_name.split()) < 2:
        await message.answer(
            "Пожалуйста, введите ФИО полностью (минимум фамилия и имя)."
        )
        return

    # Разбираем ФИО на first_name / last_name
    parts = full_name.split()
    if len(parts) == 2:
        last_name, first_name = parts
    else:
        last_name = parts[0]
        first_name = " ".join(parts[1:])

    await state.update_data(
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
    )
    await state.set_state(RegistrationFSM.birth_date)

    await message.answer(
        "Отлично! Теперь введите *дату рождения* в формате ДД.ММ.ГГГГ\n"
        "Например: `05.12.1998`",
        parse_mode="Markdown",
    )


# ==============================
#   Шаг 2: дата рождения
# ==============================

@router.message(RegistrationFSM.birth_date)
async def reg_birth_date(message: Message, state: FSMContext):
    text = message.text.strip()

    try:
        birth_date = datetime.strptime(text, "%d.%m.%Y").date()
    except ValueError:
        await message.answer(
            "❗ Неверный формат даты.\n"
            "Пожалуйста, введите в формате ДД.ММ.ГГГГ, например: 05.12.1998"
        )
        return

    await state.update_data(birth_date=birth_date)
    await state.set_state(RegistrationFSM.phone)

    await message.answer(
        "Спасибо! Остался последний шаг.\n\n"
        "Отправьте, пожалуйста, *номер телефона* через кнопку ниже "
        "или введите его вручную в формате `+79991112233`.",
        parse_mode="Markdown",
        reply_markup=get_request_phone_kb(),
    )


# ==============================
#   Шаг 3: телефон — через контакт
# ==============================

@router.message(RegistrationFSM.phone, F.contact)
async def reg_phone_contact(message: Message, state: FSMContext, session):
    if not message.contact:
        await message.answer("❗ Пожалуйста, отправь номер через кнопку или текстом.")
        return

    phone = message.contact.phone_number
    await finish_registration(message, state, session, phone)


# ==============================
#   Шаг 3: телефон — вручную
# ==============================

@router.message(RegistrationFSM.phone, F.text.regexp(r'^\+?\d{10,15}$'))
async def reg_phone_text(message: Message, state: FSMContext, session):
    phone = message.text.strip()
    await finish_registration(message, state, session, phone)


# ==============================
#   Завершение регистрации
# ==============================

async def finish_registration(
    message: Message,
    state: FSMContext,
    session,
    phone: str,
):
    data = await state.get_data()

    first_name = data.get("first_name")
    last_name = data.get("last_name")
    birth_date = data.get("birth_date")

    user_service = UserService(session)
    tg_user = message.from_user

    # создаём пользователя только здесь, в конце
    user, created = await user_service.get_or_create_user(
        tg_id=tg_user.id,
        username=tg_user.username,
        first_name=first_name,
        last_name=last_name,
        birth_date=birth_date,
        phone=phone,
    )

    await state.clear()

    await message.answer(
        AFTER_REGISTER_TEXT,
        parse_mode="Markdown",
        reply_markup=get_user_main_menu(),
    )

