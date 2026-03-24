import sqlite3
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database as db
from handlers.main_menu import is_admin

router = Router()

@router.message(Command("stats"))
async def cmd_stats(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    stats = db.get_category_subscribers_count()
    if not stats:
        await message.answer("Нет данных о подписчиках.")
        return
    lines = ["📊 *Статистика подписчиков по категориям:*\n"]
    total = 0
    for cat, count in stats.items():
        lines.append(f"• {cat}: {count}")
        total += count
    lines.append(f"\n*Всего подписок:* {total}")
    conn = sqlite3.connect(db.DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT user_id) FROM subscriptions")
    unique_users = cur.fetchone()[0]
    conn.close()
    lines.append(f"*Уникальных пользователей:* {unique_users}")
    await message.answer("\n".join(lines), parse_mode="Markdown")