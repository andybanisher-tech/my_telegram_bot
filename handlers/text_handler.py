# handlers/text_handler.py
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import logging
from handlers import bonus, banners, companies, main_menu
from intent_classifier import classify_with_model
from keyboards.common import get_main_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Парсер ключевых слов
def keyword_intent(text: str) -> str:
    text = text.lower()
    if any(word in text for word in ['баланс', 'баллы', 'сколько баллов', 'бонусы']):
        return 'balance'
    if any(word in text for word in ['история', 'изменение', 'операции']):
        return 'history'
    if any(word in text for word in ['мои компании', 'какие компании', 'список компаний']):
        return 'companies'
    if any(word in text for word in ['акции', 'предложения', 'скидки']):
        return 'banners'
    if any(word in text for word in ['реферальная', 'программа']):
        return 'bonus'
    return None

async def handle_intent(message: types.Message, intent: str, state: FSMContext):
    user_id = message.from_user.id
    if intent == 'balance':
        await bonus.bonus_balance_start(message, state)
    elif intent == 'history':
        await bonus.bonus_history_start(message, state)
    elif intent == 'companies':
        # Передаём "текст" как в главном меню, но можно вызвать напрямую
        # Используем тот же метод, что и при нажатии кнопки
        await main_menu.handle_main_menu(message, state, text="🏢 Мои компании")
    elif intent == 'banners':
        await main_menu.handle_main_menu(message, state, text="🎁 Текущие акции")
    elif intent == 'bonus':
        await main_menu.handle_main_menu(message, state, text="🎁 Реферальная программа")
    else:
        await message.answer("Извините, я не понял ваш запрос. Попробуйте воспользоваться кнопками меню.", 
                             reply_markup=get_main_keyboard(user_id))

@router.message(F.text)
async def text_handler(message: types.Message, state: FSMContext):
    # Игнорируем команды (они обрабатываются другими роутерами)
    if message.text.startswith('/'):
        return
    user_id = message.from_user.id
    text = message.text
    logger.info(f"Получен текст от {user_id}: {text}")
    # 1. Сначала парсер ключевых слов
    intent = keyword_intent(text)
    if intent:
        logger.info(f"Парсер определил интент: {intent}")
        await handle_intent(message, intent, state)
        return
    # 2. Если не определился, используем модель
    logger.info("Парсер не сработал, вызываем модель")
    intent = classify_with_model(text)
    logger.info(f"Модель определила интент: {intent}")
    await handle_intent(message, intent, state)