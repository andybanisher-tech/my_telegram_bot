import os
import logging
from typing import Optional
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

# Словарь синонимов для брендов (можно оставить или убрать)
BRAND_MAPPING = {
    "матрикс": "Matrix",
    "карал": "Kaaral",
    "орибе": "Oribe",
    "кутем": "Qtem",
    "виши": "Vichy",
    "лореаль": "L'Oreal",
    "л'ореаль": "L'Oreal",
    "ла рош позе": "La Roche Posay",
    "кевин мерфи": "Kevin Murphy",
    "кевин": "Kevin Murphy",
    "кеун": "Keune",
    "митчелл": "Mitchell",
    "иноа": "Inoa",
    "мажи": "Majirel",
    "диа": "Dia",
    "соколор": "Socolor",
    "кутран": "Cutrin",
    "бельарти": "Bellarti",
    "биогель": "Biogel",
    "репа": "Repair",
    "тефиа": "Tefia"
}

def extract_brand(text: str, llm) -> Optional[str]:
    """Извлекает название бренда из запроса, используя LLM, с fallback."""
    if not llm:
        return None
    text_lower = text.lower()
    # Fallback для часто встречающихся брендов
    for ru, en in BRAND_MAPPING.items():
        if ru in text_lower:
            return en
    # Промпт для LLM
    prompt = f"""Извлеки название бренда из запроса. Если бренд не упомянут, верни 'none'.
Примеры:
Запрос: покажи акции только по матрикс
Ответ: Matrix
Запрос: акции карал
Ответ: Kaaral
Запрос: скидки на Loreal
Ответ: L'Oreal
Запрос: покажи акции орибе
Ответ: Oribe
Запрос: акции кутем
Ответ: Qtem
Запрос: покажи акции матрикс
Ответ: Matrix
Запрос: покажи акции -> none
Запрос: {text}
Ответ:"""
    try:
        response = llm(prompt, max_tokens=20, stop=["\n"], temperature=0.0)
        raw = response["choices"][0]["text"].strip()
        if raw.lower() == "none" or not raw:
            return None
        raw = raw.rstrip('.,;:!?')
        return raw
    except Exception as e:
        logger.error(f"Ошибка при извлечении бренда: {e}")
        return None