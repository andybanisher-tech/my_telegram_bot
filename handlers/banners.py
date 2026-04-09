import asyncio
import os
import logging
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from keyboards.common import get_back_to_main_keyboard
from keyboards.companies import get_company_selection_keyboard
from states import states
import promo_client
import bitrix_client
import soap_client
from urllib.parse import quote

router = Router()
logger = logging.getLogger(__name__)

BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://news-bot-stalker.ru")

async def fetch_and_show_banners(
    message: types.Message,
    user_id: int,
    company_code: str,
    brand_filter: str = None,
    partner_name: str = None,
    is_manager_request: bool = False
):
    wait_msg = await message.answer("⏳ Проверяем акции...")
    
    # Получаем персональные акции
    promotions = await asyncio.to_thread(promo_client.get_promotions_list_sync, company_code)
    
    # Если персональных нет и это запрос менеджера или обычного пользователя, предлагаем все акции сайта
    if not promotions:
        if is_manager_request:
            # Для менеджера: показываем все акции сайта
            all_banners = await asyncio.to_thread(bitrix_client.get_banners_sync, company_code)
            if all_banners:
                # Используем специальный параметр all_promos=1
                web_app_url = f"{BASE_WEB_URL}/promo/{company_code}?all_promos=1"
                if brand_filter:
                    web_app_url += f"&brand={brand_filter}"
                if partner_name:
                    web_app_url += f"&partner_name={quote(partner_name)}"
                web_app_button = InlineKeyboardButton(
                    text="🎁 Открыть все акции сайта",
                    web_app=WebAppInfo(url=web_app_url)
                )
                keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])
                await wait_msg.delete()
                await message.answer(
                    f"🎁 *Для контрагента нет персональных акций, но есть общие акции сайта!*\n\n"
                    "Нажмите на кнопку ниже, чтобы открыть страницу с предложениями.",
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                await message.answer("Выберите действие:", reply_markup=get_back_to_main_keyboard())
                return
            else:
                await wait_msg.delete()
                await message.answer("❌ Для указанного контрагента нет активных акций (ни персональных, ни общих).")
                return
        else:
            await wait_msg.delete()
            await message.answer("❌ Для вас пока нет активных персональных акций.")
            return
    
    # Если есть персональные акции (или мы продолжили для менеджера с персональными)
    web_app_url = f"{BASE_WEB_URL}/promo/{company_code}"
    if brand_filter:
        web_app_url += f"?brand={brand_filter}"
    if partner_name:
        web_app_url += f"&partner_name={quote(partner_name)}"
    # Если это запрос менеджера и есть персональные, добавляем флаг персональных (не обязательно)
    
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
    partner_name = data.get('partner_name')
    is_manager_request = data.get('is_manager_request', False)
    await callback.answer("⏳ Загружаем акции...")
    await callback.message.delete()
    await state.clear()
    await fetch_and_show_banners(callback.message, callback.from_user.id, company_code, brand_filter, partner_name, is_manager_request)