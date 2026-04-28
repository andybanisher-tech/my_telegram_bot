from aiogram import Router, types, F
from aiogram.enums import ChatType
from aiogram.fsm.context import FSMContext
from intent_classifier import get_intent, load_llm_model, extract_brand
import logging
import re
import soap_client

from . import main_menu
from utils.helpers import is_manager

router = Router()
logger = logging.getLogger(__name__)

# Загружаем модель один раз при старте
_llm_instance = load_llm_model()

def extract_partner_id(text: str):
    match = re.search(r'([a-zA-Zа-яА-Я])(\d+)', text)
    if match:
        return match.group(1) + match.group(2)
    return None

BOT_USERNAME = "stalkerco_news_bot"   # укажите точное имя вашего бота

def is_bot_mentioned(message: types.Message) -> bool:
    if not message.text:
        return False
    return f"@{BOT_USERNAME}" in message.text

@router.message(
    F.text,
    lambda msg: not msg.text.startswith('/'),
    lambda msg: msg.chat.type == ChatType.PRIVATE or (
        msg.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP) and
        is_bot_mentioned(msg)
    )
)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if len(text) < 2:
        return

    intent = get_intent(text, _llm_instance)
    logger.info(f"Определён интент: {intent} для текста: {text}")

    # Определяем, куда отправлять ответ
    if message.chat.type == ChatType.PRIVATE:
        reply_chat_id = message.chat.id
    else:
        reply_chat_id = user_id
        try:
            await message.reply(
                f"@{message.from_user.username}, я отвечу вам в личные сообщения. Пожалуйста, проверьте их.",
                reply_to_message_id=message.message_id
            )
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления в группу: {e}")

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
        brand = extract_brand(text, _llm_instance) if _llm_instance else None
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