import re
import time
import logging
import os
import json
import httpx
import database as db
import soap_client
import promo_client

logger = logging.getLogger(__name__)

SEARCH_URL    = os.getenv("SEARCH_URL",     "https://stalker-co.ru/bitrix/tools/mlk_search_ajax.php")
LLM_SERVER_URL = os.getenv("LLM_SERVER_URL", "http://31.76.227.1:8000/v1/chat/completions")
LLM_MODEL     = os.getenv("LLM_MODEL",      "cotype-nano-Q4_K_M.gguf")
BASE_WEB_URL  = os.getenv("BASE_WEB_URL",   "https://bot.stalker-co.ru")
LLM_TIMEOUT   = 60

# Категории каталога для финального fallback (Название|/url/), одна на строку
_CATEGORIES_RAW = os.getenv("CATALOG_CATEGORIES", (
    "Краски для волос|/catalog/kraski-dlya-volos/\n"
    "Уход за волосами|/catalog/ukhod-za-volosami/\n"
    "Уход за кожей лица|/catalog/ukhod-za-kozhej/\n"
    "Стайлинг|/catalog/stajling/\n"
    "Расчёски и инструменты|/catalog/instrumenty/\n"
    "Шампуни|/catalog/shampuni/\n"
    "Маски и сыворотки|/catalog/maski/\n"
    "Парфюмерия|/catalog/parfyumeriya/"
))

_CATEGORIES: list[tuple[str, str]] = []
for _line in _CATEGORIES_RAW.strip().splitlines():
    _parts = _line.strip().split('|', 1)
    if len(_parts) == 2:
        _CATEGORIES.append((_parts[0].strip(), _parts[1].strip()))

# ── Per-user сессии ────────────────────────────────────────────────────────────
# Хранятся в памяти до рестарта бота (по требованию пользователя).
_sessions: dict[int, dict] = {}

_MAX_HISTORY        = 8   # сообщений в истории для LLM
_MAX_CLARIFICATIONS = 3   # попыток уточнить до сдачи

_SEARCH_INTRO_RE = re.compile(
    r'^(найди|поищи|подбери|посоветуй|хочу купить|ищу|нужен|нужна|нужно|покажи)\s+',
    re.IGNORECASE,
)


def _session(user_id: int) -> dict:
    if user_id not in _sessions:
        _sessions[user_id] = {
            'messages':           [],   # {'role': 'user'|'assistant', 'content': str}
            'pending_search':     None, # накопленный поисковый запрос
            'clarification_count': 0,
        }
    return _sessions[user_id]


def _add_msg(user_id: int, role: str, content: str) -> None:
    s = _session(user_id)
    s['messages'].append({'role': role, 'content': content})
    if len(s['messages']) > _MAX_HISTORY:
        s['messages'] = s['messages'][-_MAX_HISTORY:]


def _reset_search(user_id: int) -> None:
    s = _session(user_id)
    s['pending_search']      = None
    s['clarification_count'] = 0


def _search_ok(result: str) -> bool:
    if not result:
        return False
    bad = ["ничего не найдено", "не удалось выполнить поиск", "произошла ошибка"]
    return not any(b in result.lower() for b in bad)


def _strip_intro(text: str) -> str:
    return _SEARCH_INTRO_RE.sub('', text.strip()).strip() or text.strip()


# ── LLM helpers ───────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = (
    "Ты — помощник интернет-магазина профессиональной косметики. "
    "Товар по запросу клиента не найден — запрос слишком короткий или неточный. "
    "Задай ОДИН открытый вопрос: попроси клиента описать подробнее что именно он ищет. "
    "Правила: "
    "1. Один вопрос — не два и не три. "
    "2. Вопрос должен быть открытым — пусть клиент сам опишет товар своими словами. "
    "3. Не угадывай назначение, не сужай ответ вариантами. "
    "4. Не рассуждай, не объясняй, не извиняйся. "
    "5. Учитывай историю переписки — не спрашивай то, что уже сказано. "
    "Шаблон ответа: «Уточните, пожалуйста: [открытый вопрос о товаре]?»"
)


def strip_reasoning(text: str) -> str:
    if not text:
        return text
    text = re.sub(r'<\s*(think|thinking|reason|reasoning)\s*>.*?<\s*/\s*\1\s*>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<\s*(think|thinking|reason|reasoning)\s*>.*', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'```[a-z]*', '', text, flags=re.IGNORECASE)
    text = text.replace('```', '')
    text = re.sub(r'^\s*(ключевые слова|ответ|результат|keywords|answer)\s*[:\-–]\s*', '', text.strip(), flags=re.IGNORECASE)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return lines[-1].strip(' \t"\'`«».') if lines else text.strip()


