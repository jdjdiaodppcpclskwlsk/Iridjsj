import aiofiles
import json
from typing import Dict, List, Any, Optional, Tuple
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

RARITY_EMOJI = {
    "Обычная": "⚪",
    "Редкая": "🔵",
    "Эпическая": "🟣",
    "Легендарная": "🟡",
    "Мифическая": "🔴"
}

CATEGORY_EMOJI = {
    "main": "🔑",
    "attack": "🗡️",
    "defense": "🛡️",
    "support": "🎗️"
}

CATEGORY_NAMES = {
    "main": "Основные",
    "attack": "Атакующие",
    "defense": "Защитные",
    "support": "Саппорт"
}

EFFECT_EMOJI = {
    "good": "🟢",
    "bad": "🔴"
}

async def load_perks_data() -> Dict[str, Any]:
    try:
        async with aiofiles.open("perks.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {"perks": {}}

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rarity, emoji in RARITY_EMOJI.items():
        builder.button(text=f"{emoji} {rarity} {emoji}", callback_data=f"perk_rarity:{rarity}")
    builder.adjust(1)
    return builder.as_markup()

def get_categories_keyboard(rarity: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, name in CATEGORY_NAMES.items():
        emoji = CATEGORY_EMOJI.get(key, "•")
        builder.button(text=f"{emoji} {name} {emoji}", callback_data=f"perk_category:{rarity}:{key}")
    builder.button(text="◀️ Назад", callback_data="back_to_main_perks")
    builder.adjust(1)
    return builder.as_markup()

def get_perks_list_keyboard(perks: List[Dict], rarity: str, category: str, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_perks = perks[start:end]
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    for perk in page_perks:
        builder.button(text=f"{emoji}{perk['name']}{emoji}", callback_data=f"perk_info:{rarity}:{category}:{perk['name']}")
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="⬅️", callback_data=f"perk_page:{rarity}:{category}:{page-1}")
    nav.button(text="🏠", callback_data=f"perk_category:{rarity}")
    if end < len(perks):
        nav.button(text="➡️", callback_data=f"perk_page:{rarity}:{category}:{page+1}")
    if nav.buttons:
        builder.attach(nav)
    builder.adjust(1)
    return builder.as_markup()

def format_perk_effects(perk: Dict) -> str:
    good = []
    bad = []
    for effect in perk.get("effects", []):
        etype = effect.get("type", "neutral")
        desc = effect.get("description", "")
        emoji = EFFECT_EMOJI.get(etype, "⚪")
        if etype == "good":
            good.append(f"{emoji} {desc}")
        else:
            bad.append(f"{emoji} {desc}")
    text = "\n\n".join(good)
    if good and bad:
        text += "\n\n"
    text += "\n\n".join(bad)
    return text.strip()

async def find_perk(perk_name: str) -> Tuple[Optional[Dict], Optional[str], Optional[str]]:
    data = await load_perks_data()
    perks = data.get("perks", {})
    for rarity, cats in perks.items():
        for key, perks_list in cats.items():
            for perk in perks_list:
                if perk["name"].lower() == perk_name.lower():
                    return perk, rarity, key
    return None, None, None