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

router = Router()
logger = logging.getLogger(__name__)

BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://news-bot-stalker.ru")

async def fetch_and_show_banners(message: types.Message, user_id: int, company_code: str, brand_filter: str = None):
    wait_msg = await message.answer("⏳ Проверяем наличие акций...")
    promotions = await asyncio.to_thread(promo_client.get_promotions_list_sync, company_code)
    if not promotions:
        await wait_msg.delete()
        # Предлагаем все акции сайта
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 Все акции сайта", web_app=WebAppInfo(url=f"{BASE_WEB_URL}/promo/{company_code}?all=1"))]
        ])
        await message.answer(
            "❌ Для вас нет персональных акций.\n"
            "Вы можете посмотреть все действующие акции на сайте:",
            reply_markup=keyboard
        )
        await message.answer("Выберите действие:", reply_markup=get_back_to_main_keyboard())
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