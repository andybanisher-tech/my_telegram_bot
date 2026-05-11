cat > ~/my_telegram_bot/web_chat_handler.py << 'ENDOFFILE'
import re
import logging
import os
import httpx
import database as db
import soap_client

logger = logging.getLogger(__name__)

async def handle_web_message(user_id: int, message_text: str, context: str = "") -> str:
    text = message_text.strip().lower()
    if len(text) < 2:
        return "Пожалуйста, введите более длинный запрос."

    # Простая проверка ключевых слов вместо модели
    if any(word in text for word in ["баланс", "бонусный", "бонусы"]):
        return await handle_balance(user_id)
    if any(word in text for word in ["истори", "операци", "заказ"]):
        return await handle_history(user_id)
    if any(word in text for word in ["компани", "контрагент", "организаци"]):
        return await handle_companies(user_id)
    if any(word in text for word in ["акци", "скидк", "промо"]):
        return await handle_banners(user_id, message_text)
    if any(word in text for word in ["подписк", "подписаться", "рассылка"]):
        return "Управление подписками доступно в личном кабинете на сайте."
    if any(word in text for word in ["помощ", "help", "что ты умеешь", "команд"]):
        return get_help_text()
    
    # Если ничего не подошло – отправляем в LLM
    return await handle_general(user_id, message_text, context)

async def handle_balance(user_id: int) -> str:
    companies = db.get_user_companies(user_id)
    if not companies:
        return "У вас нет привязанных компаний. Пожалуйста, обратитесь к менеджеру."
    code = companies[0]['code']
    data = await soap_client.get_bonus_balance(code)
    if data and "SumBonus" in data:
        return f"Ваш бонусный баланс: {data['SumBonus']} баллов."
    return "Не удалось получить баланс."

async def handle_history(user_id: int) -> str:
    return "История операций доступна в личном кабинете на сайте."

async def handle_companies(user_id: int) -> str:
    companies = db.get_user_companies(user_id)
    if not companies:
        return "У вас нет привязанных компаний. Пожалуйста, обратитесь к менеджеру."
    lines = ["Ваши компании:"]
    for comp in companies:
        lines.append(f"• {comp['name']} (код {comp['code']})")
    return "\n".join(lines)

async def handle_banners(user_id: int, text: str) -> str:
    # Проверка менеджера и извлечение ID партнёра (если есть)
    try:
        from utils.helpers import is_manager
        if is_manager(user_id):
            match = re.search(r'([a-zA-Zа-яА-Я])(\d+)', text)
            if match:
                partner_id = match.group(1).upper() + match.group(2)
                return await handle_partner_actions(partner_id)
    except:
        pass
    return "Актуальные акции доступны на сайте в разделе «Акции»."

async def handle_partner_actions(partner_id: str) -> str:
    info = await soap_client.get_partner_by_id(partner_id)
    if not info:
        return f"Контрагент с ID {partner_id} не найден."
    return f"Контрагент: {info.get('name', partner_id)}. Акции доступны на сайте."

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

async def handle_general(user_id: int, text: str, context: str) -> str:
    url = os.getenv("LLM_SERVER_URL", "http://31.76.227.1:8000/v1/chat/completions")
    model = os.getenv("LLM_MODEL", "cotype-nano-Q4_K_M.gguf")
    prompt = f"Клиент (ID {user_id}). Контекст: {context}. Вопрос: {text}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 200
            }, headers={"Content-Type": "application/json"})
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            return "Извините, не могу сейчас ответить."
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Извините, произошла ошибка."
ENDOFFILE