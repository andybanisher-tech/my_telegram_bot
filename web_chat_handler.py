import re
import logging
import os
import httpx
import database as db
import soap_client
from intent_classifier import extract_brand, load_llm_model

logger = logging.getLogger(__name__)

SEARCH_URL = os.getenv("SEARCH_URL", "https://dev.stalker-co.ru/ajax/search.php")
BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://news-bot-stalker.ru")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://31.76.227.1:8000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "cotype-nano-Q4_K_M.gguf")

# Загружаем модель один раз для extract_brand
_llm_instance = load_llm_model()

async def handle_web_message(user_id: int, message_text: str, context: str = "", partner_id: str = None) -> str:
    text = message_text.strip().lower()
    if len(text) < 2:
        return "Пожалуйста, введите более длинный запрос."

    # Поиск товаров
    if any(w in text for w in ["найди", "поищи", "подбери", "посоветуй", "хочу купить"]):
        return await handle_search(user_id, message_text, context)

    # Акции
    if any(w in text for w in ["акци", "скидк", "промо"]):
        return await handle_banners(user_id, text, partner_id)

    # Баланс
    if any(w in text for w in ["баланс", "бонусный", "бонусы"]):
        return await handle_balance(user_id)

    # История
    if any(w in text for w in ["истори", "операци", "заказ"]):
        return await handle_history(user_id)

    # Компании
    if any(w in text for w in ["компани", "контрагент", "организаци"]):
        return await handle_companies(user_id)

    # Подписки
    if any(w in text for w in ["подписк", "подписаться", "рассылка"]):
        return "Управление подписками доступно в личном кабинете на сайте."

    # Помощь
    if any(w in text for w in ["помощ", "help", "что ты умеешь", "команд"]):
        return get_help_text()

    # Общий вопрос – LLM
    return await handle_general(user_id, message_text, context)


async def handle_search(user_id: int, query: str, context: str) -> str:
    search_query = re.sub(r'(найди|поищи|подбери|посоветуй|хочу купить)\s*', '', query, flags=re.IGNORECASE).strip()
    if not search_query:
        return "Пожалуйста, уточните, что вы хотите найти."
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(SEARCH_URL, params={"query": search_query, "limit": 3})
            if resp.status_code != 200:
                return "Не удалось выполнить поиск."
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return f"По запросу «{search_query}» ничего не найдено."
            html_parts = ['<div class="mlk-chat-products">']
            for item in results:
                image_url = item.get("image", "")
                img_tag = f'<img src="{image_url}" class="mlk-chat-product-img" />' if image_url else ''
                html_parts.append(f'''
                <div class="mlk-chat-product">
                    {img_tag}
                    <div class="mlk-chat-product-info">
                        <a href="{item.get("url", "#")}" target="_blank">{item.get("name", "")}</a>
                        <span>{item.get("article", "")}</span>
                    </div>
                </div>
                ''')
            html_parts.append('</div>')
            return ''.join(html_parts)
    except Exception as e:
        logger.error(f"Search error: {e}")
        return "Произошла ошибка при поиске."


async def handle_banners(user_id: int, text: str, partner_id: str = None) -> str:
    if not partner_id:
        return "Не указан партнёрский идентификатор. Проверьте настройки профиля."

    # Извлекаем бренд из сообщения с помощью LLM
    brand_filter = extract_brand(text, _llm_instance) if _llm_instance else None

    # Формируем URL Web App
    web_app_url = f"{BASE_WEB_URL}/promo/{partner_id}"
    if brand_filter:
        web_app_url += f"?brand={brand_filter}"

    return (
        '🎁 <a href="' + web_app_url + '" target="_blank">Открыть персональные акции</a>'
        + (' (бренд: ' + brand_filter + ')' if brand_filter else '')
    )


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


def get_help_text() -> str:
    return (
        "Я могу помочь вам со следующими запросами:\n"
        "• Баланс баллов\n"
        "• История операций\n"
        "• Мои компании\n"
        "• Акции и скидки\n"
        "• Найди / подбери товар\n"
        "• Реферальная программа\n"
        "• Помощь"
    )


async def handle_general(user_id: int, text: str, context: str) -> str:
    url = LLM_SERVER_URL
    model = LLM_MODEL
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