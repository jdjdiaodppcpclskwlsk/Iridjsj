import json
import aiofiles
from typing import Dict, Any, Optional, Tuple
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

RARITY_COLORS = {
    "Обычная": "⚪",
    "Редкая": "🔵",
    "Эпическая": "🟣",
    "Легендарная": "🟡",
    "Мифическая": "🔴",
}

EMOJI_MAP = {
    "good": "🟢",
    "bad": "🔴",
    "skill": "🔵",
    "cooldown": "⚪",
    "neutral": "⚫",
}

async def load_families() -> Dict[str, Any]:
    try:
        async with aiofiles.open("families.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {"families": {}}

def get_rarity_emoji(rarity: str) -> str:
    if rarity == "Секретная":
        return "⚫"
    return RARITY_COLORS.get(rarity, "⚪")

async def get_families_keyboard() -> InlineKeyboardMarkup:
    families_data = await load_families()
    builder = InlineKeyboardBuilder()
    for rarity in families_data["families"].keys():
        emoji = get_rarity_emoji(rarity)
        builder.button(text=f"{emoji} {rarity} {emoji}", callback_data=f"family_rarity:{rarity}")
    builder.adjust(1)
    return builder.as_markup()

async def find_family(family_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    families_data = await load_families()
    for rarity, families in families_data["families"].items():
        for family in families:
            if family["name"].lower() == family_name.lower():
                return family, rarity
    return None, None

def format_family_text(family: Dict, rarity: str) -> str:
    emoji = get_rarity_emoji(rarity)
    text = f"{emoji} Фамилия: {family['name']}\n📊 Редкость: {rarity}\n\n"
    for buff in family["buffs"]:
        e = EMOJI_MAP.get(buff["type"], "⚫")
        if buff["description"]:
            text += f"{e} {buff['name']}\n   📝 {buff['description']}\n\n"
        else:
            text += f"{e} {buff['name']}\n\n"
    return text