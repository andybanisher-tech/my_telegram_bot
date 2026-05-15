import re
import logging
import os
import json
import httpx
import database as db
import soap_client
import promo_client

logger = logging.getLogger(__name__)

SEARCH_URL = os.getenv("SEARCH_URL", "https://dev.stalker-co.ru/ajax/search.php")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://31.76.227.1:8000/v1/chat/completions")
LLM_MODEL = os.getenv("LLM_MODEL", "cotype-nano-Q4_K_M.gguf")
BASE_WEB_URL = os.getenv("BASE_WEB_URL", "https://bot.stalker-co.ru")
LLM_TIMEOUT = 60  # секунд

# Глобальная LLM-модель для extract_brand
_llm_instance = None
try:
    from intent_classifier import load_llm_model, extract_brand
    _llm_instance = load_llm_model()
except Exception as e:
    logger.warning(f"Не удалось загрузить LLM для извлечения бренда: {e}")

async def handle_web_message(user_id: int, message_text: str, context: str = "", partner_id: str = None) -> str:
    text = message_text.strip().lower()
    if len(text) < 2:
        return "Пожалуйста, введите более длинный запрос."

    # Явные команды
    if any(w in text for w in ["акци", "скидк", "промо"]):
        return await handle_banners(user_id, partner_id, message_text)
    if any(w in text for w in ["баланс", "бонусный", "бонусы"]):
        return await handle_balance(user_id)
    if any(w in text for w in ["истори", "операци", "заказ"]):
        return await handle_history(user_id)
    if any(w in text for w in ["компани", "контрагент", "организаци"]):
        return await handle_companies(user_id)
    if any(w in text for w in ["подписк", "подписаться", "рассылка"]):
        return "Управление подписками доступно в личном кабинете на сайте."
    if any(w in text for w in ["помощ", "help", "что ты умеешь", "команд"]):
        return get_help_text()

    # По умолчанию пробуем поиск товара
    search_result = await handle_search(user_id, message_text, context)
    if "ничего не найдено" not in search_result and "Не удалось выполнить поиск" not in search_result and search_result != "":
        return search_result

    # Если поиск не дал результатов – отправляем в LLM
    return await handle_general(user_id, message_text, context)


async def handle_search(user_id: int, query: str, context: str) -> str:
    # Убираем вводные слова
    search_query = re.sub(r'(найди|поищи|подбери|посоветуй|хочу купить|ищу|нужен|нужна|нужно|покажи)\s*', '', query, flags=re.IGNORECASE).strip()
    if not search_query:
        search_query = query.strip()
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


async def handle_banners(user_id: int, partner_id: str = None, text: str = "") -> str:
    if not partner_id:
        return "Не указан партнёрский идентификатор. Проверьте настройки профиля."
    
    # Определяем бренд
    brand_filter = None
    if text and _llm_instance:
        try:
            brand_filter = extract_brand(text, _llm_instance)
        except:
            pass
    if not brand_filter:
        match = re.search(r'по\s+(\w+)', text, re.IGNORECASE)
        if match:
            brand_filter = match.group(1).capitalize()
    
    web_app_url = f"{BASE_WEB_URL}/promo/{partner_id}"
    if brand_filter:
        web_app_url += f"?brand={brand_filter}"
    
    # Возвращаем HTML с кнопкой
    brand_text = f' по бренду {brand_filter}' if brand_filter else ''
    return (
        f'<div class="mlk-chat-promo-message">'
        f'<p>Вот акции специально для вас{brand_text}!</p>'
        f'<div class="mlk-chat-promo-button" data-url="{web_app_url}">'
        f'<span>Открыть акции</span>'
        f'</div>'
        f'</div>'
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
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(url, json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.5,
                "max_tokens": 200
            }, headers={"Content-Type": "application/json"})
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            logger.error(f"LLM returned status {resp.status_code}: {resp.text}")
            return "Извините, не могу сейчас ответить."
    except httpx.TimeoutException:
        logger.error("LLM timeout")
        return "Сервер временно перегружен, пожалуйста, попробуйте позже."
    except Exception as e:
        logger.error(f"LLM error: {e}")
        return "Извините, произошла ошибка."