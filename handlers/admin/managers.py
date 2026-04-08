from aiogram import Router, types
from aiogram.filters import Command
from utils.helpers import is_admin

router = Router()

@router.message(Command("manage_managers"))
async def cmd_manage_managers(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("✅ Команда /manage_managers работает! (тестовая версия)")