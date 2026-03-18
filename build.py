import json
import aiofiles
import sqlite3
from typing import Dict, List, Any, Optional
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

BUILDS_PER_PAGE = 5

FAMILY_EMOJI = {
    "HELOS": "⚡",
    "FRITZ": "👑",
    "YEAGER": "⚔️",
    "ACKERMAN": "🗡️",
    "REISS": "🦅",
    "LEONHART": "🎭",
    "ZOE": "🔬",
    "BRAUS": "🛡️"
}

CATEGORY_EMOJI = {
    "ТИТАНЫ": "👹",
    "ОДМ": "🛡️",
    "КОПЬЯ": "⚡",
    "БАФФЕР": "📈",
    "КАРТОШКА": "🥔",
    "ТАНК": "🚜"
}

TITAN_EMOJI = {
    "АТАКУЮЩИЙ": "👊",
    "БРОНИРОВАННЫЙ": "🛡️",
    "ЖЕНСКИЙ": "💃"
}

def init_builds_db():
    with sqlite3.connect("builds.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_builds (
                user_id INTEGER PRIMARY KEY,
                favorite_build TEXT,
                last_viewed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

async def load_builds() -> Dict[str, Any]:
    try:
        async with aiofiles.open("build.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {"builds": {}}

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    families = ["HELOS", "FRITZ", "YEAGER", "ACKERMAN", "REISS", "LEONHART", "ZOE", "BRAUS"]
    for family in families:
        emoji = FAMILY_EMOJI.get(family, "•")
        builder.button(text=f"{emoji} {family}", callback_data=f"build_family:{family}")
    builder.adjust(2)
    return builder.as_markup()

def get_family_menu(family: str, builds_data: Dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    family_builds = builds_data.get("builds", {}).get(family, {})
    for category, subcats in family_builds.items():
        cat_emoji = CATEGORY_EMOJI.get(category, "•")
        if category == "ТИТАНЫ" and isinstance(subcats, dict):
            for titan_type in subcats.keys():
                titan_emoji = TITAN_EMOJI.get(titan_type, "👹")
                builder.button(text=f"{titan_emoji} {titan_type}", callback_data=f"build_view:{family}:{category}:{titan_type}")
        elif isinstance(subcats, dict):
            for subcat in subcats.keys():
                builder.button(text=f"{cat_emoji} {subcat}", callback_data=f"build_view:{family}:{category}:{subcat}")
        else:
            builder.button(text=f"{cat_emoji} {category}", callback_data=f"build_view:{family}:{category}")
    builder.button(text="◀️ Назад", callback_data="back_to_builds_main")
    builder.adjust(1)
    return builder.as_markup()