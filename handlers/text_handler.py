from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import logging
from . import bonus, banners, companies, main_menu
from llm_intent import get_intent_from_llm

router = Router()
logger = logging.getLogger(__name__)

def get_intent_keywords(text):
    """Простейший парсер ключевых слов."""
    text = text.lower()
    if any(word in text for word in ['баланс', 'баллы', 'сколько баллов']):
        return 'balance'
    if any(word in text for word in ['история', 'изменение', 'операции']):
        return 'history'
    if any(word in text for word in ['мои компании', 'какие компании', 'покажи компании']):
        return 'companies'
    if any(word in text for word in ['акции', 'предложения', 'скидки']):
        return 'banners'
    if any(word in text for word in ['реферальная', 'программа']):
        return 'bonus'
    return None

@router.message(F.text)
async def handle_text(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text

    # 1. Сначала пробуем keywords
    intent = get_intent_keywords(text)

    # 2. Если не определилось, используем LLM
    if not intent:
        intent = get_intent_from_llm(text)
        if intent == "unknown":
            await message.answer("Извините, я не понял запрос. Пожалуйста, используйте кнопки меню.")
            return

    # 3. Вызываем соответствующую функцию (как при нажатии кнопок)
    if intent == 'balance':
        await bonus.bonus_balance_start(message, state)
    elif intent == 'history':
        await bonus.bonus_history_start(message, state)
    elif intent == 'companies':
        # В main_menu нет прямой функции для компаний, поэтому вызываем соответствующую логику
        # В main_menu это обрабатывается в handle_main_menu для текста "🏢 Мои компании"
        # Создадим фиктивное сообщение или вызовем соответствующую функцию напрямую
        # Но проще вызвать обработчик из main_menu, передав нужный текст
        await main_menu.handle_main_menu(message, state, text="🏢 Мои компании")
    elif intent == 'banners':
        await main_menu.handle_main_menu(message, state, text="🎁 Текущие акции")
    elif intent == 'bonus':
        await main_menu.handle_main_menu(message, state, text="🎁 Реферальная программа")
    else:
        await message.answer("Извините, я не понял запрос. Попробуйте воспользоваться кнопками меню.")