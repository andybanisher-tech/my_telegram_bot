import sys
import os
import logging
import asyncio
import re
import soap_client
import database as db
from handlers import main_menu
from intent_classifier import get_intent, extract_brand, load_llm_model
from utils.helpers import is_manager

logger = logging.getLogger(__name__)

# Загружаем модель один раз
_llm_instance = load_llm_model()

async def handle_web_message(user_id: int, message_text: str, context: str = "") -> str:
    """
    Обрабатывает сообщение из веб-чата, возвращает текстовый ответ.
    """
    if len(message_text) < 2:
        return "Пожалуйста, введите более длинный запрос."

    intent = get_intent(message_text, _llm_instance)
    logger.info(f"Web intent: {intent} for text: {message_text}")

    # Обработка интентов (аналогично text_handler.py)
    if intent == "balance":
        return await handle_balance(user_id)
    elif intent == "history":
        return await handle_history(user_id)
    elif intent == "companies":
        return await handle_companies(user_id)
    elif intent == "banners":
        if is_manager(user_id):
            partner_id = extract_partner_id(message_text)
            if partner_id:
                return await handle_partner_actions(user_id, partner_id)
        brand = extract_brand(message_text, _llm_instance) if _llm_instance else None
        return await handle_banners(user_id, brand)
    elif intent == "bonus":
        return await handle_bonus(user_id)
    elif intent == "subscribe" or intent == "subscriptions":
        return "Управление подписками доступно в личном кабинете на сайте."
    elif intent == "help":
        return get_help_text()
    else:
        # Если интент не определён, пробуем ответить через LLM
        return await handle_general_question(user_id, message_text, context)

# --- Вспомогательные функции ---

def extract_partner_id(text: str):
    match = re.search(r'([a-zA-Zа-яА-Я])(\d+)', text)
    if match:
        return match.group(1) + match.group(2)
    return None

async def handle_balance(user_id: int) -> str:
    companies = db.get_user_companies(user_id)
    if not companies:
        return "У вас нет выбранных компаний. Сначала выберите компании в разделе «Мои компании»."
    # Возвращаем баланс по первой компании (упрощённо)
    company_code = companies[0]['code']
    data = await soap_client.get_bonus_balance(company_code)
    if data and "SumBonus" in data:
        return f"Ваш бонусный баланс: {data['SumBonus']} баллов."
    return "Не удалось получить баланс."

async def handle_history(user_id: int) -> str:
    # Аналогично упрощённо
    return "История операций доступна в личном кабинете на сайте."

async def handle_companies(user_id: int) -> str:
    companies = db.get_user_companies(user_id)
    if not companies:
        return "У вас нет привязанных компаний. Пожалуйста, обратитесь к менеджеру."
    lines = ["Ваши компании:"]
    for comp in companies:
        lines.append(f"• {comp['name']} (код {comp['code']})")
    return "\n".join(lines)

async def handle_banners(user_id: int, brand: str = None) -> str:
    return "Актуальные акции доступны на сайте в разделе «Акции»."

async def handle_bonus(user_id: int) -> str:
    return "Информация о бонусах доступна в личном кабинете."

async def handle_partner_actions(user_id: int, partner_id: str) -> str:
    partner_info = await soap_client.get_partner_by_id(partner_id)
    if not partner_info:
        return f"Контрагент с ID {partner_id} не найден."
    return f"Контрагент: {partner_info.get('name', partner_id)}. Акции доступны на сайте."

def get_help_text() -> str:
    return (
        "Я могу помочь вам со следующими запросами:\n"
        "• Баланс баллов\n"
        "• История операций\n"
        "• Мои компании\n"
        "• Акции и скидки\n"
        "• Реферальная программа\n"
        "• Помощь"
    )

async def handle_general_question(user_id: int, message_text: str, context: str) -> str:
    """Отправляет запрос к LLM, если интент не распознан."""
    import httpx
    LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://31.76.227.1:8000/v1/chat/completions")
    LLM_MODEL = os.getenv("LLM_MODEL", "cotype-nano-Q4_K_M.gguf")
    prompt = f"Клиент (ID {user_id}). Контекст: {context}. Сообщение: {message_text}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                LLM_SERVER_URL,
                json={
                    "model": LLM_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.5,
                    "max_tokens": 200
                },
                headers={"Content-Type": "application/json"}
            )
            if resp.status_code != 200:
                return "Извините, не могу сейчас ответить."
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Извините, произошла ошибка."