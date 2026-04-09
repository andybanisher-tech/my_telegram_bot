import os
import asyncio
import logging
import soap_client
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
import database as db
import promo_client
from utils.helpers import is_manager
from keyboards.common import (
    get_main_keyboard, get_phone_keyboard, get_back_to_main_keyboard,
    get_bonus_submenu_keyboard
)
from keyboards.companies import get_companies_view_keyboard, get_company_selection_keyboard
from keyboards.subscriptions import get_category_choice_keyboard, get_subscription_management_keyboard
from handlers.companies import process_companies_loading
from handlers.banners import fetch_and_show_banners
from handlers.partner_actions import partner_actions_start
from handlers.bonus import show_company_selection, fetch_and_show_balance, fetch_and_show_history
from states import states

logger = logging.getLogger(__name__)
router = Router()

BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://news-bot-stalker.ru")

async def show_main_menu(chat_id: int, user_id: int, bot):
    await bot.send_message(chat_id, "Главное меню:", reply_markup=get_main_keyboard(user_id))

# ---------- Функции для вызова из text_handler ----------
async def show_balance(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    company = await show_company_selection(user_id, message, "balance")
    if company:
        await fetch_and_show_balance(message, user_id, company['code'])

async def show_history(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    company = await show_company_selection(user_id, message, "history")
    if company:
        await fetch_and_show_history(message, user_id, company['code'])

async def show_companies(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    phone = db.get_user_phone(user_id)
    if not phone:
        await state.set_state(states.CompanyProcess.waiting_for_phone)
        await message.answer(
            "Для просмотра компаний поделись своим номером телефона.",
            reply_markup=get_phone_keyboard()
        )
        return
    companies = db.get_user_companies(user_id)
    if companies:
        lines = ["🏢 *Ваши компании:*\n"]
        for comp in companies:
            lines.append(f"• {comp['name']} (код {comp['code']})")
        await message.answer(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=get_companies_view_keyboard()
        )
    else:
        await process_companies_loading(user_id, phone, state, message)

async def show_banners(message: types.Message, state: FSMContext, brand: str = None):
    user_id = message.from_user.id
    companies = db.get_user_companies(user_id)
    if not companies:
        await message.answer(
            "Для просмотра акций необходимо иметь выбранные компании. "
            "Сначала перейдите в раздел «Мои компании» и загрузите список."
        )
        return
    if len(companies) == 1:
        await fetch_and_show_banners(message, user_id, companies[0]['code'], brand)
    else:
        await state.update_data(brand_filter=brand)
        await state.set_state(states.BannersProcess.choosing_company)
        await message.answer(
            "У вас несколько компаний. Выберите, для какой показать акции:",
            reply_markup=get_company_selection_keyboard(companies)
        )

async def show_banners_for_partner(message: types.Message, state: FSMContext, partner_id: str):
    """Показывает акции для указанного ID контрагента (для менеджеров)."""
    wait_msg = await message.answer("⏳ Проверяем акции для контрагента...")
    
    # Получаем информацию о контрагенте
    partner_info = await soap_client.get_partner_by_id(partner_id)
    if not partner_info:
        await wait_msg.delete()
        await message.answer("❌ Контрагент с таким ID не найден.")
        return
    
    partner_name = partner_info.get('name', partner_id)
    
    # Сохраняем данные для последующего использования в колбэке выбора компании
    await state.update_data(partner_name=partner_name, is_manager_request=True)
    
    # Проверяем, есть ли у менеджера свои компании (не обязательно, но для логики)
    companies = db.get_user_companies(message.from_user.id)
    if len(companies) == 1:
        # Если у менеджера одна компания, используем её код как company_code (но для менеджера company_code — это код его компании? Нет, для запроса акций для контрагента нужен ID контрагента, а не компании менеджера. Поэтому company_code = partner_id)
        await fetch_and_show_banners(message, message.from_user.id, partner_id, None, partner_name, True)
    else:
        # Если несколько компаний, нужно выбрать, от имени какой компании делать запрос? Для запроса акций контрагента company_code — это ID контрагента, а не компании менеджера. Поэтому не нужно выбирать компанию менеджера. Просто сразу передаём partner_id.
        # Убираем выбор компании, так как company_code уже известен.
        await fetch_and_show_banners(message, message.from_user.id, partner_id, None, partner_name, True)

async def show_bonus(message: types.Message, state: FSMContext):
    await message.answer("Выберите раздел:", reply_markup=get_bonus_submenu_keyboard())

async def show_subscribe(message: types.Message, state: FSMContext):
    await state.set_state(states.CategoryChoice.selecting)
    await state.update_data(selected_categories=[])
    await message.answer(
        "Выберите категории для подписки. Нажимайте на кнопки, чтобы отметить/снять отметку.\n"
        "Когда закончите, нажмите «✅ Готово».",
        reply_markup=get_category_choice_keyboard([])
    )

async def show_subscriptions(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await state.set_state(states.SubscriptionManagement.selecting)
    current_subs = db.get_user_subscriptions(user_id)
    await state.update_data(selected_subscriptions=current_subs.copy())
    await message.answer(
        "Управление подписками. Нажимайте на кнопки, чтобы отметить/снять отметку.\n"
        "Когда закончите, нажмите «✅ Готово».",
        reply_markup=get_subscription_management_keyboard(user_id, current_subs)
    )

async def show_help(message: types.Message, state: FSMContext):
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
    await message.answer(help_text, parse_mode="Markdown")

# ---------- Оригинальный обработчик кнопок главного меню ----------
@router.message(F.text.in_([
    "📰 Подписаться на новости", "📋 Мои подписки", "🏢 Мои компании",
    "🎁 Текущие акции", "🎁 Реферальная программа", "👥 Акции контрагента",
    "ℹ️ Помощь"
]))
async def handle_main_menu(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text

    if text == "📰 Подписаться на новости":
        await show_subscribe(message, state)
    elif text == "📋 Мои подписки":
        await show_subscriptions(message, state)
    elif text == "🏢 Мои компании":
        await show_companies(message, state)
    elif text == "🎁 Текущие акции":
        await show_banners(message, state)
    elif text == "🎁 Реферальная программа":
        await show_bonus(message, state)
    elif text == "👥 Акции контрагента":
        if not is_manager(user_id):
            await message.answer("⛔ У вас нет прав для этой команды.")
            return
        await partner_actions_start(message, state)
    elif text == "ℹ️ Помощь":
        await show_help(message, state)

@router.message(F.text == "◀️ Назад в главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard(message.from_user.id))