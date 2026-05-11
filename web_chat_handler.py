from dotenv import load_dotenv
load_dotenv()

import re
import logging
import os
import httpx
import database as db
import soap_client
import promo_client

logger = logging.getLogger(__name__)

async def handle_web_message(user_id: int, message_text: str, context: str = "", partner_id: str = None) -> str:
    text = message_text.strip().lower()
    if len(text) < 2:
        return "Пожалуйста, введите более длинный запрос."

    if any(word in text for word in ["баланс", "бонусный", "бонусы"]):
        return await handle_balance(user_id)
    if any(word in text for word in ["истори", "операци", "заказ"]):
        return await handle_history(user_id)
    if any(word in text for word in ["компани", "контрагент", "организаци"]):
        return await handle_companies(user_id)
    if any(word in text for word in ["акци", "скидк", "промо"]):
        return await handle_banners(user_id, partner_id)  
    if any(word in text for word in ["подписк", "подписаться", "рассылка"]):
        return "Управление подписками доступно в личном кабинете на сайте."
    if any(word in text for word in ["помощ", "help", "что ты умеешь", "команд"]):
        return get_help_text()
    
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

async def handle_banners(user_id: int, partner_id: str = None) -> str:
    if not partner_id:
        return "Не указан партнёрский идентификатор. Проверьте настройки профиля."
    try:
        # Промо-клиент синхронный, убираем await
        promotions = promo_client.get_promotions_list_sync(partner_id)
        if promotions is None:
            return "Сервис акций временно недоступен."
        if not promotions:
            return "Для вашего контрагента нет активных акций."
        lines = ["Ваши персональные акции:"]
        for promo in promotions:
            lines.append(f"• {promo.get('name', 'Акция')} – подробнее на сайте")
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"Error fetching promotions: {e}")
        return "Не удалось загрузить акции. Попробуйте позже."

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