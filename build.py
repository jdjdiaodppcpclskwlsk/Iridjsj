import json
import aiofiles
import sqlite3
from typing import Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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

DISPLAY_NAMES = {
    "helos_odm": "🛡️ ОДМ",
    "helos_spears": "⚡ Громовые Копья",
    "helos_buffer": "📈 Баффер",
    "fritz_odm": "🛡️ ОДМ",
    "fritz_attack": "👊 Атакующий Титан",
    "fritz_female": "💃 Женский Титан",
    "fritz_spears": "⚡ Громовые Копья",
    "fritz_buffer": "📈 Баффер",
    "yeager_attack": "👊 Атакующий Титан",
    "yeager_armored": "🛡️ Бронированный Титан",
    "yeager_female": "💃 Женский Титан",
    "yeager_odm": "🛡️ ОДМ",
    "yeager_spears": "⚡ Громовые Копья",
    "ackerman_odm": "🛡️ ОДМ",
    "ackerman_spears": "⚡ Громовые Копья",
    "reiss_attack": "👊 Атакующий Титан",
    "reiss_armored": "🛡️ Бронированный Титан",
    "reiss_female": "💃 Женский Титан",
    "reiss_odm": "🛡️ ОДМ",
    "reiss_spears": "⚡ Громовые Копья",
    "reiss_buffer": "📈 Баффер",
    "leonhart_attack": "👊 Атакующий Титан",
    "leonhart_female": "💃 Женский Титан",
    "leonhart_odm": "🛡️ ОДМ",
    "leonhart_spears": "⚡ Громовые Копья",
    "leonhart_buffer": "📈 Баффер",
    "zoe_odm": "🛡️ ОДМ",
    "zoe_spears": "⚡ Громовые Копья",
    "braus_potato": "🥔 Картошка",
    "braus_tank": "🚜 Танк"
}

def init_builds_db():
    with sqlite3.connect("builds.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_builds (
                user_id INTEGER PRIMARY KEY,
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
    
    for build_key, build_text in family_builds.items():
        if build_text:
            display = DISPLAY_NAMES.get(build_key, build_key)
            builder.button(text=display, callback_data=f"build_view:{family}:{build_key}")
    
    builder.button(text="◀️ Назад", callback_data="back_to_builds_main")
    builder.adjust(1)
    return builder.as_markup()