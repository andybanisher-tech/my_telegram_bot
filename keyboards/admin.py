from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db

def get_categories_management_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить категорию", callback_data="cat_add")
    builder.button(text="✏️ Переименовать категорию", callback_data="cat_rename")
    builder.button(text="🗑️ Удалить категорию", callback_data="cat_delete")
    builder.button(text="◀️ Назад", callback_data="cat_back")
    builder.adjust(1)
    return builder.as_markup()

def get_categories_list_keyboard(action_prefix):
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in categories:
        builder.button(text=cat_name, callback_data=f"{action_prefix}_{cat_id}")
    builder.button(text="◀️ Отмена", callback_data="cat_cancel")
    builder.adjust(1)
    return builder.as_markup()

def get_admin_management_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="➕ Добавить администратора", callback_data="admin_add")
    builder.button(text="➖ Удалить администратора", callback_data="admin_remove")
    builder.button(text="📋 Список администраторов", callback_data="admin_list")
    builder.button(text="◀️ Назад", callback_data="admin_back")
    builder.adjust(1)
    return builder.as_markup()

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

def get_categories_keyboard(selected=None):
    if selected is None:
        selected = []
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in categories:
        mark = "✅" if cat_id in selected else "❌"
        builder.button(text=f"{mark} {cat_name}", callback_data=f"select_{cat_id}")
    builder.button(text="✅ Готово", callback_data="categories_done")
    builder.adjust(1)
    return builder.as_markup()

def get_preview_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="send_news")
    builder.button(text="❌ Отмена", callback_data="cancel_news")
    builder.adjust(2)
    return builder.as_markup()