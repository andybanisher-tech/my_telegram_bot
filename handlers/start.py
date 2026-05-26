import logging
from aiogram import Router, types
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
from config import STATIC_ADMINS, BOT_USERNAME
from keyboards.common import get_main_keyboard
from utils.helpers import is_admin, is_manager

router = Router()
logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    "Здравствуйте! 👋\n\n"
    "Я — бот компании Сталкер-Консалтинг (https://stalker-co.ru), "
    "надёжного B2B-дистрибьютора профессиональных товаров для индустрии красоты в России.\n\n"
    "С моей помощью вы можете:\n"
    "• 🏢 просматривать список привязанных компаний\n"
    "• 🎁 следить за актуальными акциями\n"
    "• 💰 проверять баланс и историю бонусных баллов\n"
    "• 🎁 участвовать в реферальной программе\n\n"
    "Нажимая «Начать», вы соглашаетесь с политикой конфиденциальности: https://stalker-co.ru/policy/"
)

def get_welcome_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Начать", callback_data="welcome_accept")
    return builder.as_markup()


async def _notify_admins_about_request(bot, user, role):
    role_name = "менеджера" if role == 'manager' else "администратора"
    username = f"@{user.username}" if user.username else "без username"
    text = (
        f"📥 *Новая заявка на роль {role_name}:*\n"
        f"👤 {user.first_name} ({username})\n"
        f"ID: `{user.id}`\n\n"
        f"Откройте /manage_{'managers' if role == 'manager' else 'admins'} → «📥 Заявки», "
        f"чтобы одобрить или отклонить."
    )
    admin_ids = set(STATIC_ADMINS) | {a['id'] for a in db.get_db_admins()}
    for admin_id in admin_ids:
        try:
            await bot.send_message(admin_id, text, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Не удалось уведомить админа {admin_id}: {e}")


async def _handle_role_request(message: types.Message, role: str):
    user = message.from_user
    role_name = "менеджера" if role == 'manager' else "администратора"

    if role == 'manager' and is_manager(user.id):
        await message.answer("✅ Вы уже являетесь менеджером.")
        return
    if role == 'admin' and is_admin(user.id):
        await message.answer("✅ Вы уже являетесь администратором.")
        return

    added = db.add_role_request(user.id, user.username, user.first_name, role)
    if added:
        await message.answer(
            f"📥 Ваша заявка на роль {role_name} отправлена администратору.\n"
            f"Вы получите уведомление о решении."
        )
        await _notify_admins_about_request(message.bot, user, role)
    else:
        await message.answer(
            f"📥 У вас уже есть активная заявка на роль {role_name}. Ожидайте решения."
        )


@router.message(Command("start"))
async def cmd_start(message: types.Message, command: CommandObject, state: FSMContext):
    await state.clear()
    user = message.from_user
    arg = (command.args or "").strip()

    role_from_arg = None
    if arg == "request_manager":
        role_from_arg = "manager"
    elif arg == "request_admin":
        role_from_arg = "admin"

    if role_from_arg:
        await _handle_role_request(message, role_from_arg)
        if not db.has_accepted_welcome(user.id):
            await message.answer(
                WELCOME_TEXT,
                reply_markup=get_welcome_keyboard(),
                disable_web_page_preview=True
            )
        else:
            await message.answer("Выбери действие:", reply_markup=get_main_keyboard(user.id))
        return

    if not db.has_accepted_welcome(user.id):
        await message.answer(
            WELCOME_TEXT,
            reply_markup=get_welcome_keyboard(),
            disable_web_page_preview=True
        )
        return

    await message.answer("👋 С возвращением!", reply_markup=types.ReplyKeyboardRemove())
    await message.answer("Выбери действие:", reply_markup=get_main_keyboard(user.id))


@router.callback_query(lambda c: c.data == "welcome_accept")
async def welcome_accept(callback: types.CallbackQuery, state: FSMContext):
    user = callback.from_user
    db.accept_welcome(user.id, user.username, user.first_name)
    await callback.message.edit_text("✅ Добро пожаловать!", reply_markup=None)
    await callback.bot.send_message(
        callback.message.chat.id,
        "Выбери действие:",
        reply_markup=get_main_keyboard(user.id)
    )
    await callback.answer()
