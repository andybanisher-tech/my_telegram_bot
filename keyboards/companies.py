from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_companies_view_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Обновить список компаний", callback_data="refresh_companies_view")
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