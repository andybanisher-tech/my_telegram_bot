from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards.common import get_main_keyboard
import database as db
import soap_client
from keyboards.common import get_main_keyboard, get_back_to_main_keyboard
from keyboards.companies import get_companies_keyboard
from states import states

router = Router()

async def show_main_menu(chat_id: int, bot, user_id: int):
    await bot.send_message(chat_id, "Главное меню:", reply_markup=get_main_keyboard(user_id))

async def process_companies_loading(user_id: int, phone: str, state: FSMContext, message: types.Message):
    await message.answer("⏳ Загружаем список компаний...")
    companies = await soap_client.get_companies_by_phone(phone)
    if not companies:
        await message.answer("❌ Не удалось загрузить компании. Попробуйте позже.")
        await state.clear()
        await show_main_menu(user_id, message.bot, user_id)
        return
    await state.update_data(companies=companies, selected_companies=[])
    await state.set_state(states.CompanyProcess.selecting_companies)
    await message.answer(
        "Найдены следующие организации. Выберите актуальные для вас (можно несколько):",
        reply_markup=get_companies_keyboard(companies, [])
    )

@router.message(F.contact)
async def handle_contact(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    contact = message.contact
    phone = contact.phone_number

    db.update_user_phone(user_id, phone)
    db.mark_user_verified(user_id)

    current_state = await state.get_state()
    if current_state == states.CompanyProcess.waiting_for_phone.state:
        await message.answer("✅ Номер подтверждён. Загружаем информацию...", reply_markup=types.ReplyKeyboardRemove())
        await process_companies_loading(user_id, phone, state, message)
    else:
        await message.answer("✅ Номер подтверждён.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await show_main_menu(user_id, message.bot, user_id)

@router.callback_query(lambda c: c.data.startswith('comp_'), states.CompanyProcess.selecting_companies)
async def process_company_selection(callback: types.CallbackQuery, state: FSMContext):
    idx = int(callback.data.split('_')[1])
    data = await state.get_data()
    selected = data.get('selected_companies', [])
    if idx in selected:
        selected.remove(idx)
    else:
        selected.append(idx)
    await state.update_data(selected_companies=selected)
    companies = data.get('companies', [])
    await callback.message.edit_reply_markup(
        reply_markup=get_companies_keyboard(companies, selected)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "companies_done", states.CompanyProcess.selecting_companies)
async def companies_done(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected_indices = data.get('selected_companies', [])
    companies = data.get('companies', [])
    selected_companies = [companies[i] for i in selected_indices]
    db.save_user_companies(callback.from_user.id, selected_companies)
    await callback.message.edit_text("✅ Выбор сохранён.")
    await state.clear()
    await show_main_menu(callback.message.chat.id, callback.bot, callback.from_user.id)

@router.callback_query(lambda c: c.data == "refresh_companies")
async def refresh_companies(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    phone = db.get_user_phone(user_id)
    if not phone:
        await callback.message.edit_text("Номер телефона не найден. Пожалуйста, вернитесь в главное меню и начните заново.")
        return
    await callback.message.edit_text("🔄 Обновляем список компаний...")
    await process_companies_loading(user_id, phone, state, callback.message)

@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await show_main_menu(callback.message.chat.id, callback.bot, callback.from_user.id)
    await callback.answer()