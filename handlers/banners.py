import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import promo_client
from keyboards.common import get_back_to_main_keyboard
from states import states
import logging

router = Router()
logger = logging.getLogger(__name__)

async def fetch_and_show_banners(message: types.Message, user_id: int, company_code: str, brand_filter: str = None):
    await message.answer("⏳ Загружаем акции...")
    promotions = await promo_client.get_promotions_list(company_code)
    if not promotions:
        await message.answer("❌ Не удалось загрузить список акций или акций нет.")
        return

    # Фильтрация по бренду (mark)
    if brand_filter:
        brand_filter_lower = brand_filter.lower()
        filtered = []
        for promo in promotions:
            mark = promo.get('mark', '')
            if mark and brand_filter_lower in mark.lower():
                filtered.append(promo)
        promotions = filtered
        if not promotions:
            await message.answer(f"❌ Нет акций для бренда «{brand_filter}».")
            return

    # Получаем детали каждой акции
    detailed_promos = []
    for promo in promotions:
        promo_id = promo.get('id')
        if not promo_id:
            continue
        details = await promo_client.get_promotion_details(str(promo_id))
        if details:
            details['date_from'] = promo.get('date_from')
            details['date_to'] = promo.get('date_to')
            details['mark'] = promo.get('mark')
            detailed_promos.append(details)
        await asyncio.sleep(0.1)

    if not detailed_promos:
        await message.answer("❌ Не удалось загрузить детали акций.")
        return

    # Формируем HTML-сообщение
    html_parts = ["<b>🎁 Акции для вас</b>\n\n"]
    for promo in detailed_promos:
        name = promo.get('name', 'Акция')
        html_parts.append(f"<b>{name}</b>")
        date_to = promo.get('date_to')
        if date_to:
            html_parts.append(f"📅 Действует до: {date_to}")
        image = promo.get('image')
        if image:
            html_parts.append(f'<a href="{image}">🖼️ Превью акции</a>')
        link = promo.get('link')
        if link:
            if not link.startswith(('http://', 'https://')):
                link = 'https://' + link
            html_parts.append(f'<a href="{link}">🔗 Подробнее на сайте</a>')
        html_parts.append("\n" + "-"*30 + "\n")

    full_html = "\n".join(html_parts)
    # Разбивка на части при превышении лимита
    if len(full_html) > 4000:
        parts = []
        current = "<b>🎁 Акции для вас</b>\n\n"
        for line in full_html.split("\n"):
            if len(current) + len(line) + 1 > 4000:
                parts.append(current)
                current = "<b>🎁 Акции для вас (продолжение)</b>\n\n"
            current += line + "\n"
        if current:
            parts.append(current)
        for part in parts:
            await message.answer(part, parse_mode="HTML", disable_web_page_preview=False)
    else:
        await message.answer(full_html, parse_mode="HTML", disable_web_page_preview=False)

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