import os
import logging
from typing import Optional, Tuple
from llama_cpp import Llama

logger = logging.getLogger(__name__)

INTENTS = {
    "balance": "показать баланс бонусов",
    "history": "показать историю баллов",
    "companies": "показать мои компании",
    "banners": "показать текущие акции",
    "bonus": "показать реферальную программу",
    "subscribe": "подписаться на новости",
    "subscriptions": "управление подписками",
    "help": "помощь"
}

KEYWORDS = {
    "history": [
        "история", "изменение баллов", "операции", "движение баллов",
        "за что начислены баллы", "почему начислены баллы",
        "начислены баллы", "списание баллов", "зачисление баллов"
    ],
    "balance": [
        "баланс", "баллы", "баллов", "сколько баллов", "бонусы", "бонусный счет"
    ],
    "companies": [
        "мои компании", "какие компании", "организации", "фирмы"
    ],
    "banners": [
    "акции", "предложения", "скидки", "актуальные акции", "что нового",
    "распродажи", "распродажа"
],
    "bonus": [
        "реферальная", "программа", "партнерская", "рефералка"
    ],
    "subscribe": [
        "подписаться", "получать новости", "категории"
    ],
    "subscriptions": [
        "мои подписки", "отписаться", "управление подписками"
    ],
    "help": [
        "помощь", "что умеешь", "как пользоваться", "справка",
        "привет", "здравствуй", "что ты можешь"
    ]
}

def get_intent_by_keywords(text: str) -> Optional[str]:
    text_lower = text.lower()
    words = set(text_lower.split())
    priority_order = ["history", "balance", "companies", "banners", "bonus", "subscribe", "subscriptions", "help"]
    for intent in priority_order:
        for phrase in KEYWORDS.get(intent, []):
            if phrase in text_lower:
                return intent
            phrase_words = set(phrase.split())
            if phrase_words.issubset(words):
                return intent
    return None

def load_llm_model():
    model_path = os.getenv("MODEL_PATH")
    if not model_path or not os.path.exists(model_path):
        logger.warning("MODEL_PATH не задан или файл не найден. LLM недоступна.")
        return None
    try:
        llm = Llama(model_path=model_path, n_ctx=512, n_threads=2, verbose=False)
        logger.info("Модель Qwen загружена")
        return llm
    except Exception as e:
        logger.error(f"Ошибка загрузки модели: {e}")
        return None

def get_intent_by_llm(text: str, llm) -> Optional[str]:
    if not llm:
        return None
    prompt = f"""Определи, какое действие хочет выполнить пользователь.
Варианты ответов (только одно слово): balance, history, companies, banners, bonus, subscribe, subscriptions, help.
Если ни одно не подходит, ответь 'unknown'.
Пользователь написал: {text}
Ответ:"""
    try:
        response = llm(prompt, max_tokens=10, stop=["\n"], temperature=0.0)
        raw = response["choices"][0]["text"].strip().lower()
        raw = raw.split()[0] if raw else ""
        if raw in INTENTS:
            return raw
        else:
            logger.info(f"LLM вернул неподходящий интент: {raw}")
            return None
    except Exception as e:
        logger.error(f"Ошибка при вызове LLM: {e}")
        return None

def get_intent(text: str, llm) -> Optional[str]:
    intent = get_intent_by_keywords(text)
    if intent:
        return intent
    return get_intent_by_llm(text, llm)

