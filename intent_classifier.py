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
    "balance": [
        "баланс", "баллы", "баллов", "сколько баллов", "бонусы", "бонусный счет"
    ],
    "history": [
        "история", "изменение баллов", "операции", "движение баллов"
    ],
    "companies": [
        "мои компании", "какие компании", "организации", "фирмы"
    ],
    "banners": [
        "акции", "предложения", "скидки", "актуальные акции", "что нового"
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
        "помощь", "что умеешь", "как пользоваться", "справка"
    ]
}

def get_intent_by_keywords(text: str) -> Optional[str]:
    """
    Проверяет, есть ли в тексте ключевые слова.
    Сначала ищет вхождение фразы как подстроки,
    затем — вхождение всех слов фразы как отдельных слов.
    """
    text_lower = text.lower()
    words = set(text_lower.split())
    for intent, phrases in KEYWORDS.items():
        for phrase in phrases:
            if phrase in text_lower:
                return intent
            # Проверяем, все ли слова из фразы присутствуют в запросе
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
    prompt = f"""Ты — классификатор намерений пользователя в телеграм-боте. 
Определи, какое из действий хочет выполнить пользователь. 
Варианты: balance (баланс баллов), history (история баллов), companies (мои компании), banners (текущие акции), bonus (реферальная программа), subscribe (подписаться на новости), subscriptions (мои подписки), help (помощь). 
Если ни одно не подходит, напиши ровно одно слово: unknown.
Пользователь написал: {text}
Твой ответ (только одно слово из списка или unknown):"""
    try:
        response = llm(prompt, max_tokens=10, stop=["\n"], temperature=0.0)
        answer = response["choices"][0]["text"].strip().lower()
        # Очистка от возможных знаков препинания
        answer = answer.strip('.,!?;:')
        if answer in INTENTS:
            return answer
        else:
            return None
    except Exception as e:
        logger.error(f"Ошибка при вызове LLM: {e}")
        return None

def get_intent(text: str, llm) -> Optional[str]:
    intent = get_intent_by_keywords(text)
    if intent:
        return intent
    return get_intent_by_llm(text, llm)