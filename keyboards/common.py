from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from utils.helpers import is_manager

def get_main_keyboard(user_id: int = None):
    builder = InlineKeyboardBuilder()
    builder.button(text="🏢 Мои компании", callback_data="menu_companies")
    builder.button(text="🎁 Текущие акции", callback_data="menu_banners")
    builder.button(text="🎁 Реферальная программа", callback_data="menu_bonus")
    if user_id and is_manager(user_id):
        builder.button(text="👥 Акции контрагента", callback_data="menu_partner")
    builder.button(text="ℹ️ Помощь", callback_data="menu_help")
    builder.adjust(1)
    return builder.as_markup()

def get_bonus_submenu_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Баланс баллов", callback_data="bonus_balance")
    builder.button(text="📜 История баллов", callback_data="bonus_history")
    builder.button(text="◀️ Назад в главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_phone_keyboard():
    button = KeyboardButton(text="📱 Поделиться номером", request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)

def get_back_to_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В главное меню", callback_data="back_to_main")
    return builder.as_markup()
