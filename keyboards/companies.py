from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_companies_view_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить / изменить список", callback_data="refresh_companies_view")
    builder.button(text="◀️ В главное меню", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_company_selection_keyboard(companies):
    builder = InlineKeyboardBuilder()
    for company in companies:
        builder.button(text=company['name'], callback_data=f"banner_comp_{company['code']}")
    builder.button(text="◀️ Отмена", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def get_company_multi_selection_keyboard(companies, selected_codes):
    builder = InlineKeyboardBuilder()
    for comp in companies:
        mark = "✅" if comp['code'] in selected_codes else "☐"
        builder.button(text=f"{mark} {comp['name']}", callback_data=f"toggle_comp_{comp['code']}")
    builder.button(text="💾 Сохранить выбор", callback_data="save_companies_selection")
    builder.adjust(1)
    return builder.as_markup()