def _fallback_question(context_query: str) -> str:
    return "Уточните, пожалуйста: опишите подробнее что именно ищете — для чего, какой результат нужен?"


async def _ask_clarification(user_id: int, current_text: str) -> str:
    """Отправляет историю разговора в LLM и получает уточняющий вопрос."""
    s = _session(user_id)
    # История без последнего сообщения (оно уже добавлено в _add_msg раньше)
    history = s['messages'][:-1]

    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]
    # Фильтруем HTML из истории — модели нужен только текст
    for m in history:
        content = m['content']
        if content.startswith('<'):
            content = '[результаты поиска показаны]'
        messages.append({"role": m['role'], "content": content})
    messages.append({"role": "user", "content": current_text})

    try:
        async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
            resp = await client.post(LLM_SERVER_URL, json={
                "model":       LLM_MODEL,
                "messages":    messages,
                "temperature": 0.2,
                "max_tokens":  80,
            }, headers={"Content-Type": "application/json"})
            if resp.status_code == 200:
                raw    = resp.json()["choices"][0]["message"]["content"]
                answer = strip_reasoning(raw)
                if answer and len(answer) >= 5:
                    return answer
    except httpx.TimeoutException:
        logger.error("LLM timeout in _ask_clarification")
    except Exception as e:
        logger.error(f"LLM error in _ask_clarification: {e}")

    return _fallback_question(s.get('pending_search') or current_text)


def _show_categories(accumulated_query: str) -> str:
    """Возвращает HTML со списком категорий, релевантных накопленному запросу."""
    q = accumulated_query.lower()

    # Ранжируем категории по совпадению ключевых слов
    scored: list[tuple[int, str, str]] = []
    kw_map = {
        "краски для волос":       ["краск", "окраш", "цвет", "тонир", "колор"],
        "уход за волосами":       ["волос", "шампун", "бальзам", "кондиц", "маск"],
        "уход за кожей лица":     ["крем", "сыворотк", "лосьон", "уход", "лицо", "кожа"],
        "стайлинг":               ["укладк", "лак", "муссе", "гель", "стайл"],
        "расчёски и инструменты": ["расчес", "щетк", "расческ", "инструм", "утюж", "плойк"],
        "шампуни":                ["шампун", "мыть голов", "волос"],
        "маски и сыворотки":      ["маск", "сыворотк", "ампул", "концентрат"],
        "парфюмерия":             ["парфюм", "духи", "аромат", "туалетн"],
    }

    for name, url in _CATEGORIES:
        keywords = kw_map.get(name.lower(), [])
        score = sum(1 for kw in keywords if kw in q)
        scored.append((score, name, url))

    scored.sort(key=lambda x: -x[0])
    top = scored[:4]

    links = ''.join(
        f'<a href="{url}" class="mlk-cat-link">{name}</a>'
        for _, name, url in top
    )
    return (
        '<div class="mlk-chat-categories">'
        '<p>К сожалению, точного совпадения не нашлось. '
        'Возможно, вас заинтересуют эти разделы:</p>'
        f'<div class="mlk-cat-links">{links}</div>'
        '</div>'
    )


# ── Глобальная LLM-модель для extract_brand ───────────────────────────────────
_llm_instance = None
try:
    from intent_classifier import load_llm_model, extract_brand
    _llm_instance = load_llm_model()
except Exception as e:
    logger.warning(f"Не удалось загрузить LLM для извлечения бренда: {e}")


# ── Основной обработчик ────────────────────────────────────────────────────────

