import asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
import soap_client
from keyboards.common import get_main_keyboard
from states import states
import logging

router = Router()
logger = logging.getLogger(__name__)

async def show_main_menu(chat_id: int, user_id: int, bot):
    await bot.send_message(chat_id, "Главное меню:", reply_markup=get_main_keyboard(user_id))

async def get_companies_keyboard(user_id: int, action: str, bot=None):
    """Возвращает инлайн-клавиатуру со списком компаний для выбранного действия."""
    companies = db.get_user_companies(user_id)
    if not companies:
        return None, "У вас нет выбранных компаний. Сначала выберите компании в разделе «Мои компании»."
    builder = InlineKeyboardBuilder()
    for comp in companies:
        builder.button(text=comp['name'], callback_data=f"{action}_comp_{comp['code']}")
    builder.button(text="🔄 Обновить список", callback_data=f"refresh_companies_{action}")
    builder.button(text="◀️ Отмена", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup(), None

@router.callback_query(lambda c: c.data.startswith('refresh_companies_'))
async def refresh_companies_list(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[2]  # balance, history, banners
    user_id = callback.from_user.id
    phone = db.get_user_phone(user_id)
    if not phone:
        await callback.answer("Номер телефона не найден. Пожалуйста, начните с /start в личном чате.")
        return
    await callback.message.edit_text("🔄 Обновляем список компаний...")
    companies = await soap_client.get_companies_by_phone(phone)
    if not companies:
        await callback.message.edit_text("❌ Не удалось загрузить компании. Попробуйте позже.")
        return
    db.save_user_companies(user_id, companies)
    keyboard, error = await get_companies_keyboard(user_id, action, callback.bot)
    if error:
        await callback.message.edit_text(error)
    else:
        await callback.message.edit_text("✅ Список компаний обновлён. Выберите компанию:", reply_markup=keyboard)
    await callback.answer()

async def process_companies_loading(user_id: int, phone: str, state: FSMContext, message: types.Message, reply_chat_id: int):
    await message.bot.send_message(reply_chat_id, "⏳ Загружаем список компаний...")
    companies = await soap_client.get_companies_by_phone(phone)
    if not companies:
        await message.bot.send_message(reply_chat_id, "❌ Не удалось загрузить компании. Попробуйте позже.")
        await state.clear()
        await show_main_menu(reply_chat_id, user_id, message.bot)
        return
    db.save_user_companies(user_id, companies)
    await message.bot.send_message(reply_chat_id, "✅ Список компаний загружен. Теперь вы можете использовать все функции.")

@router.message(F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    contact = message.contact
    phone = contact.phone_number
    db.update_user_phone(user_id, phone)
    db.mark_user_verified(user_id)
    current_state = await state.get_state()
    if current_state == states.CompanyProcess.waiting_for_phone.state:
        await message.answer("✅ Номер подтверждён. Загружаем информацию...", reply_markup=types.ReplyKeyboardRemove())
        await process_companies_loading(user_id, phone, state, message, message.chat.id)
    else:
        await message.answer("✅ Номер подтверждён.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await show_main_menu(message.chat.id, user_id, message.bot)