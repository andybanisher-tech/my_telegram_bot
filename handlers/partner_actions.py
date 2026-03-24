import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db
import soap_client
import bitrix_client
from keyboards.common import get_back_to_main_keyboard
from utils.helpers import is_manager, clean_html, clean_url
import logging

router = Router()
logger = logging.getLogger(__name__)

class PartnerActions(StatesGroup):
    waiting_for_partner_id = State()
    confirming_partner = State()

async def partner_actions_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_manager(user_id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return
    await state.set_state(PartnerActions.waiting_for_partner_id)
    await message.answer("Введите ID контрагента (например, С88201):")

@router.message(PartnerActions.waiting_for_partner_id)
async def partner_id_received(message: types.Message, state: FSMContext):
    partner_id = message.text.strip()
    if not partner_id:
        await message.answer("❌ ID не может быть пустым. Введите ID контрагента:")
        return
    await message.answer("⏳ Проверяем контрагента...")
    partner_info = await soap_client.get_partner_by_id(partner_id)
    if not partner_info:
        await message.answer("❌ Контрагент не найден. Проверьте ID и попробуйте снова.")
        return
    await state.update_data(partner_id=partner_id, partner_info=partner_info)
    await state.set_state(PartnerActions.confirming_partner)
    await message.answer(
        f"Найден контрагент:\n"
        f"Код: {partner_info['code']}\n"
        f"Название: {partner_info['name']}\n\n"
        f"Всё верно? (да/нет)",
        reply_markup=types.ReplyKeyboardMarkup(
            keyboard=[[types.KeyboardButton(text="✅ Да"), types.KeyboardButton(text="❌ Нет")]],
            resize_keyboard=True,
            one_time_keyboard=True
        )
    )

@router.message(PartnerActions.confirming_partner)
async def partner_confirm(message: types.Message, state: FSMContext):
    text = message.text.lower()
    if text not in ["да", "✅ да", "нет", "❌ нет"]:
        await message.answer("Пожалуйста, ответьте «да» или «нет».")
        return
    if text.startswith("да") or text == "✅ да":
        data = await state.get_data()
        partner_id = data['partner_id']
        await message.answer("⏳ Загружаем акции...", reply_markup=types.ReplyKeyboardRemove())
        banners = await bitrix_client.get_banners(partner_id)
        if not banners:
            await message.answer("❌ Не удалось загрузить акции или для этого контрагента нет активных акций.")
        else:
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
                        chat_id=message.chat.id,
                        text=msg['text'],
                        parse_mode=msg['parse_mode'],
                        reply_markup=msg['reply_markup']
                    )
                except Exception as e:
                    logger.error(f"Ошибка отправки сообщения об акции: {e}")
                    await message.bot.send_message(
                        chat_id=message.chat.id,
                        text=msg['text'],
                        reply_markup=msg['reply_markup']
                    )
                await asyncio.sleep(0.1)

        await message.answer("Выберите действие:", reply_markup=get_back_to_main_keyboard())
        await state.clear()
    else:
        await message.answer("Операция отменена.", reply_markup=get_back_to_main_keyboard())
        await state.clear()