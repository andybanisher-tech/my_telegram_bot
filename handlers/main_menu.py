from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
import database as db
from utils.helpers import is_admin, is_manager
from keyboards.common import (
    get_main_keyboard, get_phone_keyboard, get_back_to_main_keyboard,
    get_bonus_submenu_keyboard
)
from keyboards.companies import get_companies_view_keyboard, get_company_selection_keyboard
from keyboards.subscriptions import get_category_choice_keyboard, get_subscription_management_keyboard
from handlers.companies import process_companies_loading
from handlers.banners import fetch_and_show_banners
from handlers.partner_actions import partner_actions_start
from states import states

router = Router()

async def show_main_menu(chat_id: int, user_id: int, bot):
    await bot.send_message(chat_id, "Главное меню:", reply_markup=get_main_keyboard(user_id))

# Убираем удалённые пункты из списка
@router.message(F.text.in_([
    "🏢 Мои компании",
    "🎁 Текущие акции",
    "🎁 Реферальная программа",
    "👥 Акции контрагента",
    "ℹ️ Помощь"
]))

async def handle_main_menu(message: types.Message, state: FSMContext, force_text: str = None):
    user_id = message.from_user.id
    text = force_text if force_text is not None else message.text

    if text == "🏢 Мои компании":
        phone = db.get_user_phone(user_id)
        if not phone:
            await state.set_state(states.CompanyProcess.waiting_for_phone)
            await message.answer(
                "Для просмотра компаний поделись своим номером телефона.",
                reply_markup=get_phone_keyboard()
            )
            return
        companies = db.get_user_companies(user_id)
        if companies:
            lines = ["🏢 *Ваши компании:*\n"]
            for comp in companies:
                lines.append(f"• {comp['name']} (код {comp['code']})")
            await message.answer(
                "\n".join(lines),
                parse_mode="Markdown",
                reply_markup=get_companies_view_keyboard()
            )
        else:
            await process_companies_loading(user_id, phone, state, message)

    elif text == "🎁 Текущие акции":
        companies = db.get_user_companies(user_id)
        if not companies:
            await message.answer(
                "Для просмотра акций необходимо иметь выбранные компании. "
                "Сначала перейдите в раздел «Мои компании» и загрузите список."
            )
            return
        if len(companies) == 1:
            await fetch_and_show_banners(message, user_id, companies[0]['code'])
        else:
            await state.set_state(states.BannersProcess.choosing_company)
            await message.answer(
                "У вас несколько компаний. Выберите, для какой показать акции:",
                reply_markup=get_company_selection_keyboard(companies)
            )

    elif text == "🎁 Реферальная программа":
        await message.answer("Выберите раздел:", reply_markup=get_bonus_submenu_keyboard())

    elif text == "👥 Акции контрагента":
        if not is_manager(user_id):
            await message.answer("⛔ У вас нет прав для этой команды.")
            return
        await partner_actions_start(message, state)

    elif text == "ℹ️ Помощь":
        help_text = (
            "📚 *Доступные действия:*\n\n"
            "• 🏢 *Мои компании* – просмотр компаний, привязанных к вашему номеру.\n"
            "• 🎁 *Текущие акции* – актуальные акции для ваших компаний.\n"
            "• 🎁 *Реферальная программа* – бонусный баланс и история.\n"
        )
        if is_manager(user_id):
            help_text += "• 👥 *Акции контрагента* – просмотр акций для любого контрагента по его ID.\n"
        help_text += "\nЕсли у вас есть вопросы, обратитесь к администратору."
        await message.answer(help_text, parse_mode="Markdown")

@router.message(F.text == "◀️ Назад в главное меню")
async def back_to_main(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Главное меню:", reply_markup=get_main_keyboard(message.from_user.id))