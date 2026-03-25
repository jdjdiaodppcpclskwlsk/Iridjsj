import json
import aiofiles
from typing import Dict, Any
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

async def load_memories() -> Dict[str, Any]:
    try:
        async with aiofiles.open("memories.json", "r", encoding="utf-8") as f:
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