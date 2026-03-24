import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import bitrix_client
from keyboards.common import get_back_to_main_keyboard
from states import states
from utils.helpers import clean_html
import logging

router = Router()
logger = logging.getLogger(__name__)

async def fetch_and_show_banners(message: types.Message, user_id: int, company_code: str, brand_filter: str = None):
    await message.answer("⏳ Загружаем акции...")
    banners = await bitrix_client.get_banners(company_code)
    if not banners:
        await message.answer("❌ Не удалось загрузить акции или для этой компании нет активных акций.")
        return

    # Фильтруем по бренду, если указан
    if brand_filter:
        brand_filter_lower = brand_filter.lower()
        filtered_banners = []
        for banner in banners:
            name = banner.get('name', '').lower()
            # Если название баннера содержит искомый бренд (приблизительно)
            if brand_filter_lower in name:
                filtered_banners.append(banner)
        banners = filtered_banners
        if not banners:
            await message.answer(f"❌ Нет акций, содержащих бренд «{brand_filter}».")
            return

    prepared_messages = []
    for banner in banners:
        text_parts = []
        if banner.get('image'):
            text_parts.append(f'<a href="{banner["image"]}">🎁 Акция</a>')
        else:
            text_parts.append('🎁 Акция')
        if banner.get('name'):
            text_parts.append(f"\n<b>{banner['name']}</b>")
        if banner.get('description'):
            cleaned_desc = clean_html(banner['description'])
            if cleaned_desc:
                text_parts.append(f"\n{cleaned_desc}")
        if banner.get('date_to'):
            text_parts.append(f"\n📅 Действует до: {banner['date_to']}")
        markup = None
        if banner.get('link'):
            clean_link = banner['link'].strip()
            if not clean_link.startswith(('http://', 'https://')):
                clean_link = 'https://' + clean_link
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 Перейти", url=clean_link)]
            ])
        full_text = "".join(text_parts)
        prepared_messages.append({
            'text': full_text,
            'parse_mode': 'HTML',
            'reply_markup': markup
        })

    for msg in prepared_messages:
        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=msg['text'],
                parse_mode=msg['parse_mode'],
                reply_markup=msg['reply_markup']
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения об акции: {e}")
            await message.bot.send_message(
                chat_id=user_id,
                text=msg['text'],
                reply_markup=msg['reply_markup']
            )
        await asyncio.sleep(0.1)

    await message.answer("Выберите действие:", reply_markup=get_back_to_main_keyboard())

@router.callback_query(lambda c: c.data.startswith('banner_comp_'), states.BannersProcess.choosing_company)
async def process_banner_company_choice(callback: types.CallbackQuery, state: FSMContext):
    company_code = callback.data.split('_')[2]
    await callback.answer("⏳ Загружаем акции...")
    await callback.message.delete()
    await state.clear()
    # Бренд не передаётся, так как изначально не задан
    await fetch_and_show_banners(callback.message, callback.from_user.id, company_code)