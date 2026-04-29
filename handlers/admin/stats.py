import sqlite3
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database as db
from utils.helpers import is_admin

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    
    conn = sqlite3.connect(db.DB_NAME)
    cur = conn.cursor()
    
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM users WHERE is_verified = 1")
    verified_users = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM user_companies")
    total_company_links = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM user_companies")
    users_with_companies = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM promo_clicks")
    total_clicks = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM promo_clicks WHERE user_id IS NOT NULL")
    users_clicked = cur.fetchone()[0]
    
    conn.close()
    
    await message.answer(
        f"� *Статистика бота*\n\n"
        f"� Всего пользователей: {total_users}\n"
        f"✅ Верифицировали номер: {verified_users}\n"
        f"� Пользователи с компаниями: {users_with_companies}\n"
        f"� Связей пользователь-компания: {total_company_links}\n"
        f"�️ Кликов по ссылкам акций: {total_clicks}\n"
        f"� Уникальных кликнувших: {users_clicked}",
        parse_mode="Markdown"
    )