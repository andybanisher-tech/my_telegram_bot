from aiogram import Router, types, F
from aiogram.enums import ChatType
from aiogram.filters import BaseFilter
from aiogram.fsm.context import FSMContext
from intent_classifier import get_intent, load_llm_model, extract_brand
import logging
import re
import soap_client

from . import main_menu
from utils.helpers import is_manager

router = Router()
logger = logging.getLogger(__name__)

llm = load_llm_model()

BOT_USERNAME = "stalkerco_news_bot"   # замените на актуальное имя бота

def extract_partner_id(text: str):
    match = re.search(r'([a-zA-Zа-яА-Я])(\d+)', text)
    if match:
        return match.group(1) + match.group(2)
    return None

class NoActiveStateFilter(BaseFilter):
    async def __call__(self, message: types.Message, state: FSMContext) -> bool:
        current_state = await state.get_state()
        return current_state is None

def is_bot_mentioned(message: types.Message) -> bool:
    if not message.text:
        return False
    return f"@{BOT_USERNAME}" in message.text

@router.message(
    NoActiveStateFilter(),
    F.text,
    lambda msg: not msg.text.startswith('/'),
    lambda msg: msg.chat.type == ChatType.PRIVATE or (
        msg.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP) and
        is_bot_mentioned(msg)
    )
)
async def handle_text(message: types.Message, state: FSMContext):
    global llm
    user_id = message.from_user.id
    text = message.text.strip()

    if len(text) < 2:
        return

    if llm is None:
        logger.warning("Модель не загружена, попытка перезагрузить...")
        llm = load_llm_model()

    intent = get_intent(text, llm)
    logger.info(f"Определён интент: {intent} для текста: {text}")

    # Определяем, куда отправлять ответ
    if message.chat.type == ChatType.PRIVATE:
        reply_chat_id = message.chat.id
    else:
        reply_chat_id = user_id
        # Отправляем уведомление в группу
        try:
            await message.reply(
                f"@{message.from_user.username}, я отвечу вам в личные сообщения. Пожалуйста, проверьте их.",
                reply_to_message_id=message.message_id
            )
            logger.info(f"Отправлено уведомление в группу для {message.from_user.username}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления в группу: {e}")

    # Обработка интентов
    if intent == "balance":
        await main_menu.show_balance(message, state, reply_chat_id)
    elif intent == "history":
        await main_menu.show_history(message, state, reply_chat_id)
    elif intent == "companies":
        await main_menu.show_companies(message, state, reply_chat_id)
    elif intent == "banners":
        if is_manager(user_id):
            partner_id = extract_partner_id(text)
            if partner_id:
                partner_info = await soap_client.get_partner_by_id(partner_id)
                partner_name = partner_info['name'] if partner_info else partner_id
                await main_menu.show_banners_for_partner(message, state, partner_id, partner_name, reply_chat_id)
                return
        brand = extract_brand(text, llm) if llm else None
        if brand:
            logger.info(f"Извлечён бренд: {brand} для текста: {text}")
        else:
            logger.info(f"Бренд не найден для текста: {text}")
        await main_menu.show_banners(message, state, brand, reply_chat_id)
    elif intent == "bonus":
        await main_menu.show_bonus(message, state, reply_chat_id)
    elif intent == "subscribe":
        await main_menu.show_subscribe(message, state, reply_chat_id)
    elif intent == "subscriptions":
        await main_menu.show_subscriptions(message, state, reply_chat_id)
    elif intent == "help":
        await main_menu.show_help(message, state, reply_chat_id)
    else:
        await message.bot.send_message(
            chat_id=reply_chat_id,
            text="Извините, я не понял ваш запрос. Попробуйте использовать кнопки меню или введите ключевые слова: "
                 "баланс, история, компании, акции, реферальная, подписки, помощь."
        )