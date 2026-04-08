from aiogram.fsm.state import State, StatesGroup

class NewsCreation(StatesGroup):
    choosing_categories = State()
    waiting_for_text = State()
    waiting_for_photos = State()
    preview = State()

class CategoryManagement(StatesGroup):
    choosing_action = State()
    waiting_for_new_category_name = State()
    choosing_category_to_rename = State()
    waiting_for_rename_name = State()
    choosing_category_to_delete = State()

class AdminManagement(StatesGroup):
    choosing_action = State()
    waiting_for_new_admin_id = State()
    waiting_for_new_admin_name = State()
    choosing_admin_to_remove = State()

class CompanyProcess(StatesGroup):
    waiting_for_phone = State()
    selecting_companies = State()

class CategoryChoice(StatesGroup):
    selecting = State()

class SubscriptionManagement(StatesGroup):
    selecting = State()

class BannersProcess(StatesGroup):
    choosing_company = State()

# Добавьте этот класс
class ManagerManagement(StatesGroup):
    choosing_action = State()
    waiting_for_new_manager_id = State()
    waiting_for_new_manager_name = State()
    choosing_manager_to_remove = State()