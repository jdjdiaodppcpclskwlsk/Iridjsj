import json
import aiofiles
from typing import List, Dict, Any
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database

router = Router()

CODES_PER_PAGE = 5


async def load_codes() -> List[Dict[str, Any]]:
    try:
        async with aiofiles.open("config/codes.json", "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        codes = data.get("codes", [])
        codes.sort(key=lambda x: not x.get("active", False))
        return codes
    except:
        return []


def format_codes_page(codes: List[Dict[str, Any]], page: int) -> str:
    start = page * CODES_PER_PAGE
    end = start + CODES_PER_PAGE
    page_codes = codes[start:end]
    text = ""
    for c in page_codes:
        code = c.get("code", "???")
        reward = c.get("reward", "хз")
        active = c.get("active", False)
        status = "✅" if active else "❌"
        text += f"{status} <code>{code}</code> — {reward}\n"
    return text


def get_codes_keyboard(page: int, max_page: int, user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if page > 0:
        builder.button(text="⬅️ Назад", callback_data=f"page:{user_id}:{page - 1}")
    if page < max_page:
        builder.button(text="Вперёд ➡️", callback_data=f"page:{user_id}:{page + 1}")
    builder.adjust(2)
    return builder.as_markup()


@router.message(Command("code"))
async def code_command(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    user_id = message.from_user.id
    cds = await load_codes()
    max_page = (len(cds) - 1) // CODES_PER_PAGE
    text = format_codes_page(cds, 0)
    kb = get_codes_keyboard(0, max_page, user_id)
    await message.answer(text, reply_markup=kb)
    await message.delete()


@router.callback_query(F.data.startswith("page:"))
async def process_page(callback: CallbackQuery):
    await callback.answer()
    _, uid, p = callback.data.split(":")
    uid, p = int(uid), int(p)
    if callback.from_user.id != uid:
        return
    cds = await load_codes()
    max_page = (len(cds) - 1) // CODES_PER_PAGE
    text = format_codes_page(cds, p)
    kb = get_codes_keyboard(p, max_page, uid)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
    except:
        pass
