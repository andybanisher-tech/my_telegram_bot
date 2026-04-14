import asyncio
from aiogram import Router, types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import soap_client
from . import main_menu
from utils.helpers import is_manager

router = Router()

class PartnerActions(StatesGroup):
    waiting_for_partner_id = State()

async def partner_actions_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    if not is_manager(user_id):
        await message.answer("⛔ У вас нет прав для этой команды.")
        return
    await state.set_state(PartnerActions.waiting_for_partner_id)
    await message.answer("Введите ID контрагента (например, С88201):")

@router.message(PartnerActions.waiting_for_partner_id)
async def partner_id_received(message: types.Message, state: FSMContext):
    partner_id = message.text.strip()
    if not partner_id:
        await message.answer("❌ ID не может быть пустым. Введите ID контрагента:")
        return
    await message.answer("⏳ Проверяем контрагента...")
    partner_info = await soap_client.get_partner_by_id(partner_id)
    if not partner_info:
        await message.answer("❌ Контрагент не найден. Проверьте ID и попробуйте снова.")
        return
    partner_name = partner_info.get('name', partner_id)
    await state.clear()
    await main_menu.show_banners_for_partner(message, state, partner_id, partner_name, message.chat.id)