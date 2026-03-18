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

DISPLAY_NAMES = {
    "ОДМ": "⚔️ ОДМ",
    "КОПЬЯ": "⚡ Громовые Копья",
    "БАФФЕР": "📈 Баффер",
    "ТИТАНЫ": "👹 Титаны",
    "АТАКУЮЩИЙ": "👊 Атакующий",
    "БРОНИРОВАННЫЙ": "🛡️ Бронированный",
    "ЖЕНСКИЙ": "💃 Женский",
    "КАРТОШКА": "🥔 Картошка",
    "ТАНК": "🚜 Танк"
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
        if category == "ТИТАНЫ" and isinstance(subcats, dict):
            for titan_type in subcats.keys():
                display = DISPLAY_NAMES.get(titan_type, titan_type)
                builder.button(text=display, callback_data=f"build_view:{family}:{category}:{titan_type}")
        elif isinstance(subcats, dict):
            for subcat in subcats.keys():
                display = DISPLAY_NAMES.get(category, category)
                builder.button(text=display, callback_data=f"build_view:{family}:{category}:{subcat}")
            break
        else:
            display = DISPLAY_NAMES.get(category, category)
            builder.button(text=display, callback_data=f"build_view:{family}:{category}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_builds_main")
    builder.adjust(1)
    return builder.as_markup()

def save_user_favorite(user_id: int, build_name: str):
    with sqlite3.connect("builds.db") as conn:
        conn.execute("""
            INSERT OR REPLACE INTO user_builds (user_id, favorite_build, last_viewed)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (user_id, build_name))
        conn.commit()

def get_user_favorite(user_id: int) -> Optional[str]:
    with sqlite3.connect("builds.db") as conn:
        result = conn.execute("SELECT favorite_build FROM user_builds WHERE user_id = ?", (user_id,)).fetchone()
        return result[0] if result else None