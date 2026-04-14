import asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
import bonus_client
from keyboards.common import get_main_keyboard, get_bonus_submenu_keyboard
from utils.helpers import decline_ball
from states import BalanceSelecting, HistorySelecting
import logging

router = Router()
logger = logging.getLogger(__name__)

# ... (функции show_bonus_submenu, fetch_and_show_balance, fetch_and_show_history остаются без изменений)

async def fetch_and_show_balance(message: types.Message, user_id: int, company_code: str):
    await message.answer("⏳ Запрашиваем баланс...")
    data = await bonus_client.get_bonus_balance(company_code)
    if data and "SumBonus" in data:
        balance = data["SumBonus"]
        percent = data.get("BonusApplyPercent", 0)
        word = decline_ball(balance)
        text = f"💰 *Ваш бонусный баланс:*\n\n`{balance}` {word}"
        if percent:
            text += f"\n\nПроцент применения: {percent}%"
        await message.answer(text, parse_mode="Markdown")
    else:
        await message.answer("❌ Не удалось получить баланс. Попробуйте позже.")
    # Показываем подменю реферальной программы
    await message.answer("Выберите раздел:", reply_markup=get_bonus_submenu_keyboard())

async def fetch_and_show_history(message: types.Message, user_id: int, company_code: str):
    await message.answer("⏳ Запрашиваем историю...")
    lines = await bonus_client.get_bonus_history(company_code)
    if lines is None:
        await message.answer("❌ Не удалось получить историю. Попробуйте позже.")
    elif not lines:
        await message.answer("История изменений баллов пуста.")
    else:
        text = "📜 *История изменений баллов:*\n\n"
        for item in lines:
            sign = "➕" if item["type"] == "income" else "➖"
            balance = item["balance"]
            word = decline_ball(abs(balance))
            date = item["date"]
            name = item["name"]
            text += f"{sign} *{balance}* {word} – {date}\n_{name}_\n\n"
        if len(text) > 4000:
            parts = []
            current = "📜 *История изменений баллов:*\n\n"
            for item in lines:
                sign = "➕" if item["type"] == "income" else "➖"
                balance = item["balance"]
                word = decline_ball(abs(balance))
                date = item["date"]
                name = item["name"]
                line = f"{sign} *{balance}* {word} – {date}\n_{name}_\n\n"
                if len(current) + len(line) > 4000:
                    parts.append(current)
                    current = "📜 *История изменений баллов (продолжение):*\n\n" + line
                else:
                    current += line
            if current:
                parts.append(current)
            for part in parts:
                await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown")
    await message.answer("Выберите раздел:", reply_markup=get_bonus_submenu_keyboard())

@router.message(F.text == "💰 Баланс баллов")
async def bonus_balance_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    # Показываем выбор компании через инлайн-клавиатуру (функция из companies.py)
    from handlers.companies import get_companies_keyboard
    keyboard, error = await get_companies_keyboard(user_id, "balance", message.bot)
    if error:
        await message.answer(error)
        return
    await message.answer("Выберите компанию для просмотра баланса:", reply_markup=keyboard)
    await state.set_state(BalanceSelecting.company)

@router.callback_query(lambda c: c.data.startswith('balance_comp_'), BalanceSelecting.company)
async def balance_company_chosen(callback: types.CallbackQuery, state: FSMContext):
    company_code = callback.data.split('_')[2]
    await callback.message.delete()
    await callback.answer()
    await fetch_and_show_balance(callback.message, callback.from_user.id, company_code)
    await state.clear()

@router.message(F.text == "📜 История баллов")
async def bonus_history_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    from handlers.companies import get_companies_keyboard
    keyboard, error = await get_companies_keyboard(user_id, "history", message.bot)
    if error:
        await message.answer(error)
        return
    await message.answer("Выберите компанию для просмотра истории:", reply_markup=keyboard)
    await state.set_state(HistorySelecting.company)

@router.callback_query(lambda c: c.data.startswith('history_comp_'), HistorySelecting.company)
async def history_company_chosen(callback: types.CallbackQuery, state: FSMContext):
    company_code = callback.data.split('_')[2]
    await callback.message.delete()
    await callback.answer()
    await fetch_and_show_history(callback.message, callback.from_user.id, company_code)
    await state.clear()

# Обработчик кнопки "◀️ Отмена" из клавиатуры компаний (перенаправляет в главное меню)
@router.callback_query(lambda c: c.data == "back_to_main")
async def bonus_back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(callback.from_user.id))
    await callback.answer()