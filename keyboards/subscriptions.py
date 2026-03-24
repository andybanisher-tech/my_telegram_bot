from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db

def get_category_choice_keyboard(selected=None):
    if selected is None:
        selected = []
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in categories:
        mark = "✅" if cat_id in selected else "❌"
        builder.button(text=f"{mark} {cat_name}", callback_data=f"sub_cat_{cat_id}")
    builder.button(text="✅ Готово", callback_data="sub_categories_done")
    builder.adjust(1)
    return builder.as_markup()

def get_subscription_management_keyboard(user_id, selected=None):
    if selected is None:
        selected = db.get_user_subscriptions(user_id)
    categories = db.get_categories()
    builder = InlineKeyboardBuilder()
    for cat_id, cat_name in categories:
        mark = "✅" if cat_id in selected else "❌"
        builder.button(text=f"{mark} {cat_name}", callback_data=f"sub_manage_{cat_id}")
    builder.button(text="✅ Готово", callback_data="sub_manage_done")
    builder.button(text="❌ Отписаться от всего", callback_data="sub_manage_unsubscribe_all")
    builder.adjust(1)
    return builder.as_markup()