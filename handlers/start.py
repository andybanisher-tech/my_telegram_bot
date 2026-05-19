from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
from keyboards.common import get_main_keyboard

router = Router()

WELCOME_TEXT = (
    "Здравствуйте! 👋\n\n"
    "Я — бот компании Сталкер-Консалтинг (https://stalker-co.ru), "
    "надёжного B2B-дистрибьютора профессиональных товаров для индустрии красоты в России.\n\n"
    "С моей помощью вы можете:\n"
    "• 🏢 просматривать список привязанных компаний\n"
    "• 🎁 следить за актуальными акциями\n"
    "• 💰 проверять баланс и историю бонусных баллов\n"
    "• 🎁 участвовать в реферальной программе\n\n"
    "Нажимая «Начать», вы соглашаетесь с политикой конфиденциальности: https://stalker-co.ru/policy/"
)

def get_welcome_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Начать", callback_data="welcome_accept")
    return builder.as_markup()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user

    if not db.has_accepted_welcome(user.id):
        await message.answer(
            WELCOME_TEXT,
            reply_markup=get_welcome_keyboard(),
            disable_web_page_preview=True
        )
        return

    await message.answer("👋 С возвращением!", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Выбери действие:", reply_markup=get_main_keyboard(user.id))

@router.callback_query(lambda c: c.data == "welcome_accept")
async def welcome_accept(callback: types.CallbackQuery, state: FSMContext):
    user = callback.from_user
    db.accept_welcome(user.id, user.username, user.first_name)
    await callback.message.edit_text("✅ Добро пожаловать!", reply_markup=None)
    await callback.bot.send_message(
        callback.message.chat.id,
        "Выбери действие:",
        reply_markup=get_main_keyboard(user.id)
    )
    await callback.answer()
