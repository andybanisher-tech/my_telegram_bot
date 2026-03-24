import asyncio
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database as db
import bonus_client
from keyboards.common import get_main_keyboard
from utils.helpers import decline_ball
import logging

router = Router()
logger = logging.getLogger(__name__)

class BonusProcess(StatesGroup):
    choosing_company = State()

def get_lk_keyboard():
    """Клавиатура со ссылкой на личный кабинет."""
    builder = InlineKeyboardBuilder()
    builder.button(text="🔗 Подробнее в личном кабинете", url="https://stalker-co.ru/personal/internet/")
    return builder.as_markup()

async def show_company_selection(user_id: int, message: types.Message, action: str):
    companies = db.get_user_companies(user_id)
    if not companies:
        await message.answer("У вас нет выбранных компаний. Сначала выберите компании в разделе «Мои компании».")
        return None
    if len(companies) == 1:
        return companies[0]
    builder = InlineKeyboardBuilder()
    for company in companies:
        builder.button(text=company['name'], callback_data=f"bonus_comp_{action}_{company['code']}")
    builder.button(text="◀️ Отмена", callback_data="back_to_main")
    builder.adjust(1)
    await message.answer("Выберите компанию:", reply_markup=builder.as_markup())
    return None

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
    await message.answer("Выберите действие:", reply_markup=get_main_keyboard(user_id))

async def fetch_and_show_history(message: types.Message, user_id: int, company_code: str):
    await message.answer("⏳ Запрашиваем историю...")
    lines = await bonus_client.get_bonus_history(company_code)
    if lines is None:
        await message.answer("❌ Не удалось получить историю. Попробуйте позже.")
    elif not lines:
        # Если история пуста, показываем сообщение и кнопку на ЛК
        await message.answer(
            "История изменений баллов пуста.",
            reply_markup=get_lk_keyboard()
        )
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
            for i, part in enumerate(parts):
                # К последней части добавляем кнопку
                if i == len(parts) - 1:
                    await message.answer(part, parse_mode="Markdown", reply_markup=get_lk_keyboard())
                else:
                    await message.answer(part, parse_mode="Markdown")
        else:
            await message.answer(text, parse_mode="Markdown", reply_markup=get_lk_keyboard())
    await message.answer("Выберите действие:", reply_markup=get_main_keyboard(user_id))

@router.message(F.text == "💰 Баланс баллов")
async def bonus_balance_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    company = await show_company_selection(user_id, message, "balance")
    if company:
        await fetch_and_show_balance(message, user_id, company['code'])

@router.callback_query(lambda c: c.data.startswith("bonus_comp_balance_"))
async def bonus_balance_company_chosen(callback: types.CallbackQuery, state: FSMContext):
    company_code = callback.data.split('_')[3]
    await callback.message.delete()
    await callback.answer()
    await fetch_and_show_balance(callback.message, callback.from_user.id, company_code)

@router.message(F.text == "📜 История баллов")
async def bonus_history_start(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    company = await show_company_selection(user_id, message, "history")
    if company:
        await fetch_and_show_history(message, user_id, company['code'])

@router.callback_query(lambda c: c.data.startswith("bonus_comp_history_"))
async def bonus_history_company_chosen(callback: types.CallbackQuery, state: FSMContext):
    company_code = callback.data.split('_')[3]
    await callback.message.delete()
    await callback.answer()
    await fetch_and_show_history(callback.message, callback.from_user.id, company_code)

@router.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main_callback(callback: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.message.answer("Главное меню:", reply_markup=get_main_keyboard(callback.from_user.id))
    await callback.answer()