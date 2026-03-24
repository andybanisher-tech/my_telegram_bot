import logging
from pathlib import Path
from llama_cpp import Llama

logger = logging.getLogger(__name__)

# Путь к файлу модели (скачать заранее)
MODEL_PATH = Path(__file__).parent / "models" / "qwen2.5-0.5b-instruct-q4_k_m.gguf"

# Глобальная переменная для модели (загружается один раз)
_model = None

def load_model():
    """Загружает модель, если она ещё не загружена."""
    global _model
    if _model is None:
        if not MODEL_PATH.exists():
            logger.error(f"Модель не найдена: {MODEL_PATH}")
            return False
        try:
            _model = Llama(
                model_path=str(MODEL_PATH),
                n_ctx=512,          # контекст для экономии памяти
                n_threads=2,        # кол-во потоков CPU
                n_gpu_layers=0,     # 0 = только CPU
                verbose=False
            )
            logger.info("Модель Qwen2.5-0.5B успешно загружена")
            return True
        except Exception as e:
            logger.error(f"Ошибка загрузки модели: {e}")
            return False
    return True

def get_intent_from_llm(user_text: str):
    """
    Отправляет текст пользователя в модель и возвращает интент.
    Возвращает строку: 'balance', 'history', 'companies', 'banners', 'bonus', 'unknown'.
    """
    if not load_model():
        return "unknown"

    prompt = f"""Ты — помощник Telegram-бота. Определи, какое действие хочет выполнить пользователь. Ответь только одним словом из списка: balance, history, companies, banners, bonus, unknown.

Текст пользователя: "{user_text}"

Твой ответ:"""
    try:
        output = _model(
            prompt,
            max_tokens=10,
            temperature=0,
            stop=["\n", "."],
            echo=False
        )
        text = output['choices'][0]['text'].strip().lower()
        # Возможные варианты
        if text in ['balance', 'history', 'companies', 'banners', 'bonus']:
            return text
        else:
            return "unknown"
    except Exception as e:
        logger.error(f"Ошибка вызова модели: {e}")
        return "unknown"