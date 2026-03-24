from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database as db
from keyboards.admin import (
    get_categories_management_keyboard,
    get_categories_list_keyboard
)
from states import states
from handlers.main_menu import is_admin

router = Router()

@router.message(Command("categories"))
async def cmd_manage_categories(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.set_state(states.CategoryManagement.choosing_action)
    await message.answer(
        "Управление категориями. Выберите действие:",
        reply_markup=get_categories_management_keyboard()
    )

# Добавление категории
@router.callback_query(lambda c: c.data == "cat_add", states.CategoryManagement.choosing_action)
async def category_add_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(states.CategoryManagement.waiting_for_new_category_name)
    await callback.message.edit_text(
        "Введите название новой категории (или отправьте /cancel для отмены):"
    )
    await callback.answer()

@router.message(states.CategoryManagement.waiting_for_new_category_name)
async def category_add_finish(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Добавление категории отменено.")
        return
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    if db.get_category_by_name(new_name):
        await message.answer("❌ Категория с таким именем уже существует. Введите другое имя:")
        return
    db.add_category(new_name)
    await message.answer(f"✅ Категория «{new_name}» успешно добавлена!")
    await state.set_state(states.CategoryManagement.choosing_action)
    await message.answer(
        "Управление категориями. Выберите действие:",
        reply_markup=get_categories_management_keyboard()
    )

# Переименование категории
@router.callback_query(lambda c: c.data == "cat_rename", states.CategoryManagement.choosing_action)
async def category_rename_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    categories = db.get_categories()
    if len(categories) == 0:
        await callback.message.edit_text("Нет категорий для переименования.")
        await state.clear()
        return
    await state.set_state(states.CategoryManagement.choosing_category_to_rename)
    await callback.message.edit_text(
        "Выберите категорию для переименования:",
        reply_markup=get_categories_list_keyboard("rename_cat")
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("rename_cat_"), states.CategoryManagement.choosing_category_to_rename)
async def category_rename_choose(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    cat_id = int(callback.data.split('_')[2])
    cat_name = db.get_category_by_id(cat_id)
    if not cat_name:
        await callback.answer("Категория не найдена")
        return
    await state.update_data(rename_cat_id=cat_id, rename_cat_name=cat_name)
    await state.set_state(states.CategoryManagement.waiting_for_rename_name)
    await callback.message.edit_text(
        f"Текущее название: «{cat_name}».\n"
        "Введите новое название для этой категории (или отправьте /cancel для отмены):"
    )
    await callback.answer()

@router.message(states.CategoryManagement.waiting_for_rename_name)
async def category_rename_finish(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Переименование категории отменено.")
        return
    data = await state.get_data()
    old_name = data.get('rename_cat_name')
    new_name = message.text.strip()
    if not new_name:
        await message.answer("Название не может быть пустым. Попробуйте ещё раз:")
        return
    if old_name.lower() == new_name.lower():
        await message.answer("Новое название совпадает со старым. Введите другое имя:")
        return
    if db.get_category_by_name(new_name):
        await message.answer("❌ Категория с таким именем уже существует. Введите другое имя:")
        return
    success = db.rename_category(old_name, new_name)
    if success:
        await message.answer(f"✅ Категория переименована из «{old_name}» в «{new_name}».")
    else:
        await message.answer("❌ Не удалось переименовать. Возможно, категория была удалена.")
    await state.set_state(states.CategoryManagement.choosing_action)
    await message.answer(
        "Управление категориями. Выберите действие:",
        reply_markup=get_categories_management_keyboard()
    )

# Удаление категории
@router.callback_query(lambda c: c.data == "cat_delete", states.CategoryManagement.choosing_action)
async def category_delete_start(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    categories = db.get_categories()
    if len(categories) == 0:
        await callback.message.edit_text("Нет категорий для удаления.")
        await state.clear()
        return
    await state.set_state(states.CategoryManagement.choosing_category_to_delete)
    await callback.message.edit_text(
        "Выберите категорию для удаления (все подписки на неё будут удалены):",
        reply_markup=get_categories_list_keyboard("delete_cat")
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith("delete_cat_"), states.CategoryManagement.choosing_category_to_delete)
async def category_delete_confirm(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    cat_id = int(callback.data.split('_')[2])
    cat_name = db.get_category_by_id(cat_id)
    if not cat_name:
        await callback.answer("Категория не найдена")
        return
    success = db.delete_category(cat_name)
    if success:
        await callback.answer("✅ Категория удалена")
        await callback.message.edit_text(f"✅ Категория «{cat_name}» успешно удалена.")
    else:
        await callback.answer("❌ Ошибка удаления")
        await callback.message.edit_text(f"❌ Не удалось удалить категорию «{cat_name}».")
    await state.set_state(states.CategoryManagement.choosing_action)
    await callback.message.answer(
        "Управление категориями. Выберите действие:",
        reply_markup=get_categories_management_keyboard()
    )

# Возврат назад
@router.callback_query(lambda c: c.data == "cat_back")
async def categories_back(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.clear()
    await callback.message.edit_text("Выход из управления категориями.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "cat_cancel")
async def categories_cancel(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await state.set_state(states.CategoryManagement.choosing_action)
    await callback.message.edit_text(
        "Управление категориями. Выберите действие:",
        reply_markup=get_categories_management_keyboard()
    )
    await callback.answer()