async def handle_web_message(user_id: int, message_text: str, context: str = "", partner_id: str = None) -> str:
    text       = message_text.strip()
    text_lower = text.lower()

    if len(text_lower) < 2:
        return "Пожалуйста, введите более длинный запрос."

    # Сохраняем сообщение пользователя в историю
    _add_msg(user_id, 'user', text)

    # ── Явные команды — сбрасывают поисковый контекст ─────────────────────────
    if any(w in text_lower for w in ["акци", "скидк", "промо"]):
        _reset_search(user_id)
        reply = await handle_banners(user_id, partner_id, text)
        _add_msg(user_id, 'assistant', '[акции]')
        return reply

    if any(w in text_lower for w in ["баланс", "бонусный", "бонусы"]):
        _reset_search(user_id)
        reply = await handle_balance(user_id)
        _add_msg(user_id, 'assistant', reply)
        return reply

    if any(w in text_lower for w in ["истори", "операци", "заказ"]):
        _reset_search(user_id)
        reply = await handle_history(user_id)
        _add_msg(user_id, 'assistant', reply)
        return reply

    if any(w in text_lower for w in ["компани", "контрагент", "организаци"]):
        _reset_search(user_id)
        reply = await handle_companies(user_id)
        _add_msg(user_id, 'assistant', reply)
        return reply

    if any(w in text_lower for w in ["подписк", "подписаться", "рассылка"]):
        _reset_search(user_id)
        return "Управление подписками доступно в личном кабинете на сайте."

    if any(w in text_lower for w in ["помощ", "help", "что ты умеешь", "команд"]):
        _reset_search(user_id)
        return get_help_text()

    s = _session(user_id)

    # ── Если явно новый поиск — сбрасываем предыдущий контекст ───────────────
    if _SEARCH_INTRO_RE.match(text) and s['pending_search']:
        _reset_search(user_id)

    # ── Режим ожидания ответа на уточняющий вопрос ────────────────────────────
    if s['pending_search']:
        # Накапливаем: добавляем ответ пользователя к ранее собранному запросу
        combined = s['pending_search'] + ' ' + _strip_intro(text)
        s['pending_search'] = combined

        search_result = await handle_search(user_id, combined, context)
        if _search_ok(search_result):
            _reset_search(user_id)
            _add_msg(user_id, 'assistant', '[результаты поиска]')
            return search_result

        s['clarification_count'] += 1

        if s['clarification_count'] >= _MAX_CLARIFICATIONS:
            # Исчерпали попытки — показываем похожие категории
            _reset_search(user_id)
            reply = _show_categories(combined)
            _add_msg(user_id, 'assistant', '[категории]')
            return reply

        # Ещё одно уточнение с полной историей
        question = await _ask_clarification(user_id, text)
        _add_msg(user_id, 'assistant', question)
        return question

    # ── Обычный поиск ─────────────────────────────────────────────────────────
    search_result = await handle_search(user_id, text, context)
    if _search_ok(search_result):
        _reset_search(user_id)
        _add_msg(user_id, 'assistant', '[результаты поиска]')
        return search_result

    # Поиск не дал результатов — начинаем цикл уточнений
    s['pending_search']      = _strip_intro(text)
    s['clarification_count'] = 0

    question = await _ask_clarification(user_id, text)
    _add_msg(user_id, 'assistant', question)
    return question


# ── Поиск товаров ─────────────────────────────────────────────────────────────

async def handle_search(user_id: int, query: str, context: str) -> str:
    search_query = _SEARCH_INTRO_RE.sub('', query.strip()).strip() or query.strip()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(SEARCH_URL, data={
                "query":   search_query,
                "limit":   4,
                "ai_mode": 1,
            })
            if resp.status_code != 200:
                return "Не удалось выполнить поиск."
            data    = resp.json()
            results = data.get("results", [])
            if not results:
                return f"По запросу «{search_query}» ничего не найдено."

            html_parts = ['<div class="mlk-chat-products">']
            for item in results:
                image_url    = item.get("image", "")
                img_tag      = f'<img src="{image_url}" class="mlk-chat-product-img" />' if image_url else ''
                article      = item.get("article", "")
                article_html = f'<span>{article}</span>' if article else ''
                html_parts.append(
                    f'<div class="mlk-chat-product">'
                    f'{img_tag}'
                    f'<div class="mlk-chat-product-info">'
                    f'<a href="{item.get("url","#")}" target="_blank">{item.get("name","")}</a>'
                    f'{article_html}'
                    f'</div></div>'
                )
            html_parts.append('</div>')
            return ''.join(html_parts)
    except Exception as e:
        logger.error(f"Search error: {e}")
        return "Произошла ошибка при поиске."


# ── Прочие обработчики ────────────────────────────────────────────────────────

async def handle_banners(user_id: int, partner_id: str = None, text: str = "") -> str:
    if not partner_id:
        return "Не указан партнёрский идентификатор. Проверьте настройки профиля."

    brand_filter = None
    if text and _llm_instance:
        try:
            brand_filter = extract_brand(text, _llm_instance)
        except Exception:
            pass
    if not brand_filter:
        match = re.search(r'по\s+(\w+)', text, re.IGNORECASE)
        if match:
            brand_filter = match.group(1).capitalize()

    web_app_url = f"{BASE_WEB_URL}/promo/{partner_id}"
    if brand_filter:
        web_app_url += f"?brand={brand_filter}"

    brand_text = f' по бренду {brand_filter}' if brand_filter else ''
    return (
        f'<div class="mlk-chat-promo-message">'
        f'<p>Вот акции специально для вас{brand_text}!</p>'
        f'<div class="mlk-chat-promo-button" data-url="{web_app_url}">'
        f'<span>Открыть акции</span>'
        f'</div></div>'
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


# handle_general оставлен как алиас для совместимости с внешними вызовами
async def handle_general(user_id: int, text: str, context: str) -> str:
    return await _ask_clarification(user_id, text)
