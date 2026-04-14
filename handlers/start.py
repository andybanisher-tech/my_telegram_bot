from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database as db
from keyboards.common import get_main_keyboard

router = Router()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db.add_user(user.id, user.username, user.first_name)
    await message.answer(
        f"👋 Привет, {user.first_name}!\nВыбери действие:",
        reply_markup=get_main_keyboard(user.id)
    )