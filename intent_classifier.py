# intent_classifier.py
import os
import logging
from typing import Optional
from llama_cpp import Llama

logger = logging.getLogger(__name__)

# Конфигурация из .env
MODEL_PATH = os.getenv("MODEL_PATH")

# Системный промпт для модели
SYSTEM_PROMPT = """Ты – классификатор намерений для телеграм-бота. 
Пользователь пишет сообщение, а ты должен определить, какое действие он хочет выполнить. 
Ответь только одним словом из списка: balance, history, companies, banners, bonus, other.

- balance: если пользователь спрашивает о количестве баллов, балансе, бонусах.
- history: если пользователь хочет посмотреть историю начислений/списаний баллов.
- companies: если пользователь хочет посмотреть свои компании.
- banners: если пользователь хочет посмотреть акции, предложения.
- bonus: если пользователь интересуется реферальной программой.
- other: если ничего из перечисленного не подходит.

Примеры:
Пользователь: сколько у меня баллов? -> balance
Пользователь: покажи историю -> history
Пользователь: мои компании -> companies
Пользователь: какие сейчас акции -> banners
Пользователь: реферальная программа -> bonus
Пользователь: привет -> other

Теперь определи намерение для сообщения: """

# Инициализируем модель (глобально, при импорте)
llm = None
def init_model():
    global llm
    if llm is None and MODEL_PATH:
        try:
            llm = Llama(model_path=MODEL_PATH, n_ctx=512, n_threads=2, verbose=False)
            logger.info("Модель Qwen загружена")
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            llm = None
    return llm

def classify_with_model(text: str) -> str:
    """Отправляет текст в модель и возвращает интент."""
    llm = init_model()
    if not llm:
        return "other"
    prompt = SYSTEM_PROMPT + f"\nПользователь: {text}\nОтвет:"
    try:
        response = llm(prompt, max_tokens=10, temperature=0, stop=["\n"])
        intent = response['choices'][0]['text'].strip().lower()
        if intent in ['balance', 'history', 'companies', 'banners', 'bonus', 'other']:
            return intent
        else:
            return "other"
    except Exception as e:
        logger.error(f"Ошибка инференса модели: {e}")
        return "other"