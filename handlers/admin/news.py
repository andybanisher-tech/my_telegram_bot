import asyncio
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import database as db
from keyboards.admin import get_categories_keyboard, get_preview_keyboard
from states import states
from handlers.main_menu import is_admin
import logging

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("admin"))
async def cmd_admin(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён.")
        return
    await state.set_state(states.NewsCreation.choosing_categories)
    await state.update_data(selected_categories=[], photos=[])
    await message.answer(
        "Выберите категории для рассылки. Можно выбрать несколько.\n"
        "Нажимайте на кнопки, чтобы отметить/снять отметку. Когда закончите, нажмите «✅ Готово».",
        reply_markup=get_categories_keyboard([])
    )

@router.callback_query(lambda c: c.data.startswith('select_'), states.NewsCreation.choosing_categories)
async def select_category(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    cat_id = int(callback.data.split('_')[1])
    data = await state.get_data()
    selected = data.get('selected_categories', [])
    if cat_id in selected:
        selected.remove(cat_id)
    else:
        selected.append(cat_id)
    await state.update_data(selected_categories=selected)
    await callback.message.edit_reply_markup(reply_markup=get_categories_keyboard(selected))
    await callback.answer()

@router.callback_query(lambda c: c.data == "categories_done", states.NewsCreation.choosing_categories)
async def categories_done(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    data = await state.get_data()
    selected = data.get('selected_categories', [])
    if not selected:
        await callback.answer("Выберите хотя бы одну категорию!", show_alert=True)
        return
    await state.set_state(states.NewsCreation.waiting_for_text)
    await callback.message.edit_text(
        "Отлично! Теперь отправьте текст новости (или отправьте /skip, чтобы оставить пустым)."
    )
    await callback.answer()

@router.message(states.NewsCreation.waiting_for_text)
async def process_text(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    if message.text == "/skip":
        text = ""
    else:
        text = message.text
    await state.update_data(news_text=text)
    await state.set_state(states.NewsCreation.waiting_for_photos)
    await message.answer(
        "Теперь отправляйте фотографии (по одной).\n"
        "Когда закончите, отправьте /done.\n"
        "Если фото не нужны, отправьте /skip_photos."
    )

@router.message(states.NewsCreation.waiting_for_photos, F.photo)
async def process_photo(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    data = await state.get_data()
    photos = data.get('photos', [])
    photos.append(message.photo[-1].file_id)
    await state.update_data(photos=photos)
    await message.answer(f"✅ Фото добавлено. Всего: {len(photos)}. Можете добавить ещё или отправить /done.")

@router.message(states.NewsCreation.waiting_for_photos, Command("done"))
async def photos_done(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await show_preview(message, state)

@router.message(states.NewsCreation.waiting_for_photos, Command("skip_photos"))
async def skip_photos(message: types.Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await show_preview(message, state)

async def show_preview(message: types.Message, state: FSMContext):
    data = await state.get_data()
    categories_ids = data.get('selected_categories', [])
    categories_names = [name for cid, name in db.get_categories() if cid in categories_ids]
    news_text = data.get('news_text', '')
    photos = data.get('photos', [])
    preview_text = f"📢 *Предпросмотр новости*\n\n"
    preview_text += f"*Категории:* {', '.join(categories_names)}\n"
    if news_text:
        preview_text += f"\n{news_text}\n"
    if photos:
        preview_text += f"\nФото: {len(photos)} шт. (первое показано ниже)"
    else:
        preview_text += f"\n(без фото)"
    await state.set_state(states.NewsCreation.preview)
    if photos:
        await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=photos[0],
            caption=preview_text,
            parse_mode="Markdown",
            reply_markup=get_preview_keyboard()
        )
    else:
        await message.answer(preview_text, parse_mode="Markdown", reply_markup=get_preview_keyboard())

@router.callback_query(lambda c: c.data == "send_news", states.NewsCreation.preview)
async def send_news(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    data = await state.get_data()
    categories_ids = data.get('selected_categories', [])
    news_text = data.get('news_text', '')
    photos = data.get('photos', [])
    users = db.get_users_by_categories(categories_ids)
    if not users:
        await callback.message.answer("❌ Нет подписчиков на выбранные категории.")
        await state.clear()
        return
    await callback.message.answer(f"⏳ Отправка новости {len(users)} подписчикам...")
    sent = 0
    failed = 0
    for uid in users:
        try:
            if photos:
                if len(photos) == 1:
                    await callback.bot.send_photo(
                        chat_id=uid,
                        photo=photos[0],
                        caption=news_text if news_text else None,
                        parse_mode="Markdown"
                    )
                else:
                    from aiogram.types import InputMediaPhoto
                    media = []
                    for i, file_id in enumerate(photos):
                        if i == 0:
                            media.append(InputMediaPhoto(media=file_id, caption=news_text, parse_mode="Markdown"))
                        else:
                            media.append(InputMediaPhoto(media=file_id))
                    await callback.bot.send_media_group(chat_id=uid, media=media)
            else:
                await callback.bot.send_message(chat_id=uid, text=news_text, parse_mode="Markdown")
            sent += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Не удалось отправить {uid}: {e}")
            failed += 1
    await callback.message.answer(f"✅ Рассылка завершена.\nОтправлено: {sent}\n❌ Ошибок: {failed}")
    await state.clear()

@router.callback_query(lambda c: c.data == "cancel_news", states.NewsCreation.preview)
async def cancel_news(callback: types.CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        await callback.answer("Недоступно")
        return
    await callback.message.edit_text("❌ Создание новости отменено.")
    await state.clear()
    await callback.answer()