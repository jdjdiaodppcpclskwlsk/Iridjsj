from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Фарм", callback_data="menu_farm")
    builder.button(text="⭐ Престиж", callback_data="prestige")
    builder.button(text="⚡ Билды", callback_data="menu_builds")
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

def get_builds_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="👑 Fritz", callback_data="build_fritz")
    builder.button(text="⚡ Helos", callback_data="build_helos")
    builder.button(text="🗡️ Ackerman", callback_data="build_ackerman")
    builder.button(text="🎭 Leonhart", callback_data="build_leonhart")
    builder.button(text="◀️ Назад", callback_data="back_main")
    builder.adjust(1)
    return builder.as_markup()

def get_fritz_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡️ ОДМ", callback_data="fritz_odm")
    builder.button(text="👊 Атак титан", callback_data="fritz_attack")
    builder.button(text="💃 Фем титан", callback_data="fritz_female")
    builder.button(text="◀️ Назад", callback_data="menu_builds")
    builder.adjust(1)
    return builder.as_markup()

def get_helos_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡️ ОДМ", callback_data="helos_odm")
    builder.button(text="⚡ Громовые Копья", callback_data="helos_spears")
    builder.button(text="📈 Баффер", callback_data="helos_buffer")
    builder.button(text="◀️ Назад", callback_data="menu_builds")
    builder.adjust(1)
    return builder.as_markup()

def get_ackerman_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🛡️ ОДМ", callback_data="ackerman_odm")
    builder.button(text="⚡ Громовые Копья", callback_data="ackerman_spears")
    builder.button(text="◀️ Назад", callback_data="menu_builds")
    builder.adjust(1)
    return builder.as_markup()

def get_leonhart_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💃 Фемка", callback_data="leonhart_female")
    builder.button(text="◀️ Назад", callback_data="menu_builds")
    builder.adjust(1)
    return builder.as_markup()