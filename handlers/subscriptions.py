from aiogram import Router, types
from aiogram.fsm.context import FSMContext
import database as db
from keyboards.subscriptions import get_category_choice_keyboard, get_subscription_management_keyboard
from keyboards.common import get_back_to_main_keyboard
from states import states

router = Router()

@router.callback_query(lambda c: c.data.startswith('sub_cat_'), states.CategoryChoice.selecting)
async def category_choice_toggle(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split('_')[2])
    data = await state.get_data()
    selected = data.get('selected_categories', [])
    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.append(cat_id)
    await state.update_data(selected_categories=selected)
    await callback.message.edit_reply_markup(
        reply_markup=get_category_choice_keyboard(selected)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "sub_categories_done", states.CategoryChoice.selecting)
async def category_choice_done(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    selected = data.get('selected_categories', [])
    if not selected:
        await callback.answer("Вы не выбрали ни одной категории!", show_alert=True)
        return
    db.unsubscribe_all(user_id)
    for cat_id in selected:
        db.subscribe(user_id, cat_id)
    await callback.message.edit_text("✅ Подписка сохранена. Теперь вы будете получать новости по выбранным категориям.")
    await state.clear()
    await callback.message.answer(
        "Вернуться в главное меню:",
        reply_markup=get_back_to_main_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data.startswith('sub_manage_'), states.SubscriptionManagement.selecting)
async def sub_manage_toggle(callback: types.CallbackQuery, state: FSMContext):
    cat_id = int(callback.data.split('_')[2])
    data = await state.get_data()
    selected = data.get('selected_subscriptions', [])
    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.append(cat_id)
    await state.update_data(selected_subscriptions=selected)
    await callback.message.edit_reply_markup(
        reply_markup=get_subscription_management_keyboard(callback.from_user.id, selected)
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "sub_manage_done", states.SubscriptionManagement.selecting)
async def sub_manage_done(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    data = await state.get_data()
    selected = data.get('selected_subscriptions', [])
    db.unsubscribe_all(user_id)
    for cat_id in selected:
        db.subscribe(user_id, cat_id)
    await callback.message.edit_text("✅ Изменения сохранены.")
    await state.clear()
    await callback.message.answer(
        "Вернуться в главное меню:",
        reply_markup=get_back_to_main_keyboard()
    )
    await callback.answer()

@router.callback_query(lambda c: c.data == "sub_manage_unsubscribe_all", states.SubscriptionManagement.selecting)
async def sub_manage_unsubscribe_all(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    db.unsubscribe_all(user_id)
    await callback.message.edit_text("❌ Вы отписаны от всех новостей.")
    await state.clear()
    await callback.message.answer(
        "Вернуться в главное меню:",
        reply_markup=get_back_to_main_keyboard()
    )
    await callback.answer()