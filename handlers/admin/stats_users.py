import logging
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database as db
from utils.helpers import is_admin

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("stats_users"))
async def cmd_stats_users(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    stats = db.get_stats()
    total_users = stats['total_users']
    lines = [f"� *Статистика*\n\n� *Всего пользователей:* {total_users}\n\n*Переходы по акциям:*"]
    partners = stats['partners']
    if not partners:
        lines.append("Нет данных")
    else:
        for code, data in partners.items():
            clicks = data['clicks']
            # Если хотите показывать и уникальных пользователей по партнёру, раскомментируйте:
            # users = data['users']
            lines.append(f"• {code}: {clicks} кликов")
    await message.answer("\n".join(lines), parse_mode="Markdown")