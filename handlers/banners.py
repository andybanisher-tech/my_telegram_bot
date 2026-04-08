import asyncio
import os
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from keyboards.common import get_back_to_main_keyboard
from states import states
import logging

router = Router()
logger = logging.getLogger(__name__)

# Базовый URL веб-сервера с акциями (будет взят из .env)
BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://vm94041.it-garage.network")

async def fetch_and_show_banners(message: types.Message, user_id: int, company_code: str, brand_filter: str = None):
    """
    Отправляет пользователю ссылку на веб-страницу со списком акций.
    Больше не генерирует длинное HTML-сообщение в чате.
    """
    await message.answer("⏳ Готовим подборку акций...")
    
    # Формируем URL для веб-страницы
    promo_url = f"{BASE_WEB_URL}/promo/{company_code}"
    if brand_filter:
        # Если нужна фильтрация по бренду, добавляем параметр запроса
        promo_url += f"?brand={brand_filter}"
    
    # Отправляем ссылку. Telegram сам подхватит Open Graph мета-теги и покажет превью
    await message.answer(
        f"🎁 *Ваша персональная подборка акций готова!*\n\n"
        f"Нажмите на кнопку ниже, чтобы открыть страницу с предложениями.\n\n"
        f"🔗 [Открыть страницу с акциями]({promo_url})",
        parse_mode="Markdown",
        disable_web_page_preview=False  # Разрешаем показывать превью
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