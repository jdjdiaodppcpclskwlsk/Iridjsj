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

def get_main_menu_perks() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for rarity, emoji in RARITY_EMOJI.items():
        builder.button(
            text=f"{emoji} {rarity} {emoji}",
            callback_data=f"perk_rarity:{rarity}"
        )
    
    builder.adjust(1)
    return builder.as_markup()

def get_categories_keyboard(rarity: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    
    for category_key, category_name in CATEGORY_NAMES.items():
        emoji = CATEGORY_EMOJI.get(category_key, "•")
        builder.button(
            text=f"{emoji} {category_name} {emoji}",
            callback_data=f"perk_category:{rarity}:{category_key}"
        )
    
    builder.button(text="◀️ Назад", callback_data="back_to_main_perks")
    builder.adjust(1)
    
    return builder.as_markup()

def get_perks_list_keyboard(perks: List[Dict], rarity: str, category: str, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    perks_per_page = 5
    start = page * perks_per_page
    end = start + perks_per_page
    page_perks = perks[start:end]
    rarity_emoji = RARITY_EMOJI.get(rarity, "⚪")
    
    for perk in page_perks:
        builder.button(
            text=f"{rarity_emoji}{perk['name']}{rarity_emoji}",
            callback_data=f"perk_info:{rarity}:{category}:{perk['name']}"
        )
    
    nav_builder = InlineKeyboardBuilder()
    
    if page > 0:
        nav_builder.button(
            text="⬅️",
            callback_data=f"perk_page:{rarity}:{category}:{page-1}"
        )
    
    nav_builder.button(text="🏠", callback_data=f"perk_category:{rarity}")
    
    if end < len(perks):
        nav_builder.button(
            text="➡️",
            callback_data=f"perk_page:{rarity}:{category}:{page+1}"
        )
    
    if nav_builder.buttons:
        builder.attach(nav_builder)
    
    builder.adjust(1)
    return builder.as_markup()

def format_perk_effects(perk: Dict) -> str:
    good_effects = []
    bad_effects = []
    
    for effect in perk.get("effects", []):
        effect_type = effect.get("type", "neutral")
        description = effect.get("description", "")
        emoji = EFFECT_EMOJI.get(effect_type, "⚪")
        
        if effect_type == "good":
            good_effects.append(f"{emoji} {description}")
        else:
            bad_effects.append(f"{emoji} {description}")
    
    text = ""
    
    if good_effects:
        text += "\n\n".join(good_effects)
    
    if bad_effects:
        if good_effects:
            text += "\n\n"
        text += "\n\n".join(bad_effects)
    
    return text.strip()

async def find_perk(perk_name: str) -> Tuple[Optional[Dict], Optional[str], Optional[str]]:
    perks_data = await load_perks_data()
    perks = perks_data.get("perks", {})
    
    for rarity, categories in perks.items():
        for category_key, perks_list in categories.items():
            for perk in perks_list:
                if perk["name"].lower() == perk_name.lower():
                    return perk, rarity, category_key
    
    return None, None, None