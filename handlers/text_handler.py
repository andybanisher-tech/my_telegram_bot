from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from intent_classifier import get_intent, load_llm_model
import logging

from . import bonus, main_menu, banners, subscriptions, companies, start
from utils.helpers import is_manager

router = Router()
logger = logging.getLogger(__name__)

# Загружаем модель один раз при старте (может быть None, если модель недоступна)
llm = load_llm_model()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if len(text) < 2:
        return
    if text.startswith('/'):
        return

    intent = get_intent(text, llm)
    logger.info(f"Определён интент: {intent} для текста: {text}")

    if intent == "balance":
        await bonus.bonus_balance_start(message, state)
    elif intent == "history":
        await bonus.bonus_history_start(message, state)
    elif intent == "companies":
        original_text = message.text
        message.text = "🏢 Мои компании"
        await main_menu.handle_main_menu(message, state)
        message.text = original_text
    elif intent == "banners":
        original_text = message.text
        message.text = "🎁 Текущие акции"
        await main_menu.handle_main_menu(message, state)
        message.text = original_text
    elif intent == "bonus":
        original_text = message.text
        message.text = "🎁 Реферальная программа"
        await main_menu.handle_main_menu(message, state)
        message.text = original_text
    elif intent == "subscribe":
        original_text = message.text
        message.text = "📰 Подписаться на новости"
        await main_menu.handle_main_menu(message, state)
        message.text = original_text
    elif intent == "subscriptions":
        original_text = message.text
        message.text = "📋 Мои подписки"
        await main_menu.handle_main_menu(message, state)
        message.text = original_text
    elif intent == "help":
        original_text = message.text
        message.text = "ℹ️ Помощь"
        await main_menu.handle_main_menu(message, state)
        message.text = original_text
    else:
        await message.answer(
            "Извините, я не понял ваш запрос. Попробуйте использовать кнопки меню или введите ключевые слова: "
            "баланс, история, компании, акции, реферальная, подписки, помощь."
        )