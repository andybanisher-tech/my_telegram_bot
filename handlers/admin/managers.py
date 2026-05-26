import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
from config import STATIC_MANAGERS, BOT_USERNAME
from utils.helpers import is_admin
from states import ManagerManagement

router = Router()
logger = logging.getLogger(__name__)

def get_manager_management_keyboard():
    pending = db.get_pending_count('manager')
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить менеджера", callback_data="manager_add")
    builder.button(text="➖ Удалить менеджера", callback_data="manager_remove")
    builder.button(text="📋 Список менеджеров", callback_data="manager_list")
    badge = f" ({pending})" if pending else ""
    builder.button(text=f"📥 Заявки на менеджера{badge}", callback_data="mreq_list")
    builder.button(text="🔗 Ссылка-приглашение", callback_data="mreq_invite")
    builder.button(text="◀️ Назад", callback_data="manager_back")
    builder.adjust(1)
    return builder.as_markup()

def get_manager_requests_keyboard():
    requests = db.get_pending_requests('manager')
    builder = InlineKeyboardBuilder()
    for req in requests:
        name = req['first_name'] or '—'
        if len(name) > 12:
            name = name[:11] + "…"
        builder.button(text=f"✅ {name}", callback_data=f"req_approve_m_{req['id']}")
        builder.button(text=f"❌ {name}", callback_data=f"req_reject_m_{req['id']}")
    builder.button(text="◀️ Назад", callback_data="mreq_back")
    sizes = [2] * len(requests) + [1]
    builder.adjust(*sizes)
    return builder.as_markup()

def _render_requests_text(requests):
    if not requests:
        return "📥 *Заявок на роль менеджера нет.*"
    lines = ["📥 *Заявки на роль менеджера:*\n"]
    for i, req in enumerate(requests, 1):
        username = f"@{req['username']}" if req['username'] else "без username"
        lines.append(f"{i}. {req['first_name']} ({username})\n   ID: `{req['user_id']}`")
    return "\n".join(lines)

def get_managers_list_keyboard():
    managers = db.get_db_managers()
    builder = InlineKeyboardBuilder()
    for manager in managers:
        button_text = f"{manager['name']} ({manager['id']})"
        builder.button(text=button_text, callback_data=f"remove_manager_{manager['id']}")
    builder.button(text="◀️ Отмена", callback_data="manager_cancel")
    builder.adjust(1)
    return builder.as_markup()

