from aiogram import Router, types
from aiogram.filters import Command
from utils.helpers import is_admin

router = Router()

@router.message(Command("manage_admins"))
async def cmd_manage_admins(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await message.answer("✅ Команда /manage_admins работает! (тестовая версия)")