def extract_brand(text: str, llm) -> Optional[str]:
    """Извлекает название бренда из запроса, используя fallback-словарь и LLM."""
    if not llm:
        return None

    text_lower = text.lower()

    # Максимально полный fallback-словарь
    brand_map = {
        # American Crew
        "американ крю": "American Crew",
        "американкрю": "American Crew",
        "american crew": "American Crew",
        "амкрю": "American Crew",
        # Matrix
        "матрикс": "Matrix",
        "матрик": "Matrix",
        "матрица": "Matrix",
        "matric": "Matrix",
        "matrix": "Matrix",
        "матракс": "Matrix",

        # Kaaral
        "карал": "Kaaral",
        "караль": "Kaaral",
        "каралл": "Kaaral",
        "kaaral": "Kaaral",
        "каралс": "Kaaral",

        # Oribe
        "орибе": "Oribe",
        "ориб": "Oribe",
        "oribe": "Oribe",

        # Qtem
        "кутем": "Qtem",
        "кутемс": "Qtem",
        "qtem": "Qtem",
        "кютем": "Qtem",

        # Vichy
        "виши": "Vichy",
        "виши": "Vichy",
        "vichy": "Vichy",

        # L'Oreal
        "лореаль": "L'Oreal",
        "лореал": "L'Oreal",
        "loreal": "L'Oreal",
        "лореаль париж": "L'Oreal",
        "l'oréal": "L'Oreal",
        "l'oreal": "L'Oreal",

        # La Roche Posay
        "ла рош позе": "La Roche Posay",
        "ларошпозе": "La Roche Posay",
        "la roche": "La Roche Posay",
        "ла рош": "La Roche Posay",
        "ларош": "La Roche Posay",

        # Kevin Murphy
        "кевин мерфи": "Kevin Murphy",
        "кевин": "Kevin Murphy",
        "kevin murphy": "Kevin Murphy",
        "кевин мёрфи": "Kevin Murphy",

        # Keune
        "кеун": "Keune",
        "кеуне": "Keune",
        "keune": "Keune",

        # Mitchell
        "митчелл": "Mitchell",
        "митчел": "Mitchell",
        "mitchell": "Mitchell",

        # Inoa
        "иноа": "Inoa",
        "inoa": "Inoa",

        # Majirel
        "мажи": "Majirel",
        "мажирель": "Majirel",
        "majirel": "Majirel",

        # Dia
        "диа": "Dia",
        "dia": "Dia",

        # Socolor
        "соколор": "Socolor",
        "socolor": "Socolor",

        # Cutrin
        "кутран": "Cutrin",
        "cutrin": "Cutrin",

        # Bellarti
        "бельарти": "Bellarti",
        "белларти": "Bellarti",
        "bellarti": "Bellarti",

        # Biogel
        "биогель": "Biogel",
        "biogel": "Biogel",

        # Repair
        "репа": "Repair",
        "репейр": "Repair",
        "repair": "Repair",

        # Tefia
        "тефиа": "Tefia",
        "тефия": "Tefia",
        "tefia": "Tefia",

        # Sesderma
        "сесдерма": "Sesderma",
        "sesderma": "Sesderma",

        # Martinex
        "мартинекс": "Martinex",
        "martinex": "Martinex",

        # Biotherme
        "биотерм": "Biotherm",
        "biotherm": "Biotherm",

        # Kydra
        "кюдра": "Kydra",
        "кудра": "Kydra",
        "kydra": "Kydra",

        # Arli's Story
        "арлис": "Arli's Story",
        "арли": "Arli's Story",
        "arli's story": "Arli's Story",

        # Favori
        "фавори": "Favori",
        "favori": "Favori",

        # Gernetic
        "жернетик": "Gernetic",
        "гернетик": "Gernetic",
        "gernetic": "Gernetic",

        # Gigi
        "гиги": "Gigi",
        "gigi": "Gigi",

        # Hair Sekta
        "хэир секта": "Hair Sekta",
        "хейр секта": "Hair Sekta",
        "hair sekta": "Hair Sekta",

        # Inspira
        "инспира": "Inspira",
        "inspira": "Inspira",

        # Janssen
        "янссен": "Janssen",
        "janssen": "Janssen",

        # Jufora
        "юфора": "Jufora",
        "jufora": "Jufora",

        # Klapp
        "клапп": "Klapp",
        "klapp": "Klapp",

        # Nook
        "нук": "Nook",
        "nook": "Nook",

        # Oribe (уже есть)
        # Paul Mitchell
        "пауль митчелл": "Paul Mitchell",
        "paul mitchell": "Paul Mitchell",

        # Peach Peel
        "пич пил": "Peach Peel",
        "peach peel": "Peach Peel",

        # Princess
        "принцесс": "Princess",
        "princess": "Princess",

        # PRX-T33
        "прх": "PRX-T33",
        "prx": "PRX-T33",
        "prx-t33": "PRX-T33",

        # QTFILL
        "кутфилл": "QTFILL",
        "qtfill": "QTFILL",

        # R+Co
        "р+co": "R+Co",
        "р+ко": "R+Co",
        "r+co": "R+Co",

        # Realook
        "реалук": "Realook",
        "realook": "Realook",

        # Repart
        "репарт": "Repart",
        "repart": "Repart",

        # Revi
        "реви": "Revi",
        "revi": "Revi",

        # Sofiderm
        "софидерм": "Sofiderm",
        "sofiderm": "Sofiderm",

        # Stylage
        "стиляж": "Stylage",
        "stylage": "Stylage",

        # Teoxane
        "теоксан": "Teoxane",
        "teoxane": "Teoxane",

        # You Be Lab
        "ю би лаб": "You Be Lab",
        "you be lab": "You Be Lab",

        # ZQ-II
        "зкью": "ZQ-II",
        "zq-ii": "ZQ-II",
    }

    # Проверяем вхождение любого из вариантов
    for key, value in brand_map.items():
        if key in text_lower:
            return value

    # Если не нашли, используем LLM
    prompt = f"""Извлеки название бренда из запроса. Если бренд не упомянут, верни 'none'.
Примеры:
покажи акции только по матрикс -> Matrix
акции карал -> Kaaral
скидки на Loreal -> L'Oreal
покажи акции орибе -> Oribe
акции кутем -> Qtem
покажи акции матрикс -> Matrix
акции виши -> Vichy
скидки ла рош позе -> La Roche Posay
акции кевин мерфи -> Kevin Murphy
покажи акции -> none
Запрос: {text}
Ответ:"""
    try:
        response = llm(prompt, max_tokens=20, stop=["\n"], temperature=0.0)
        raw = response["choices"][0]["text"].strip()
        logger.info(f"LLM ответ для бренда (raw): '{raw}'")
        if raw.lower() == "none" or not raw:
            return None
        raw = raw.rstrip('.,;:!?')
        return raw
    except Exception as e:
        logger.error(f"Ошибка при извлечении бренда: {e}")
        return None