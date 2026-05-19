import os
import asyncio
import logging
import urllib.parse
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import database as db
import promo_client
from utils.helpers import is_manager
from handlers.companies import get_companies_keyboard
from keyboards.common import (
    get_main_keyboard, get_phone_keyboard, get_back_to_main_keyboard,
    get_bonus_submenu_keyboard
)
from keyboards.companies import get_companies_view_keyboard, get_company_selection_keyboard
from keyboards.subscriptions import get_category_choice_keyboard, get_subscription_management_keyboard
from handlers.companies import process_companies_loading
from handlers.banners import fetch_and_show_banners
from handlers.partner_actions import partner_actions_start
from handlers.bonus import fetch_and_show_balance, fetch_and_show_history
from states import states, BalanceSelecting, HistorySelecting, BannersSelecting

logger = logging.getLogger(__name__)
router = Router()

BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://news-bot-stalker.ru")

async def show_main_menu(chat_id: int, user_id: int, bot):
    await bot.send_message(chat_id, "Выбери действие:", reply_markup=get_main_keyboard(user_id))

# ---------- Пользовательские функции ----------
async def show_balance(message: types.Message, state: FSMContext, reply_chat_id: int, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id
    keyboard, error = await get_companies_keyboard(user_id, "balance", message.bot)
    if error:
        await message.bot.send_message(reply_chat_id, error)
        return
    await message.bot.send_message(reply_chat_id, "Выберите компанию для просмотра баланса:", reply_markup=keyboard)
    await state.set_state(BalanceSelecting.company)

async def show_history(message: types.Message, state: FSMContext, reply_chat_id: int, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id
    keyboard, error = await get_companies_keyboard(user_id, "history", message.bot)
    if error:
        await message.bot.send_message(reply_chat_id, error)
        return
    await message.bot.send_message(reply_chat_id, "Выберите компанию для просмотра истории:", reply_markup=keyboard)
    await state.set_state(HistorySelecting.company)

async def show_companies(message: types.Message, state: FSMContext, reply_chat_id: int, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id
    phone = db.get_user_phone(user_id)
    if not phone:
        await state.set_state(states.CompanyProcess.waiting_for_phone)
        await message.bot.send_message(reply_chat_id,
            "Для просмотра компаний поделись своим номером телефона.",
            reply_markup=get_phone_keyboard()
        )
        return
    companies = db.get_user_companies(user_id)
    if companies:
        lines = ["🏢 *Ваши компании:*\n"]
        for comp in companies:
            lines.append(f"• {comp['name']} (код {comp['code']})")
        await message.bot.send_message(
            reply_chat_id,
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=get_companies_view_keyboard()
        )
    else:
        await process_companies_loading(user_id, phone, state, message, reply_chat_id)

async def show_banners(message: types.Message, state: FSMContext, brand: str = None, reply_chat_id: int = None, user_id: int = None):
    if reply_chat_id is None:
        reply_chat_id = message.chat.id
    if user_id is None:
        user_id = message.from_user.id
    keyboard, error = await get_companies_keyboard(user_id, "banners", message.bot)
    if error:
        await message.bot.send_message(reply_chat_id, error)
        return
    await state.update_data(brand_filter=brand)
    await state.set_state(BannersSelecting.company)
    await message.bot.send_message(reply_chat_id, "Выберите компанию для показа акций:", reply_markup=keyboard)

async def show_banners_for_partner(message: types.Message, state: FSMContext, partner_id: str, partner_name: str, reply_chat_id: int):
    wait_msg = await message.bot.send_message(reply_chat_id, f"⏳ Проверяем акции для контрагента {partner_id}...")
    promotions = await asyncio.to_thread(promo_client.get_promotions_list_sync, partner_id)
    if not promotions:
        await message.bot.delete_message(reply_chat_id, wait_msg.message_id)
        encoded_name = urllib.parse.quote(partner_name)
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Все акции сайта", web_app=WebAppInfo(url=f"{BASE_WEB_URL}/promo/{partner_id}?all=1&name={encoded_name}"))]
        ])
        await message.bot.send_message(
            reply_chat_id,
            f"❌ Для контрагента {partner_name} (ID {partner_id}) нет персональных акций.\n"
            "Вы можете посмотреть все действующие акции на сайте:",
            reply_markup=keyboard
        )
        await message.bot.send_message(reply_chat_id, "Выберите действие:", reply_markup=get_back_to_main_keyboard())
        return
    encoded_name = urllib.parse.quote(partner_name)
    web_app_url = f"{BASE_WEB_URL}/promo/{partner_id}?name={encoded_name}"
    web_app_button = InlineKeyboardButton(text="🎁 Открыть акции", web_app=WebAppInfo(url=web_app_url))
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    await message.bot.delete_message(reply_chat_id, wait_msg.message_id)
    await message.bot.send_message(
        reply_chat_id,
        f"🎁 *Акции для контрагента {partner_name} (ID {partner_id})*\n\n"
        "Нажмите на кнопку ниже, чтобы открыть страницу с предложениями.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await message.bot.send_message(reply_chat_id, "Выберите действие:", reply_markup=get_back_to_main_keyboard())

async def show_bonus(message: types.Message, state: FSMContext, reply_chat_id: int):
    await message.bot.send_message(reply_chat_id, "Выберите раздел:", reply_markup=get_bonus_submenu_keyboard())

async def show_help(message: types.Message, state: FSMContext, reply_chat_id: int, user_id: int = None):
    if user_id is None:
        user_id = message.from_user.id
    help_text = (
        "📚 *Доступные действия:*\n\n"
        "• 🏢 *Мои компании* – просмотр компаний, привязанных к вашему номеру.\n"
        "• 🎁 *Текущие акции* – актуальные акции для ваших компаний.\n"
        "• 🎁 *Реферальная программа* – бонусный баланс и история.\n"
    )
    if is_manager(user_id):
        help_text += "• 👥 *Акции контрагента* – просмотр акций для любого контрагента по его ID.\n"
    help_text += "\nЕсли у вас есть вопросы, обратитесь к администратору."
    await message.bot.send_message(reply_chat_id, help_text, parse_mode="Markdown")

# ---------- Обработчики инлайн-кнопок главного меню ----------
@router.callback_query(lambda c: c.data.startswith("menu_"))
async def handle_main_menu_callback(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = callback.data
    if callback.message.chat.type != "private":
        reply_chat_id = user_id
    else:
        reply_chat_id = callback.message.chat.id
    await callback.answer()

    if data == "menu_companies":
        await show_companies(callback.message, state, reply_chat_id, user_id)
    elif data == "menu_banners":
        await show_banners(callback.message, state, None, reply_chat_id, user_id)
    elif data == "menu_bonus":
        await show_bonus(callback.message, state, reply_chat_id)
    elif data == "menu_partner":
        if not is_manager(user_id):
            await callback.bot.send_message(reply_chat_id, "⛔ У вас нет прав для этой команды.")
            return
        await partner_actions_start(callback.message, state)
    elif data == "menu_help":
        await show_help(callback.message, state, reply_chat_id, user_id)

@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.message.chat.type != "private":
        reply_chat_id = callback.from_user.id
    else:
        reply_chat_id = callback.message.chat.id
    await callback.message.delete()
    await callback.bot.send_message(reply_chat_id, "Выбери действие:", reply_markup=get_main_keyboard(callback.from_user.id))
    await callback.answer()
