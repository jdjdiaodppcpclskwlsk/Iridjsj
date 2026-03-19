import asyncio
import sqlite3
from typing import List, Tuple
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

CREATOR_ID = 7306010609


class MailingStates(StatesGroup):
    waiting_for_text = State()


def get_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📨 Рассылка", callback_data="admin_mailing")
    builder.button(text="📊 Статистика", callback_data="admin_stats")
    builder.button(text="📬 Заявки", callback_data="offers_menu")
    builder.adjust(1)
    return builder.as_markup()


async def get_all_chats() -> List[Tuple[int]]:
    with sqlite3.connect("chats.db") as conn:
        return conn.execute("SELECT chat_id FROM verified_chats WHERE verified = 1").fetchall()


async def get_all_users() -> List[Tuple[int]]:
    with sqlite3.connect("users.db") as conn:
        return conn.execute("SELECT user_id FROM users").fetchall()


async def send_mailing(bot: Bot, text: str) -> Tuple[int, int]:
    chats = await get_all_chats()
    users = await get_all_users()
    sent, failed = 0, 0
    for chat in chats:
        try:
            await bot.send_message(chat[0], text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    for user in users:
        try:
            await bot.send_message(user[0], text)
            sent += 1
            await asyncio.sleep(0.05)
        except:
            failed += 1
    return sent, failed


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав для админ-панели.")
        return
    await state.clear()
    await message.answer("Админ-панель:\nВыбери действие:", reply_markup=get_admin_menu())


@router.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(MailingStates.waiting_for_text)
    await callback.message.edit_text("Введи текст для рассылки:\n(отправь сообщение с текстом)")


@router.message(MailingStates.waiting_for_text)
async def process_mailing_text(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        await state.clear()
        return
    if not message.text:
        await message.answer("Отправь текстовое сообщение.")
        return
    status = await message.answer("Начинаю рассылку...")
    sent, failed = await send_mailing(bot, message.text)
    await status.edit_text(f"Рассылка завершена!\nОтправлено: {sent}\nНе удалось: {failed}")
    await state.clear()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    import database
    users = database.get_all_users()
    chats = database.get_all_verified_chats()
    text = f"Статистика:\n\nПользователей: {len(users)}\nЧатов: {len(chats)}"
    await callback.message.edit_text(text, reply_markup=get_admin_menu())


@router.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text("Админ-панель:\nВыбери действие:", reply_markup=get_admin_menu())
