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
    # Удаляем лишние пробелы и приводим к нижнему регистру для единообразия
    text_clean = text.strip().lower()
    # Ищем последовательность: одна буква (кириллица или латиница) + цифры
    match = re.search(r'([a-zа-я])(\d+)', text_clean)
    if match:
        # Возвращаем оригинальный регистр буквы? Лучше вернуть как есть, но для API обычно нужен оригинал
        # Поскольку мы привели к нижнему регистру, восстановим букву из оригинального текста
        original_letter = text[text.lower().find(match.group(1))]  # костыль, но работает
        return original_letter + match.group(2)
    return None



@router.message(F.text, lambda msg: not msg.text.startswith('/'))
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
        is_man = is_manager(user_id)
        logger.info(f"Пользователь {user_id} является менеджером: {is_man}")
        if is_man:
            partner_id = extract_partner_id(text)
            logger.info(f"Извлечённый ID контрагента: {partner_id}")
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