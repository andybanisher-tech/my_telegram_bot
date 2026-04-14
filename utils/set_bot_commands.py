import logging
from aiogram.types import BotCommand, BotCommandScopeDefault, BotCommandScopeChat
import database as db
from config import STATIC_ADMINS

logger = logging.getLogger(__name__)

async def set_bot_commands(bot):
    default_commands = [
        BotCommand(command="start", description="👋 Главное меню"),
        #BotCommand(command="cancel", description="❌ Отменить текущее действие"),
    ]
    await bot.set_my_commands(default_commands, scope=BotCommandScopeDefault())

    admin_extra = [
    #BotCommand(command="admin", description="📢 Создать новость"),
    #BotCommand(command="stats", description="📊 Статистика"),
    #BotCommand(command="categories", description="🏷️ Управление категориями"),
    #BotCommand(command="manage_admins", description="👥 Управление админами"),
    #BotCommand(command="manage_managers", description="👥 Управление менеджерами"),
    #BotCommand(command="send", description="✉️ Быстрая рассылка"),
]
    admin_full = default_commands + admin_extra
    
    

    for admin_id in STATIC_ADMINS:
        try:
            await bot.set_my_commands(admin_full, scope=BotCommandScopeChat(chat_id=admin_id))
        except Exception as e:
            logger.error(f"Ошибка установки команд для статического админа {admin_id}: {e}")

    for admin in db.get_db_admins():
        if admin["id"] not in STATIC_ADMINS:
            try:
                await bot.set_my_commands(admin_full, scope=BotCommandScopeChat(chat_id=admin["id"]))
            except Exception as e:
                logger.error(f"Ошибка установки команд для админа {admin['id']}: {e}")