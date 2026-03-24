import os
import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from dotenv import load_dotenv, set_key
from pathlib import Path
from utils.helpers import is_admin

router = Router()
logger = logging.getLogger(__name__)

class SetBitrixKey(StatesGroup):
    waiting_for_key = State()

@router.message(Command("set_bitrix_key"))
async def cmd_set_bitrix_key(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return
    await state.set_state(SetBitrixKey.waiting_for_key)
    await message.answer("Введите новый BITRIX_API_KEY:")

@router.message(SetBitrixKey.waiting_for_key)
async def process_new_key(message: types.Message, state: FSMContext):
    new_key = message.text.strip()
    if not new_key:
        await message.answer("❌ Ключ не может быть пустым. Попробуйте снова.")
        return
    # Обновляем переменную в текущем окружении
    os.environ['BITRIX_API_KEY'] = new_key
    # Находим путь к .env (предполагаем, что он в корне проекта)
    env_path = Path(__file__).parent.parent.parent / '.env'
    if env_path.exists():
        try:
            set_key(str(env_path), 'BITRIX_API_KEY', new_key)
            await message.answer(f"✅ BITRIX_API_KEY успешно обновлён на: `{new_key}`", parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Ошибка записи в .env: {e}")
            await message.answer("✅ Ключ обновлён в памяти, но не удалось записать в .env. Изменения сохранятся до перезапуска.")
    else:
        await message.answer("⚠️ Файл .env не найден, ключ обновлён только в памяти.")
    await state.clear()