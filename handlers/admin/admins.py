import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
from config import STATIC_ADMINS, BOT_USERNAME
from utils.helpers import is_admin

router = Router()
logger = logging.getLogger(__name__)

ADMIN_BOT_COMMANDS = [
    BotCommand(command="admin", description="📢 Создать новость"),
    BotCommand(command="stats", description="📊 Статистика"),
    BotCommand(command="categories", description="🏷️ Управление категориями"),
    BotCommand(command="manage_admins", description="👥 Управление админами"),
    BotCommand(command="manage_managers", description="👥 Управление менеджерами"),
    BotCommand(command="send", description="✉️ Быстрая рассылка"),
    BotCommand(command="cancel", description="❌ Отмена процесса"),
]

class AdminManagement(StatesGroup):
    choosing_action = State()
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_name = State()
    choosing_admin_to_remove = State()

def get_admin_management_keyboard():
    pending = db.get_pending_count('admin')
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить администратора", callback_data="admin_add")
    builder.button(text="➖ Удалить администратора", callback_data="admin_remove")
    builder.button(text="📋 Список администраторов", callback_data="admin_list")
    badge = f" ({pending})" if pending else ""
    builder.button(text=f"📥 Заявки на администратора{badge}", callback_data="areq_list")
    builder.button(text="🔗 Ссылка-приглашение", callback_data="areq_invite")
    builder.button(text="◀️ Назад", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_requests_keyboard():
    requests = db.get_pending_requests('admin')
    builder = InlineKeyboardBuilder()
    for req in requests:
        name = req['first_name'] or '—'
        if len(name) > 12:
            name = name[:11] + "…"
        builder.button(text=f"✅ {name}", callback_data=f"req_approve_a_{req['id']}")
        builder.button(text=f"❌ {name}", callback_data=f"req_reject_a_{req['id']}")
    builder.button(text="◀️ Назад", callback_data="areq_back")
    sizes = [2] * len(requests) + [1]
    builder.adjust(*sizes)
    return builder.as_markup()

def _render_admin_requests_text(requests):
    if not requests:
        return "📥 *Заявок на роль администратора нет.*"
    lines = ["📥 *Заявки на роль администратора:*\n"]
    for i, req in enumerate(requests, 1):
        username = f"@{req['username']}" if req['username'] else "без username"
        lines.append(f"{i}. {req['first_name']} ({username})\n   ID: `{req['user_id']}`")
    return "\n".join(lines)

def get_admins_list_keyboard(static_admins):
    admins = db.get_db_admins()
    builder = InlineKeyboardBuilder()
    for admin in admins:
        if admin["id"] in static_admins:
            continue
        button_text = f"{admin['name']} ({admin['id']})"
        builder.button(text=button_text, callback_data=f"remove_admin_{admin['id']}")
    builder.button(text="◀️ Отмена", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command("manage_admins"))
async def cmd_manage_admins(message: types.Message, state: FSMContext):
    print(f"DEBUG: {message.text} получена")
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.set_state(AdminManagement.choosing_action)
    await message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_add", AdminManagement.choosing_action)
async def admin_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(AdminManagement.waiting_for_new_admin_id)
    await callback.message.edit_text(
        "Введите Telegram ID нового администратора (число).\n"
        "Узнать ID можно у @userinfobot.\n"
        "Отправьте /cancel для отмены."
    )
    await callback.answer()

@router.message(AdminManagement.waiting_for_new_admin_id)
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
    await state.set_state(AdminManagement.waiting_for_new_admin_name)
    await message.answer(
        "Введите имя для этого администратора (например, Иван или @username):"
    )

@router.message(AdminManagement.waiting_for_new_admin_name)
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
    # Устанавливаем команды для нового админа (опционально)
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
    await state.set_state(AdminManagement.choosing_action)
    await message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_remove", AdminManagement.choosing_action)
async def admin_remove_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    admins = db.get_db_admins()
    removable = [a for a in admins if a["id"] not in STATIC_ADMINS]
    if not removable:
        await callback.message.edit_text("Нет администраторов для удаления (кроме статических).")
        await state.set_state(AdminManagement.choosing_action)
        await callback.message.answer(
            "Управление администраторами. Выберите действие:",
            reply_markup=get_admin_management_keyboard()
        )
        return
    await state.set_state(AdminManagement.choosing_admin_to_remove)
    await callback.message.edit_text(
        "Выберите администратора для удаления:",
        reply_markup=get_admins_list_keyboard(STATIC_ADMINS)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("remove_admin_"), AdminManagement.choosing_admin_to_remove)
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
    await state.set_state(AdminManagement.choosing_action)
    await callback.message.answer(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "admin_list", AdminManagement.choosing_action)
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
    await state.set_state(AdminManagement.choosing_action)
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
    await state.set_state(AdminManagement.choosing_action)
    await callback.message.edit_text(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )
    await callback.answer()

# ---------- Заявки на роль администратора ----------

@router.callback_query(lambda c: c.data == "areq_invite")
async def admin_invite_link(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    link = f"https://t.me/{BOT_USERNAME}?start=request_admin"
    text = (
        "🔗 *Ссылка-приглашение для администраторов:*\n\n"
        f"`{link}`\n\n"
        "Отправьте эту ссылку будущему администратору. Когда он по ней перейдёт, "
        "его заявка появится в разделе «📥 Заявки на администратора»."
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="areq_back")
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup(), disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(lambda c: c.data == "areq_list")
async def admin_requests_list(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    requests = db.get_pending_requests('admin')
    await callback.message.edit_text(
        _render_admin_requests_text(requests),
        parse_mode="Markdown",
        reply_markup=get_admin_requests_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "areq_back")
async def admin_requests_back(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(AdminManagement.choosing_action)
    await callback.message.edit_text(
        "Управление администраторами. Выберите действие:",
        reply_markup=get_admin_management_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("req_approve_a_"))
async def admin_request_approve(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    request_id = int(callback.data.rsplit('_', 1)[1])
    req = db.get_request_by_id(request_id)
    if not req or req['role'] != 'admin' or req['status'] != 'pending':
        await callback.answer("Заявка уже обработана.", show_alert=True)
        await _refresh_admin_requests(callback)
        return
    name = req['first_name'] or (f"@{req['username']}" if req['username'] else str(req['user_id']))
    db.add_admin(req['user_id'], name)
    db.update_request_status(request_id, 'approved')
    try:
        await callback.bot.set_my_commands(ADMIN_BOT_COMMANDS, scope=BotCommandScopeChat(chat_id=req['user_id']))
    except Exception as e:
        logger.error(f"Не удалось установить команды для нового админа {req['user_id']}: {e}")
    try:
        await callback.bot.send_message(
            req['user_id'],
            "✅ Ваша заявка на роль администратора одобрена! Вам стали доступны команды /manage_admins, /manage_managers и др."
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {req['user_id']}: {e}")
    await callback.answer(f"Одобрен: {name}")
    await _refresh_admin_requests(callback)

@router.callback_query(lambda c: c.data.startswith("req_reject_a_"))
async def admin_request_reject(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    request_id = int(callback.data.rsplit('_', 1)[1])
    req = db.get_request_by_id(request_id)
    if not req or req['role'] != 'admin' or req['status'] != 'pending':
        await callback.answer("Заявка уже обработана.", show_alert=True)
        await _refresh_admin_requests(callback)
        return
    db.update_request_status(request_id, 'rejected')
    try:
        await callback.bot.send_message(
            req['user_id'],
            "❌ Ваша заявка на роль администратора отклонена."
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {req['user_id']}: {e}")
    await callback.answer("Отклонено")
    await _refresh_admin_requests(callback)

async def _refresh_admin_requests(callback: types.CallbackQuery):
    requests = db.get_pending_requests('admin')
    await callback.message.edit_text(
        _render_admin_requests_text(requests),
        parse_mode="Markdown",
        reply_markup=get_admin_requests_keyboard()
    )