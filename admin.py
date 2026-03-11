import asyncio
import sqlite3
from typing import List, Tuple
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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