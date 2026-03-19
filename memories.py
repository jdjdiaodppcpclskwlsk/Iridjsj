import json
import aiofiles
from typing import Dict, Any
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database

router = Router()


async def load_memories() -> Dict[str, Any]:
    try:
        async with aiofiles.open("config/memories.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {}


def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐", callback_data="mem_1")
    builder.button(text="⭐⭐", callback_data="mem_2")
    builder.button(text="⭐⭐⭐", callback_data="mem_3")
    builder.button(text="⭐⭐⭐⭐", callback_data="mem_4")
    builder.adjust(4)
    return builder.as_markup()


def get_memories_keyboard(memories: Dict, page: int = 0, rarity: str = "") -> InlineKeyboardMarkup:
    memories_list = list(memories.items())
    start = page * 5
    end = start + 5
    page_memories = memories_list[start:end]
    builder = InlineKeyboardBuilder()
    for name, _ in page_memories:
        builder.button(text=name, callback_data=f"memory:{rarity}:{name}")
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="⬅️", callback_data=f"mempage:{rarity}:{page-1}")
    nav.button(text="🏠", callback_data="mem_home")
    if end < len(memories_list):
        nav.button(text="➡️", callback_data=f"mempage:{rarity}:{page+1}")
    if nav.buttons:
        builder.attach(nav)
    builder.adjust(1)
    return builder.as_markup()


@router.message(Command("memories"))
async def cmd_memories(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    msg = await message.answer("Мемори:", reply_markup=get_main_menu())
    database.save_session(uid, "memories", msg.message_id)
    await message.delete()


@router.callback_query(F.data.in_(["mem_1", "mem_2", "mem_3", "mem_4"]))
async def show_memories(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        return
    rarity = callback.data.split("_")[1]
    mems = await load_memories()
    m = mems.get(f"{rarity}_star", {})
    if not m:
        return
    kb = get_memories_keyboard(m, 0, rarity)
    try:
        await callback.message.edit_text("выбери нужное мемори:", reply_markup=kb)
    except:
        pass


@router.callback_query(F.data.startswith("mempage:"))
async def change_memory_page(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        return
    try:
        _, rarity, p = callback.data.split(":")
        p = int(p)
        mems = await load_memories()
        m = mems.get(f"{rarity}_star", {})
        if not m:
            return
        kb = get_memories_keyboard(m, p, rarity)
        await callback.message.edit_text("выбери нужное мемори:", reply_markup=kb)
    except:
        return


@router.callback_query(F.data.startswith("memory:"))
async def show_memory_info(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        return
    try:
        _, rarity, name = callback.data.split(":", 2)
        mems = await load_memories()
        desc = mems.get(f"{rarity}_star", {}).get(name)
        if not desc:
            return
        text = f"<b>{name}</b>\n\n{desc}"
        b = InlineKeyboardBuilder()
        b.button(text="⬅️", callback_data=f"mem_{rarity}")
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        return


@router.callback_query(F.data == "mem_home")
async def back_to_memories_main(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        return
    try:
        await callback.message.edit_text("Мемори:", reply_markup=get_main_menu())
    except:
        pass
