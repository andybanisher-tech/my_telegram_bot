import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import bitrix_client
from keyboards.common import get_back_to_main_keyboard
from states import states
from utils.helpers import clean_html, clean_url
import logging

router = Router()
logger = logging.getLogger(__name__)

async def fetch_and_show_banners(message: types.Message, user_id: int, company_code: str):
    await message.answer("⏳ Загружаем акции...")
    banners = await bitrix_client.get_banners(company_code)
    if not banners:
        await message.answer("❌ Не удалось загрузить акции или для этой компании нет активных акций.")
        return

    prepared_messages = []
    for banner in banners:
        text_parts = []
        if banner.get('image'):
            clean_image = clean_url(banner['image'])
            text_parts.append(f'<a href="{clean_image}">🎁 Акция</a>')
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
            clean_link = clean_url(banner['link'])
            if clean_link:
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
    await fetch_and_show_banners(callback.message, callback.from_user.id, company_code)