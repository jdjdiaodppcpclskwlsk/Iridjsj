import sqlite3
import asyncio
from typing import List, Tuple
from aiogram import Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

class MailingStates(StatesGroup):
    waiting_for_text = State()

def get_admin_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📨 Рассылка", callback_data="admin_mailing")
    builder.adjust(1)
    return builder.as_markup()

async def get_all_chats() -> List[Tuple[int]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        result = conn.execute(
            "SELECT chat_id FROM verified_chats WHERE verified = 1"
        ).fetchall()
        return result

async def get_all_users() -> List[Tuple[int]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        result = conn.execute(
            "SELECT DISTINCT user_id FROM user_sessions"
        ).fetchall()
        return result

async def send_mailing(bot: Bot, text: str) -> Tuple[int, int]:
    chats = await get_all_chats()
    users = await get_all_users()
    
    sent_count = 0
    failed_count = 0
    
    for chat in chats:
        try:
            await bot.send_message(chat[0], text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except:
            failed_count += 1
    
    for user in users:
        try:
            await bot.send_message(user[0], text)
            sent_count += 1
            await asyncio.sleep(0.05)
        except:
            failed_count += 1
    
    return sent_count, failed_count