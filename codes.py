import json
import aiofiles
from typing import List, Dict, Any
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

CODES_PER_PAGE = 5

async def load_codes() -> List[Dict[str, Any]]:
    try:
        async with aiofiles.open("codes.json", "r", encoding="utf-8") as f:
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