@router.message(Command("manage_managers"))
async def cmd_manage_managers(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.set_state(ManagerManagement.choosing_action)
    await message.answer(
        "Управление менеджерами. Выберите действие:",
        reply_markup=get_manager_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "manager_add", ManagerManagement.choosing_action)
async def manager_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(ManagerManagement.waiting_for_new_manager_id)
    await callback.message.edit_text(
        "Введите Telegram ID нового менеджера (число).\n"
        "Узнать ID можно у @userinfobot.\n"
        "Отправьте /cancel для отмены."
    )
    await callback.answer()

@router.message(ManagerManagement.waiting_for_new_manager_id)
async def manager_add_id_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление менеджера отменено.")
        return
    try:
        new_manager_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Некорректный ID. Введите целое число.")
        return
    existing = db.get_db_managers()
    if any(m["id"] == new_manager_id for m in existing):
        await message.answer("❌ Этот пользователь уже является менеджером.")
        return
    await state.update_data(new_manager_id=new_manager_id)
    await state.set_state(ManagerManagement.waiting_for_new_manager_name)
    await message.answer(
        "Введите имя для этого менеджера (например, Иван или @username):"
    )

@router.message(ManagerManagement.waiting_for_new_manager_name)
async def manager_add_name_received(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление менеджера отменено.")
        return
    name = message.text.strip()
    if not name:
        await message.answer("Имя не может быть пустым. Попробуйте ещё раз:")
        return
    data = await state.get_data()
    new_manager_id = data.get("new_manager_id")
    db.add_manager(new_manager_id, name)
    await message.answer(f"✅ Пользователь {name} (ID {new_manager_id}) добавлен в менеджеры.")
    await state.set_state(ManagerManagement.choosing_action)
    await message.answer(
        "Управление менеджерами. Выберите действие:",
        reply_markup=get_manager_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "manager_remove", ManagerManagement.choosing_action)
async def manager_remove_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    managers = db.get_db_managers()
    if not managers:
        await callback.message.edit_text("Нет менеджеров для удаления.")
        await state.set_state(ManagerManagement.choosing_action)
        await callback.message.answer(
            "Управление менеджерами. Выберите действие:",
            reply_markup=get_manager_management_keyboard()
        )
        return
    await state.set_state(ManagerManagement.choosing_manager_to_remove)
    await callback.message.edit_text(
        "Выберите менеджера для удаления:",
        reply_markup=get_managers_list_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("remove_manager_"), ManagerManagement.choosing_manager_to_remove)
async def manager_remove_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    manager_id = int(callback.data.split('_')[2])
    db.remove_manager(manager_id)
    await callback.answer("✅ Менеджер удалён")
    await callback.message.edit_text("✅ Менеджер удалён.")
    await state.set_state(ManagerManagement.choosing_action)
    await callback.message.answer(
        "Управление менеджерами. Выберите действие:",
        reply_markup=get_manager_management_keyboard()
    )

@router.callback_query(lambda c: c.data == "manager_list", ManagerManagement.choosing_action)
async def manager_list(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    managers = db.get_db_managers()
    lines = ["📋 *Список менеджеров:*\n"]
    if managers:
        for m in managers:
            lines.append(f"• {m['name']} (ID {m['id']})")
    else:
        lines.append("Нет менеджеров.")
    await callback.message.edit_text("\n".join(lines), parse_mode="Markdown")
    await state.set_state(ManagerManagement.choosing_action)
    await callback.message.answer(
        "Управление менеджерами. Выберите действие:",
        reply_markup=get_manager_management_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "manager_back")
async def manager_back(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.clear()
    await callback.message.edit_text("Выход из управления менеджерами.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "manager_cancel")
async def manager_cancel(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(ManagerManagement.choosing_action)
    await callback.message.edit_text(
        "Управление менеджерами. Выберите действие:",
        reply_markup=get_manager_management_keyboard()
    )
    await callback.answer()

# ---------- Заявки на роль менеджера ----------

@router.callback_query(lambda c: c.data == "mreq_invite")
async def manager_invite_link(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    link = f"https://t.me/{BOT_USERNAME}?start=request_manager"
    text = (
        "🔗 *Ссылка-приглашение для менеджеров:*\n\n"
        f"`{link}`\n\n"
        "Отправьте эту ссылку будущему менеджеру. Когда он по ней перейдёт, "
        "его заявка появится в разделе «📥 Заявки на менеджера»."
    )
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="mreq_back")
    await callback.message.edit_text(text, parse_mode="Markdown", reply_markup=builder.as_markup(), disable_web_page_preview=True)
    await callback.answer()

@router.callback_query(lambda c: c.data == "mreq_list")
async def manager_requests_list(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    requests = db.get_pending_requests('manager')
    await callback.message.edit_text(
        _render_requests_text(requests),
        parse_mode="Markdown",
        reply_markup=get_manager_requests_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "mreq_back")
async def manager_requests_back(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(ManagerManagement.choosing_action)
    await callback.message.edit_text(
        "Управление менеджерами. Выберите действие:",
        reply_markup=get_manager_management_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("req_approve_m_"))
async def manager_request_approve(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    request_id = int(callback.data.rsplit('_', 1)[1])
    req = db.get_request_by_id(request_id)
    if not req or req['role'] != 'manager' or req['status'] != 'pending':
        await callback.answer("Заявка уже обработана.", show_alert=True)
        await _refresh_manager_requests(callback)
        return
    name = req['first_name'] or (f"@{req['username']}" if req['username'] else str(req['user_id']))
    db.add_manager(req['user_id'], name)
    db.update_request_status(request_id, 'approved')
    try:
        await callback.bot.send_message(
            req['user_id'],
            "✅ Ваша заявка на роль менеджера одобрена! Откройте главное меню — стал доступен раздел «👥 Акции контрагента»."
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {req['user_id']}: {e}")
    await callback.answer(f"Одобрен: {name}")
    await _refresh_manager_requests(callback)

@router.callback_query(lambda c: c.data.startswith("req_reject_m_"))
async def manager_request_reject(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    request_id = int(callback.data.rsplit('_', 1)[1])
    req = db.get_request_by_id(request_id)
    if not req or req['role'] != 'manager' or req['status'] != 'pending':
        await callback.answer("Заявка уже обработана.", show_alert=True)
        await _refresh_manager_requests(callback)
        return
    db.update_request_status(request_id, 'rejected')
    try:
        await callback.bot.send_message(
            req['user_id'],
            "❌ Ваша заявка на роль менеджера отклонена."
        )
    except Exception as e:
        logger.error(f"Не удалось уведомить пользователя {req['user_id']}: {e}")
    await callback.answer("Отклонено")
    await _refresh_manager_requests(callback)

async def _refresh_manager_requests(callback: types.CallbackQuery):
    requests = db.get_pending_requests('manager')
    await callback.message.edit_text(
        _render_requests_text(requests),
        parse_mode="Markdown",
        reply_markup=get_manager_requests_keyboard()
    )