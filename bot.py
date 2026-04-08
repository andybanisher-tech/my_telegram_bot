import asyncio
import os
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from dotenv import load_dotenv
from pathlib import Path

import database as db
import soap_client
import bitrix_client
from handlers.admin import admins as admin_admins
from handlers.admin import managers as admin_managers
from handlers import (
    start, main_menu, companies, subscriptions, banners, partner_actions, bonus,
    admin_news, admin_categories, admin_admins, admin_stats, admin_managers,
    admin_set_bitrix_key, text_handler  # новый
)
from utils.set_bot_commands import set_bot_commands
from intent_classifier import load_llm_model  # для предзагрузки модели


# Загружаем переменные окружения
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("Токен не найден! Проверьте файл .env")

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация базы данных
db.init_db()

# Инициализация модели (чтобы загрузилась при старте, не обязательно)
load_llm_model()

# Создаём объекты бота и диспетчера
storage = MemoryStorage()
bot = Bot(token=TOKEN)
dp = Dispatcher(storage=storage)

# Регистрируем все роутеры
dp.include_router(start.router)
dp.include_router(main_menu.router)
dp.include_router(companies.router)
dp.include_router(subscriptions.router)
dp.include_router(banners.router)
dp.include_router(partner_actions.router)
dp.include_router(bonus.router)
dp.include_router(text_handler.router)  # добавлен
dp.include_router(admin_news.router)
dp.include_router(admin_categories.router)
dp.include_router(admin_admins.router)
dp.include_router(admin_stats.router)
dp.include_router(admin_managers.router)
dp.include_router(admin_set_bitrix_key.router)


# ---------- ЗАПУСК ----------
async def main():
    await set_bot_commands(bot)
    logger.info("Бот запущен и готов к работе")
    await dp.start_polling(bot)
print("Зарегистрированные роутеры:")
for router in dp.sub_routers:
    print(router)        

if __name__ == "__main__":
    asyncio.run(main())

