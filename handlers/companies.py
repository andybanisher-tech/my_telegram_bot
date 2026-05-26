import asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
import soap_client
from keyboards.common import get_main_keyboard
from keyboards.companies import get_companies_view_keyboard, get_company_multi_selection_keyboard
from states import states
from states.states import CompanyProcess
import logging

router = Router()
logger = logging.getLogger(__name__)

async def show_main_menu(chat_id: int, user_id: int, bot):
    await bot.send_message(chat_id, "Выбери действие:", reply_markup=get_main_keyboard(user_id))

async def get_companies_keyboard(user_id: int, action: str, bot=None):
    companies = db.get_user_companies(user_id)
    if not companies:
        return None, "У вас нет выбранных компаний. Сначала выберите компании в разделе «Мои компании»."
    builder = InlineKeyboardBuilder()
    for comp in companies:
        builder.button(text=comp['name'], callback_data=f"{action}_comp_{comp['code']}")
    builder.button(text="🔄 Обновить / изменить список", callback_data=f"refresh_companies_{action}")
    builder.button(text="◀️ Отмена", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup(), None

async def _show_company_selection(companies: list, state: FSMContext, reply_chat_id: int, bot):
    selected_codes = [comp['code'] for comp in companies]
    await state.update_data(available_companies=companies, selected_codes=selected_codes)
    await state.set_state(CompanyProcess.selecting_companies)
    keyboard = get_company_multi_selection_keyboard(companies, selected_codes)
    await bot.send_message(
        reply_chat_id,
        "Отметьте нужные компании и нажмите «Сохранить»:",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data.startswith('refresh_companies_'))
async def refresh_companies_list(callback: types.CallbackQuery, state: FSMContext):
    action = callback.data.split('_')[2]
    user_id = callback.from_user.id
    phone = db.get_user_phone(user_id)
    if not phone:
        await callback.answer("Номер телефона не найден. Пожалуйста, начните с /start в личном чате.")
        return
    await callback.message.edit_text("🔄 Обновляем список компаний...")
    companies = await soap_client.get_companies_by_phone(phone)
    if not companies:
        await callback.message.edit_text("❌ Не удалось загрузить компании. Попробуйте позже.")
        return

    selected_codes = [comp['code'] for comp in companies]
    await state.update_data(
        available_companies=companies,
        selected_codes=selected_codes,
        next_action=action,
    )
    await state.set_state(CompanyProcess.selecting_companies)
    keyboard = get_company_multi_selection_keyboard(companies, selected_codes)
    await callback.message.edit_text(
        "Отметьте нужные компании и нажмите «Сохранить»:",
        reply_markup=keyboard
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith('toggle_comp_'), CompanyProcess.selecting_companies)
async def toggle_company(callback: types.CallbackQuery, state: FSMContext):
    code = callback.data[len('toggle_comp_'):]
    data = await state.get_data()
    companies = data['available_companies']
    selected_codes = data['selected_codes']

    if code in selected_codes:
        selected_codes.remove(code)
    else:
        selected_codes.append(code)

    await state.update_data(selected_codes=selected_codes)
    keyboard = get_company_multi_selection_keyboard(companies, selected_codes)
    await callback.message.edit_reply_markup(reply_markup=keyboard)
    await callback.answer()

@router.callback_query(lambda c: c.data == 'save_companies_selection', CompanyProcess.selecting_companies)
async def save_companies_selection(callback: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    companies = data['available_companies']
    selected_codes = data['selected_codes']
    next_action = data.get('next_action', 'view')
    user_id = callback.from_user.id

    if not selected_codes:
        await callback.answer("Выберите хотя бы одну компанию!", show_alert=True)
        return

    selected = [c for c in companies if c['code'] in selected_codes]
    db.save_user_companies(user_id, selected)
    await state.clear()
    await callback.answer("Сохранено!")

    if next_action == 'view':
        lines = ["✅ *Выбранные компании сохранены:*\n"]
        for comp in selected:
            lines.append(f"• {comp['name']} (код {comp['code']})")
        await callback.message.edit_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=get_companies_view_keyboard()
        )
        return

    # Возврат к исходному действию (balance / history / banners)
    if len(selected) == 1:
        await callback.message.delete()
        company_code = selected[0]['code']
        if next_action == 'balance':
            from handlers.bonus import fetch_and_show_balance
            await fetch_and_show_balance(callback.message, user_id, company_code)
        elif next_action == 'history':
            from handlers.bonus import fetch_and_show_history
            await fetch_and_show_history(callback.message, user_id, company_code)
        elif next_action == 'banners':
            from handlers.banners import fetch_and_show_banners
            brand_filter = data.get('brand_filter')
            await fetch_and_show_banners(callback.message, user_id, company_code, brand_filter)
        return

    keyboard, error = await get_companies_keyboard(user_id, next_action, callback.bot)
    if error:
        await callback.message.edit_text(error)
        return

    from states import BalanceSelecting, HistorySelecting, BannersSelecting
    state_map = {
        'balance': BalanceSelecting.company,
        'history': HistorySelecting.company,
        'banners': BannersSelecting.company,
    }
    if next_action in state_map:
        await state.set_state(state_map[next_action])
        if next_action == 'banners' and data.get('brand_filter') is not None:
            await state.update_data(brand_filter=data['brand_filter'])
    await callback.message.edit_text("✅ Список обновлён. Выберите компанию:", reply_markup=keyboard)

async def process_companies_loading(user_id: int, phone: str, state: FSMContext, message: types.Message, reply_chat_id: int):
    await message.bot.send_message(reply_chat_id, "⏳ Загружаем список компаний...")
    companies = await soap_client.get_companies_by_phone(phone)
    if not companies:
        await message.bot.send_message(reply_chat_id, "❌ Не удалось загрузить компании. Попробуйте позже.")
        await state.clear()
        await show_main_menu(reply_chat_id, user_id, message.bot)
        return
    await _show_company_selection(companies, state, reply_chat_id, message.bot)

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
        await process_companies_loading(user_id, phone, state, message, message.chat.id)
    else:
        await message.answer("✅ Номер подтверждён.", reply_markup=types.ReplyKeyboardRemove())
        await state.clear()
        await show_main_menu(message.chat.id, user_id, message.bot)
