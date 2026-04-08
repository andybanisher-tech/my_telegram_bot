import asyncio
import os
import re
import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from keyboards.common import get_back_to_main_keyboard
from keyboards.companies import get_company_selection_keyboard
from states import states
from utils.helpers import is_manager
import promo_client

router = Router()
logger = logging.getLogger(__name__)

BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://news-bot-stalker.ru")

def extract_partner_id(text: str) -> str | None:
    """
    Извлекает ID контрагента из текста запроса.
    ID имеет формат: русская буква (или несколько) + цифры.
    Примеры: с88211, С88201, Т0066007.
    """
    # Ищем паттерн: одна или несколько русских букв, затем цифры
    match = re.search(r'([а-яё]{1,3})(\d+)', text, re.IGNORECASE)
    if match:
        # Возвращаем как есть (буквы могут быть в любом регистре)
        return match.group(0)
    return None

async def fetch_and_show_banners(message: types.Message, user_id: int, company_code: str, brand_filter: str = None):
    wait_msg = await message.answer("⏳ Проверяем наличие акций...")
    
    promotions = await asyncio.to_thread(promo_client.get_promotions_list_sync, company_code)
    if not promotions:
        await wait_msg.delete()
        await message.answer("❌ Для вас пока нет активных акций.")
        return
    
    web_app_url = f"{BASE_WEB_URL}/promo/{company_code}"
    if brand_filter:
        web_app_url += f"?brand={brand_filter}"
    
    web_app_button = InlineKeyboardButton(
        text="🎁 Открыть акции",
        web_app=WebAppInfo(url=web_app_url)
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    
    await wait_msg.delete()
    await message.answer(
        "🎁 *Ваша персональная подборка акций готова!*\n\n"
        "Нажмите на кнопку ниже, чтобы открыть страницу с предложениями.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await message.answer("Выберите действие:", reply_markup=get_back_to_main_keyboard())

@router.callback_query(lambda c: c.data.startswith('banner_comp_'), states.BannersProcess.choosing_company)
async def process_banner_company_choice(callback: types.CallbackQuery, state: FSMContext):
    company_code = callback.data.split('_')[2]
    data = await state.get_data()
    brand_filter = data.get('brand_filter')
    await callback.answer("⏳ Загружаем акции...")
    await callback.message.delete()
    await state.clear()
    await fetch_and_show_banners(callback.message, callback.from_user.id, company_code, brand_filter)

# Новая функция для прямого запроса акций по ID контрагента (для менеджеров)
async def fetch_and_show_banners_by_partner(message: types.Message, partner_id: str, brand_filter: str = None):
    wait_msg = await message.answer("⏳ Проверяем акции для контрагента...")
    promotions = await asyncio.to_thread(promo_client.get_promotions_list_sync, partner_id)
    if not promotions:
        await wait_msg.delete()
        await message.answer(f"❌ Для контрагента {partner_id} нет активных акций.")
        return
    
    web_app_url = f"{BASE_WEB_URL}/promo/{partner_id}"
    if brand_filter:
        web_app_url += f"?brand={brand_filter}"
    
    web_app_button = InlineKeyboardButton(
        text="🎁 Открыть акции",
        web_app=WebAppInfo(url=web_app_url)
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
    
    await wait_msg.delete()
    await message.answer(
        f"🎁 *Акции для контрагента {partner_id}*\n\n"
        "Нажмите на кнопку ниже, чтобы открыть страницу с предложениями.",
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    await message.answer("Выберите действие:", reply_markup=get_back_to_main_keyboard())