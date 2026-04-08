from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from intent_classifier import get_intent, load_llm_model, extract_brand, extract_partner_id
import logging

from . import main_menu
from utils.helpers import is_manager

router = Router()
logger = logging.getLogger(__name__)

llm = load_llm_model()

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()

    if len(text) < 2:
        return
    if text.startswith('/'):
        return

    if llm is None:
        logger.warning("Модель не загружена, попытка перезагрузить...")
        global llm
        llm = load_llm_model()

    intent = get_intent(text, llm)
    logger.info(f"Определён интент: {intent} для текста: {text}")

    if intent == "banners":
        # Проверяем, не указан ли ID контрагента
        partner_id = extract_partner_id(text)
        if partner_id and is_manager(user_id):
            # Менеджер запрашивает акции для конкретного контрагента
            await main_menu.show_banners_for_partner(message, state, partner_id)
            return
        # Иначе пробуем извлечь бренд
        brand = extract_brand(text, llm) if llm else None
        if brand:
            logger.info(f"Извлечён бренд: {brand} для текста: {text}")
        else:
            logger.info(f"Бренд не найден для текста: {text}")
        await main_menu.show_banners(message, state, brand)
    elif intent == "balance":
        await main_menu.show_balance(message, state)
    elif intent == "history":
        await main_menu.show_history(message, state)
    elif intent == "companies":
        await main_menu.show_companies(message, state)
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