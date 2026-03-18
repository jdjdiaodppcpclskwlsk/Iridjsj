import sqlite3
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def init_guide_db():
    with sqlite3.connect("guide.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS guide_views (
                user_id INTEGER PRIMARY KEY,
                last_viewed TEXT,
                view_count INTEGER DEFAULT 1
            )
        """)
        conn.commit()

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Фарм", callback_data="menu_farm")
    builder.button(text="⭐ Престиж", callback_data="prestige")
    builder.adjust(1)
    return builder.as_markup()

def get_farm_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🪙 Золото", callback_data="farm_gold")
    builder.button(text="👹 Титаны", callback_data="farm_titans")
    builder.button(text="🎯 Рейды", callback_data="farm_raids")
    builder.button(text="◀️ Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()