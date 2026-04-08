from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from intent_classifier import get_intent, load_llm_model, extract_brand
import logging
import re
import asyncio

from . import main_menu
from utils.helpers import is_manager

router = Router()
logger = logging.getLogger(__name__)

llm = load_llm_model()

def extract_partner_id(text: str):
    """Извлекает ID контрагента (буква + цифры) из текста. Буква может быть русской или английской."""
    match = re.search(r'([a-zA-Zа-яА-Я])(\d+)', text)
    if match:
        return match.group(1) + match.group(2)
    return None

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    global llm
    user_id = message.from_user.id
    text = message.text.strip()

    if len(text) < 2:
        return
    if text.startswith('/'):
        return

    if llm is None:
        logger.warning("Модель не загружена, попытка перезагрузить...")
        llm = load_llm_model()

    intent = get_intent(text, llm)
    logger.info(f"Определён интент: {intent} для текста: {text}")

    if intent == "balance":
        await main_menu.show_balance(message, state)
    elif intent == "history":
        await main_menu.show_history(message, state)
    elif intent == "companies":
        await main_menu.show_companies(message, state)
    elif intent == "banners":
        # Проверяем, менеджер ли пользователь
        if is_manager(user_id):
            partner_id = extract_partner_id(text)
            logger.info(f"Менеджер {user_id}, извлечённый ID контрагента: {partner_id}")
            if partner_id:
                await main_menu.show_banners_for_partner(message, state, partner_id)
                return
        # Обычная логика для пользователей
        brand = extract_brand(text, llm) if llm else None
        if brand:
            logger.info(f"Извлечён бренд: {brand} для текста: {text}")
        else:
            logger.info(f"Бренд не найден для текста: {text}")
        await main_menu.show_banners(message, state, brand)
    elif intent == "bonus":
        await main_menu.show_bonus(message, state)
    elif intent == "subscribe":
        await main_menu.show_subscribe(message, state)
    elif intent == "subscriptions":
        await main_menu.show_subscriptions(message, state)
    elif intent == "help":
        await main_menu.show_help(message, state)
    else:
        await message.answer(
            "Извините, я не понял ваш запрос. Попробуйте использовать кнопки меню или введите ключевые слова: "
            "баланс, история, компании, акции, реферальная, подписки, помощь."
        )