# web_chat_handler.py
import logging
from handlers.balance import get_balance
from handlers.history import get_history
from handlers.companies import get_companies
from handlers.banners import get_banners
from handlers.help import get_help_message
from handlers.general import ask_llm  # если такого файла нет, создадим
from database import get_user_companies

logger = logging.getLogger(__name__)

async def handle_web_message(user_id: int, message_text: str, context: str = "") -> str:
    text = message_text.strip().lower()
    if len(text) < 2:
        return "Пожалуйста, введите более длинный запрос."

    # Проверка привязки компаний (как в боте)
    companies = get_user_companies(user_id)
    if not companies and any(w in text for w in ["баланс", "истори", "компани", "акци", "скидк"]):
        return "У вас нет привязанных компаний. Пожалуйста, обратитесь к менеджеру."

    if any(w in text for w in ["баланс", "бонусный", "бонусы"]):
        return await get_balance(user_id)
    if any(w in text for w in ["истори", "операци", "заказ"]):
        return await get_history(user_id)
    if any(w in text for w in ["компани", "контрагент", "организаци"]):
        return await get_companies(user_id)
    if any(w in text for w in ["акци", "скидк", "промо"]):
        return await get_banners(user_id, text)
    if any(w in text for w in ["подписк", "подписаться", "рассылка"]):
        return "Управление подписками доступно в личном кабинете на сайте."
    if any(w in text for w in ["помощ", "help", "что ты умеешь", "команд"]):
        return get_help_message()

    return await ask_llm(user_id, text, context)