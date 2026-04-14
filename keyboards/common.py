from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from utils.helpers import is_manager

def get_main_keyboard(user_id: int = None):
    """Главное меню (без подписок)."""
    buttons = [
        [KeyboardButton(text="🏢 Мои компании")],
        [KeyboardButton(text="🎁 Текущие акции")],
        [KeyboardButton(text="🎁 Реферальная программа")],
    ]
    if user_id and is_manager(user_id):
        buttons.append([KeyboardButton(text="👥 Акции контрагента")])
    buttons.append([KeyboardButton(text="ℹ️ Помощь")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def get_bonus_submenu_keyboard():
    kb = [
        [KeyboardButton(text="💰 Баланс баллов")],
        [KeyboardButton(text="📜 История баллов")],
        [KeyboardButton(text="◀️ Назад в главное меню")]
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

def get_phone_keyboard():
    button = KeyboardButton(text="📱 Поделиться номером", request_contact=True)
    return ReplyKeyboardMarkup(keyboard=[[button]], resize_keyboard=True, one_time_keyboard=True)

def get_back_to_main_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ В главное меню", callback_data="back_to_main")
    return builder.as_markup()