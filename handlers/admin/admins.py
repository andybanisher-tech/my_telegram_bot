import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BotCommand, BotCommandScopeChat
import database as db
from config import STATIC_ADMINS
from keyboards.admin import (
    get_admin_management_keyboard,
    get_admins_list_keyboard
)
from states import states
from utils.helpers import is_admin  # правильный импорт

logger = logging.getLogger(__name__)
router = Router()

@router.message(Command("manage_admins"))
async def cmd_manage_admins(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.set_state(states.AdminManagement.choosing_action)
    await message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_add", states.AdminManagement.choosing_action)
async def admin_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(states.AdminManagement.waiting_for_new_admin_id)
    await callback.message.edit_text(
        "Введите Telegram ID нового администратора (число).\n"
        "Узнать ID можно у @userinfobot.\n"
        "Отправьте /cancel для отмены."
    )
    await callback.answer()

@router.message(states.AdminManagement.waiting_for_new_admin_id)
async def admin_add_id_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление администратора отменено.")
        return
    try:
        new_admin_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите целое число.")
        return
    if new_admin_id in STATIC_ADMINS:
        await message.answer("❌ Этот пользователь уже является статическим администратором (нельзя добавить повторно).")
        return
    existing = db.get_db_admins()
    if any(admin["id"] == new_admin_id for admin in existing):
        await message.answer("❌ Этот администратор уже есть в базе.")
        return
    await state.update_data(new_admin_id=new_admin_id)
    await state.set_state(states.AdminManagement.waiting_for_new_admin_name)
    await message.answer(
        "Введите имя для этого администратора (например, Иван или @username):"
    )

@router.message(states.AdminManagement.waiting_for_new_admin_name)
async def admin_add_name_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление администратора отменено.")
        return
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Попробуйте ещё раз:")
        return
    data = await state.get_data()
    new_admin_id = data.get("new_admin_id")
    db.add_admin(new_admin_id, name)
    # Устанавливаем команды для нового админа
    admin_commands = [
        BotCommand(command="admin", description="📢 Создать новость"),
        BotCommand(command="stats", description="📊 Статистика"),
        BotCommand(command="categories", description="🏷️ Управление категориями"),
        BotCommand(command="manage_admins", description="👥 Управление админами"),
        BotCommand(command="send", description="✉️ Быстрая рассылка"),
        BotCommand(command="cancel", description="❌ Отмена процесса"),
    ]
    try:
        await message.bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=new_admin_id))
    except Exception as e:
        logger.error(f"Не удалось установить команды для админа {new_admin_id}: {e}")
    await message.answer(f"✅ Пользователь {name} (ID {new_admin_id}) добавлен в администраторы.")
    await state.set_state(states.AdminManagement.choosing_action)
    await message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_remove", states.AdminManagement.choosing_action)
async def admin_remove_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    admins = db.get_db_admins()
    removable = [a for a in admins if a["id"] not in STATIC_ADMINS]
    if not removable:
        await callback.message.edit_text("Нет администраторов для удаления (кроме статических).")
        await state.set_state(states.AdminManagement.choosing_action)
        await callback.message.answer(
            "Управление администраторами. Выберите действие:",
            reply_markup=get_admin_management_keyboard()
        )
        return
    await state.set_state(states.AdminManagement.choosing_admin_to_remove)
    await callback.message.edit_text(
        "Выберите администратора для удаления:",
        reply_markup=get_admins_list_keyboard(STATIC_ADMINS)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("remove_admin_"), states.AdminManagement.choosing_admin_to_remove)
async def admin_remove_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    admin_id = int(callback.data.split('_')[2])
    if admin_id in STATIC_ADMINS:
        await callback.answer("Нельзя удалить статического администратора!")
        return
    db.remove_admin(admin_id)
    await callback.answer("✅ Администратор удалён")
    await callback.message.edit_text("✅ Администратор удалён.")
    await state.set_state(states.AdminManagement.choosing_action)
    await callback.message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_list", states.AdminManagement.choosing_action)
async def admin_list(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    statics = STATIC_ADMINS
    db_admins = db.get_db_admins()
    lines = ["📋 *Список администраторов:*\n"]
    if statics:
        lines.append("*Статические (неудаляемые):*")
        for sid in statics:
            name = next((a["name"] for a in db_admins if a["id"] == sid), "Без имени")
            lines.append(f"• {name} (ID {sid})")
        lines.append("")
    if db_admins:
        lines.append("*Из базы данных:*")
        for admin in db_admins:
            if admin["id"] not in statics:
                lines.append(f"• {admin['name']} (ID {admin['id']})")
    else:
        lines.append("Нет администраторов в БД.")
    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown")
    await state.set_state(states.AdminManagement.choosing_action)
    await callback.message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_back")
async def admin_back(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.clear()
    await callback.message.edit_text("Выход из управления администраторами.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "admin_cancel")
async def admin_cancel(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(states.AdminManagement.choosing_action)
    await callback.message.edit_text(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )
    await callback.answer()