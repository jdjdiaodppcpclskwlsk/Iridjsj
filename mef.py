import asyncio
import json
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import aiofiles
from aiogram import Bot, Dispatcher, F, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from aiogram.utils.callback_answer import CallbackAnswerMiddleware
from aiogram.utils.chat_action import ChatActionMiddleware
from aiogram.utils.keyboard import InlineKeyboardBuilder

from perks import (
    load_perks_data, get_main_menu_perks, get_categories_keyboard,
    get_perks_list_keyboard, format_perk_effects, find_perk,
    RARITY_EMOJI, CATEGORY_NAMES, CATEGORY_EMOJI
)

from admin import MailingStates, get_admin_menu, send_mailing
from offer import (
    OfferStates, OfferStatus, create_offer, get_user_offers,
    get_offers_by_status, get_offer_by_id, update_offer_status,
    get_offers_menu, get_user_offers_keyboard, get_offers_list_keyboard,
    format_offer_text, send_offer_notification, get_offer_main_menu
)

BOT_TOKEN = "8377727368:AAHUmJu_dUSJ-ZmwDWHP4mNdtvQNP39kRZM"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

CREATOR_ID = 7306010609

CODES_PER_PAGE = 5

EMOJI_MAP = {
    "good": "🟢",
    "bad": "🔴",
    "skill": "🔵",
    "cooldown": "⚪",
    "neutral": "⚫",
}

RARITY_COLORS = {
    "Обычная": "⚪",
    "Редкая": "🔵",
    "Эпическая": "🟣",
    "Легендарная": "🟡",
    "Мифическая": "🔴",
}

PERK_TYPES = {
    "Основной": "main",
    "Атакующий": "attack",
    "Дефенс": "defense",
    "Саппорт": "support",
}


def init_db() -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS verified_chats (
                chat_id INTEGER PRIMARY KEY,
                chat_title TEXT,
                verified BOOLEAN NOT NULL DEFAULT 1,
                added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                user_id INTEGER,
                session_type TEXT,
                message_id INTEGER,
                PRIMARY KEY (user_id, session_type)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                offer_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                offer_name TEXT NOT NULL,
                description TEXT NOT NULL,
                benefit TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                reviewed_at TIMESTAMP,
                reviewed_by INTEGER
            )
        """)
        
        conn.commit()


def save_user_session(user_id: int, session_type: str, message_id: int) -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO user_sessions (user_id, session_type, message_id)
            VALUES (?, ?, ?)
        """,
            (user_id, session_type, message_id),
        )
        conn.commit()


def get_user_session(user_id: int, session_type: str) -> Optional[int]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        result = conn.execute(
            """
            SELECT message_id FROM user_sessions 
            WHERE user_id = ? AND session_type = ?
        """,
            (user_id, session_type),
        ).fetchone()
        return result[0] if result else None


def check_session_access(user_id: int, message_id: int, session_type: str) -> bool:
    saved_message_id = get_user_session(user_id, session_type)
    return saved_message_id == message_id


def add_user_to_db(user_id: int, first_name: str, username: str = None) -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (user_id, first_name, username, last_activity)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (user_id, first_name, username))
        conn.commit()


def update_user_activity(user_id: int) -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute("""
            UPDATE users SET last_activity = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (user_id,))
        conn.commit()


def add_chat_to_db(chat_id: int, chat_title: str) -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute("""
            INSERT OR IGNORE INTO verified_chats (chat_id, chat_title, verified)
            VALUES (?, ?, 1)
        """, (chat_id, chat_title))
        conn.commit()


def remove_chat_from_db(chat_id: int) -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute("""
            UPDATE verified_chats SET verified = 0
            WHERE chat_id = ?
        """, (chat_id,))
        conn.commit()


def check_chat_verification(chat_id: int) -> bool:
    if chat_id > 0:
        return True

    with sqlite3.connect("verified_mega_aotr.db") as conn:
        result = conn.execute(
            "SELECT verified FROM verified_chats WHERE chat_id = ?", (chat_id,)
        ).fetchone()
        return result is not None and result[0] == 1


def get_all_verified_chats() -> List[Tuple[int, str]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        result = conn.execute(
            "SELECT chat_id, chat_title FROM verified_chats WHERE verified = 1"
        ).fetchall()
        return result


def get_all_users() -> List[Tuple[int, str, str]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        result = conn.execute(
            "SELECT user_id, first_name, username FROM users"
        ).fetchall()
        return result


async def load_memories() -> Dict[str, Any]:
    try:
        async with aiofiles.open("memories.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {}


async def load_families() -> Dict[str, Any]:
    try:
        async with aiofiles.open("families.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {"families": {}}


async def load_config() -> Dict[str, Any]:
    try:
        async with aiofiles.open("config.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {}


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
        builder.button(
            text="⬅️ Назад",
            callback_data=f"page:{user_id}:{page - 1}",
        )
    if page < max_page:
        builder.button(
            text="Вперёд ➡️",
            callback_data=f"page:{user_id}:{page + 1}",
        )

    builder.adjust(2)
    return builder.as_markup()


async def find_family(family_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    families_data = await load_families()
    for rarity, families in families_data["families"].items():
        for family in families:
            if family["name"].lower() == family_name.lower():
                return family, rarity
    return None, None


def get_rarity_emoji(rarity: str) -> str:
    if rarity == "Секретная":
        return "⚫"
    return RARITY_COLORS.get(rarity, "⚪")


def get_main_menu_families() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    return builder.as_markup()


async def get_families_keyboard() -> InlineKeyboardMarkup:
    families_data = await load_families()
    builder = InlineKeyboardBuilder()

    for rarity in families_data["families"].keys():
        emoji_circle = get_rarity_emoji(rarity)
        builder.button(
            text=f"{emoji_circle} {rarity} {emoji_circle}",
            callback_data=f"family_rarity:{rarity}",
        )

    builder.adjust(1)
    return builder.as_markup()


def get_main_menu_guide() -> InlineKeyboardMarkup:
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


def get_main_menu_memories() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⭐", callback_data="mem_1")
    builder.button(text="⭐⭐", callback_data="mem_2")
    builder.button(text="⭐⭐⭐", callback_data="mem_3")
    builder.button(text="⭐⭐⭐⭐", callback_data="mem_4")
    builder.adjust(4)
    return builder.as_markup()


def get_memories_keyboard(
    memories_dict: Dict, page: int = 0, rarity: str = ""
) -> InlineKeyboardMarkup:
    memories_list = list(memories_dict.items())
    start_idx = page * 5
    end_idx = start_idx + 5
    page_memories = memories_list[start_idx:end_idx]

    builder = InlineKeyboardBuilder()

    for memory_name, _ in page_memories:
        builder.button(
            text=memory_name,
            callback_data=f"memory:{rarity}:{memory_name}",
        )

    nav_builder = InlineKeyboardBuilder()
    if page > 0:
        nav_builder.button(
            text="⬅️", callback_data=f"mempage:{rarity}:{page - 1}"
        )

    nav_builder.button(text="🏠", callback_data="mem_home")

    if end_idx < len(memories_list):
        nav_builder.button(
            text="➡️", callback_data=f"mempage:{rarity}:{page + 1}"
        )

    if nav_builder.buttons:
        builder.attach(nav_builder)

    builder.adjust(1)
    return builder.as_markup()


@dp.message.middleware()
async def track_users_middleware(handler, event: Message, data: dict):
    if event.from_user:
        add_user_to_db(
            event.from_user.id,
            event.from_user.first_name,
            event.from_user.username
        )
    return await handler(event, data)


@dp.callback_query.middleware()
async def check_verification_middleware(
    handler, event: CallbackQuery, data: dict
):
    if not check_chat_verification(event.message.chat.id):
        await event.answer("Чат не верифицирован", show_alert=True)
        return
    return await handler(event, data)


@dp.message(Command("AotrOn"))
async def cmd_verification_on(message: Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        return

    chat_id = message.chat.id
    chat_title = message.chat.title or "Личный чат"
    
    add_chat_to_db(chat_id, chat_title)
    
    await message.answer("✅ Чат верифицирован.")


@dp.message(Command("AotrOff"))
async def cmd_verification_off(message: Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        return

    chat_id = message.chat.id
    remove_chat_from_db(chat_id)
    
    await message.answer("❌ Верификация отключена.")


@dp.message(Command("start_aotrcode"))
async def start_handler(message: Message):
    await message.answer("Бот активен все збс.")


@dp.message(Command("code"))
async def code_command(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    user_id = message.from_user.id
    codes = await load_codes()
    max_page = (len(codes) - 1) // CODES_PER_PAGE

    text = format_codes_page(codes, 0)
    keyboard = get_codes_keyboard(0, max_page, user_id)
    await message.answer(text, reply_markup=keyboard)
    await message.delete()


@dp.callback_query(F.data.startswith("page:"))
async def process_callback_page(callback: CallbackQuery):
    await callback.answer()

    _, user_id_str, page_str = callback.data.split(":")
    user_id = int(user_id_str)
    page = int(page_str)

    if callback.from_user.id != user_id:
        return

    codes = await load_codes()
    max_page = (len(codes) - 1) // CODES_PER_PAGE

    text = format_codes_page(codes, page)
    keyboard = get_codes_keyboard(page, max_page, user_id)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        pass


@dp.message(Command("families"))
async def cmd_families(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    user_id = message.from_user.id
    keyboard = await get_families_keyboard()

    if message.reply_to_message:
        msg = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            text="Фамилии:",
            reply_markup=keyboard,
        )
        save_user_session(user_id, "families", msg.message_id)
    else:
        msg = await message.answer("Фамилии:", reply_markup=keyboard)
        save_user_session(user_id, "families", msg.message_id)

    await message.delete()


@dp.message(Command("search"))
async def cmd_search(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    if len(message.text.split()) < 2:
        await message.answer("Правильный формат: /search [фамилия]")
        return

    family_name = " ".join(message.text.split()[1:])
    family_data, rarity = await find_family(family_name)

    if not family_data:
        await message.answer(f"Фамилии '{family_name}' нема")
        return

    emoji_circle = get_rarity_emoji(rarity)

    text = f"{emoji_circle} Фамилия: {family_data['name']}\n📊 Редкость: {rarity}\n\n"

    for buff in family_data["buffs"]:
        emoji = EMOJI_MAP.get(buff["type"], "⚫")
        if buff["description"]:
            text += f"{emoji} {buff['name']}\n   📝 {buff['description']}\n\n"
        else:
            text += f"{emoji} {buff['name']}\n\n"

    await message.answer(text)
    await message.delete()


@dp.callback_query(F.data.startswith("family_rarity:"))
async def show_families(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return

    rarity = callback.data.split(":", 1)[1]
    families_data = await load_families()
    families = families_data["families"].get(rarity, [])

    builder = InlineKeyboardBuilder()
    emoji_circle = get_rarity_emoji(rarity)

    for family in families:
        builder.button(
            text=f"{emoji_circle} {family['name']} {emoji_circle}",
            callback_data=f"family:{rarity}:{family['name']}",
        )

    builder.button(text="⬅️ Назад", callback_data="back_to_main_families")
    builder.adjust(1)

    try:
        await callback.message.edit_text(
            f"🎲 Фамилия: {rarity}\nВыбирай:", reply_markup=builder.as_markup()
        )
    except:
        pass


@dp.callback_query(F.data.startswith("family:"))
async def show_family_info(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return

    _, rarity, family_name = callback.data.split(":", 2)

    families_data = await load_families()
    family_data = None
    for family in families_data["families"][rarity]:
        if family["name"] == family_name:
            family_data = family
            break

    if not family_data:
        return

    emoji_circle = get_rarity_emoji(rarity)

    text = f"{emoji_circle} Фамилия: {family_name}\n📊 Редкость: {rarity}\n\n"

    for buff in family_data["buffs"]:
        emoji = EMOJI_MAP.get(buff["type"], "⚫")
        if buff["description"]:
            text += f"{emoji} {buff['name']}\n   📝 {buff['description']}\n\n"
        else:
            text += f"{emoji} {buff['name']}\n\n"

    builder = InlineKeyboardBuilder()
    builder.button(
        text="⬅️ Назад к фамилиям",
        callback_data=f"family_rarity:{rarity}",
    )

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data == "back_to_main_families")
async def back_to_main_families(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return

    keyboard = await get_families_keyboard()
    try:
        await callback.message.edit_text("Фамилии:", reply_markup=keyboard)
    except:
        pass


@dp.message(Command("guide"))
async def cmd_guide(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    user_id = message.from_user.id

    msg = await message.answer(
        "🎮 Выбирай:", reply_markup=get_main_menu_guide()
    )

    save_user_session(user_id, "guide", msg.message_id)
    await message.delete()


@dp.callback_query(F.data == "menu_farm")
async def menu_farm(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "💰 Фарм:", reply_markup=get_farm_menu()
        )
    except:
        pass


@dp.callback_query(F.data == "menu_builds")
async def menu_builds(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "⚡ Билды:", reply_markup=get_builds_menu()
        )
    except:
        pass


@dp.callback_query(F.data == "prestige")
async def menu_prestige(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    config_data = await load_config()
    text = config_data.get("prestige", {}).get("text", "Информация о престиже")

    if not text or text.strip() == "":
        text = "нихуя нема"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="back_main")

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data == "farm_gold")
async def farm_gold(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    config_data = await load_config()
    text = config_data.get("farm", {}).get("gold", "Информация о фарме золота")

    if not text or text.strip() == "":
        text = "нихуя нема"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="menu_farm")

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data == "farm_titans")
async def farm_titans(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    config_data = await load_config()
    text = config_data.get("farm", {}).get("titans", "Информация о фарме титанов")

    if not text or text.strip() == "":
        text = "нихуя нема"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="menu_farm")

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data == "farm_raids")
async def farm_raids(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    config_data = await load_config()
    text = config_data.get("farm", {}).get("raids", "Информация о рейдах")

    if not text or text.strip() == "":
        text = "нихуя нема"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="menu_farm")

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data == "build_fritz")
async def build_fritz(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "👑 Билды Fritz:", reply_markup=get_fritz_menu()
        )
    except:
        pass


@dp.callback_query(F.data == "build_helos")
async def build_helos(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "⚡ Билды Helos:", reply_markup=get_helos_menu()
        )
    except:
        pass


@dp.callback_query(F.data == "build_ackerman")
async def build_ackerman(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "🗡️ Билды Ackerman:", reply_markup=get_ackerman_menu()
        )
    except:
        pass


@dp.callback_query(F.data == "build_leonhart")
async def build_leonhart(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "🎭 Билды Leonhart:", reply_markup=get_leonhart_menu()
        )
    except:
        pass


@dp.callback_query(F.data.startswith(("fritz_", "helos_", "ackerman_", "leonhart_")))
async def handle_builds(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    build_type = callback.data
    parts = build_type.split("_")
    character = parts[0]

    config_data = await load_config()
    text = (
        config_data.get("builds", {})
        .get(character, {})
        .get(build_type, "Информация о билде")
    )

    if not text or text.strip() == "":
        text = "нихуя нема"

    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=f"build_{character}")

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "guide"):
        return

    try:
        await callback.message.edit_text(
            "🎮 Выбирай:", reply_markup=get_main_menu_guide()
        )
    except:
        pass


@dp.message(Command("memories"))
async def cmd_memories(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    user_id = message.from_user.id

    msg = await message.answer(
        "Мемори:", reply_markup=get_main_menu_memories()
    )

    save_user_session(user_id, "memories", msg.message_id)
    await message.delete()


@dp.callback_query(F.data.in_(["mem_1", "mem_2", "mem_3", "mem_4"]))
async def show_memories(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "memories"):
        return

    rarity = callback.data.split("_")[1]
    memories_data = await load_memories()
    memories = memories_data.get(f"{rarity}_star", {})

    if not memories:
        return

    keyboard = get_memories_keyboard(memories, 0, rarity)
    try:
        await callback.message.edit_text(
            "выбери нужное мемори:", reply_markup=keyboard
        )
    except:
        pass


@dp.callback_query(F.data.startswith("mempage:"))
async def change_memory_page(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "memories"):
        return

    try:
        _, rarity, page_str = callback.data.split(":")
        page = int(page_str)

        memories_data = await load_memories()
        memories = memories_data.get(f"{rarity}_star", {})

        if not memories:
            return

        keyboard = get_memories_keyboard(memories, page, rarity)
        await callback.message.edit_text(
            "выбери нужное мемори:", reply_markup=keyboard
        )
    except:
        return


@dp.callback_query(F.data.startswith("memory:"))
async def show_memory_info(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "memories"):
        return

    try:
        _, rarity, memory_name = callback.data.split(":", 2)

        memories_data = await load_memories()
        memories = memories_data.get(f"{rarity}_star", {})
        memory_description = memories.get(memory_name)

        if not memory_description:
            return

        text = f"<b>{memory_name}</b>\n\n{memory_description}"

        builder = InlineKeyboardBuilder()
        builder.button(text="⬅️", callback_data=f"mem_{rarity}")

        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        return


@dp.callback_query(F.data == "mem_home")
async def back_to_memories_main(callback: CallbackQuery):
    await callback.answer()

    user_id = callback.from_user.id
    message_id = callback.message.message_id

    if not check_session_access(user_id, message_id, "memories"):
        return

    try:
        await callback.message.edit_text(
            "Мемори:", reply_markup=get_main_menu_memories()
        )
    except:
        pass


@dp.message(Command("perks"))
async def cmd_perks(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    user_id = message.from_user.id
    
    msg = await message.answer(
        "⚡ Перки:\nВыбери редкость:",
        reply_markup=get_main_menu_perks()
    )
    
    save_user_session(user_id, "perks", msg.message_id)
    await message.delete()


@dp.message(Command("searchp"))
async def cmd_search_perk(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return

    if len(message.text.split()) < 2:
        await message.answer("Правильный формат: /searchp [название перка]")
        return

    perk_name = " ".join(message.text.split()[1:])
    perk_data, rarity, category_key = await find_perk(perk_name)

    if not perk_data:
        await message.answer(f"Перк '{perk_name}' не найден")
        return

    emoji = RARITY_EMOJI.get(rarity, "⚪")
    category_name = CATEGORY_NAMES.get(category_key, "")
    category_emoji = CATEGORY_EMOJI.get(category_key, "•")
    
    text = f"{emoji} <b>{perk_name}</b>\n"
    text += f"📊 Редкость: {rarity}\n"
    text += f"{category_emoji} Категория: {category_name}\n\n"
    text += format_perk_effects(perk_data)

    await message.answer(text)
    await message.delete()


@dp.callback_query(F.data.startswith("perk_rarity:"))
async def process_perk_rarity(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    
    rarity = callback.data.split(":", 1)[1]
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    
    try:
        await callback.message.edit_text(
            f"{emoji} {rarity}:\nВыбери категорию:",
            reply_markup=get_categories_keyboard(rarity)
        )
    except:
        pass


@dp.callback_query(F.data.startswith("perk_category:"))
async def process_perk_category(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    
    parts = callback.data.split(":")
    if len(parts) == 2:
        rarity = parts[1]
        try:
            await callback.message.edit_text(
                f"{RARITY_EMOJI.get(rarity, '⚪')} {rarity}:\nВыбери категорию:",
                reply_markup=get_categories_keyboard(rarity)
            )
        except:
            pass
        return
    
    _, rarity, category_key = parts
    
    perks_data = await load_perks_data()
    perks = perks_data.get("perks", {}).get(rarity, {}).get(category_key, [])
    
    if not perks:
        return
    
    category_name = CATEGORY_NAMES.get(category_key, "")
    category_emoji = CATEGORY_EMOJI.get(category_key, "•")
    rarity_emoji = RARITY_EMOJI.get(rarity, "⚪")
    
    try:
        await callback.message.edit_text(
            f"{rarity_emoji} {rarity} • {category_emoji} {category_name}\nВыбери перк:",
            reply_markup=get_perks_list_keyboard(perks, rarity, category_key)
        )
    except:
        pass


@dp.callback_query(F.data.startswith("perk_info:"))
async def process_perk_info(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    
    _, rarity, category_key, perk_name = callback.data.split(":", 3)
    
    perks_data = await load_perks_data()
    perks = perks_data.get("perks", {}).get(rarity, {}).get(category_key, [])
    
    perk_data = None
    for perk in perks:
        if perk["name"] == perk_name:
            perk_data = perk
            break
    
    if not perk_data:
        return
    
    rarity_emoji = RARITY_EMOJI.get(rarity, "⚪")
    category_name = CATEGORY_NAMES.get(category_key, "")
    category_emoji = CATEGORY_EMOJI.get(category_key, "•")
    
    text = f"{rarity_emoji} <b>{perk_name}</b>\n"
    text += f"📊 Редкость: {rarity}\n"
    text += f"{category_emoji} Категория: {category_name}\n\n"
    text += format_perk_effects(perk_data)
    
    builder = InlineKeyboardBuilder()
    builder.button(
        text="◀️ Назад",
        callback_data=f"perk_category:{rarity}"
    )
    
    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    except:
        pass


@dp.callback_query(F.data.startswith("perk_page:"))
async def process_perk_page(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    
    _, rarity, category_key, page_str = callback.data.split(":")
    page = int(page_str)
    
    perks_data = await load_perks_data()
    perks = perks_data.get("perks", {}).get(rarity, {}).get(category_key, [])
    
    if not perks:
        return
    
    category_name = CATEGORY_NAMES.get(category_key, "")
    category_emoji = CATEGORY_EMOJI.get(category_key, "•")
    rarity_emoji = RARITY_EMOJI.get(rarity, "⚪")
    
    try:
        await callback.message.edit_text(
            f"{rarity_emoji} {rarity} • {category_emoji} {category_name}\nВыбери перк:",
            reply_markup=get_perks_list_keyboard(perks, rarity, category_key, page)
        )
    except:
        pass


@dp.callback_query(F.data == "back_to_main_perks")
async def back_to_main_perks(callback: CallbackQuery):
    await callback.answer()
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    
    try:
        await callback.message.edit_text(
            "⚡ Перки:\nВыбери редкость:",
            reply_markup=get_main_menu_perks()
        )
    except:
        pass


@dp.message(Command("offer"))
async def cmd_offer(message: Message, state: FSMContext):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    
    await state.clear()
    
    await message.answer(
        "📬 <b>Ваши идеи для бота:</b>",
        reply_markup=get_offer_main_menu()
    )
    await message.delete()


@dp.callback_query(F.data == "create_offer")
async def create_offer_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_offer")
    
    await callback.message.edit_text(
        "📝 <b>Создание заявки</b>\n\n"
        "Шаг 1/3\n"
        "Введите <b>название идеи</b>:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(OfferStates.waiting_for_name)


@dp.callback_query(F.data == "cancel_offer")
async def cancel_offer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text(
        "📬 <b>Ваши идеи для бота:</b>",
        reply_markup=get_offer_main_menu()
    )


@dp.message(OfferStates.waiting_for_name)
async def process_offer_name(message: Message, state: FSMContext):
    await state.update_data(offer_name=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_offer")
    
    await message.answer(
        "📝 <b>Создание заявки</b>\n\n"
        "Шаг 2/3\n"
        "Введите <b>описание/принцип работы</b>:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(OfferStates.waiting_for_description)
    await message.delete()


@dp.message(OfferStates.waiting_for_description)
async def process_offer_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Отмена", callback_data="cancel_offer")
    
    await message.answer(
        "📝 <b>Создание заявки</b>\n\n"
        "Шаг 3/3\n"
        "Введите <b>чем будет полезно</b>:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(OfferStates.waiting_for_benefit)
    await message.delete()


@dp.message(OfferStates.waiting_for_benefit)
async def process_offer_benefit(message: Message, state: FSMContext):
    await state.update_data(benefit=message.text)
    data = await state.get_data()
    
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Отправить", callback_data="submit_offer")
    builder.button(text="❌ Отменить", callback_data="cancel_offer")
    builder.adjust(1)
    
    text = (
        "📝 <b>Проверьте данные:</b>\n\n"
        f"1. <b>Название идеи:</b>\n{data['offer_name']}\n\n"
        f"2. <b>Описание/Принцип работы:</b>\n{data['description']}\n\n"
        f"3. <b>Чем будет полезно:</b>\n{data['benefit']}"
    )
    
    await message.answer(text, reply_markup=builder.as_markup())
    await message.delete()


@dp.callback_query(F.data == "submit_offer")
async def submit_offer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    
    offer_id = create_offer(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        offer_name=data['offer_name'],
        description=data['description'],
        benefit=data['benefit']
    )
    
    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Заявка отправлена на рассмотрение!</b>\n"
        "Ответ придет, когда ее проверят."
    )
    
    await asyncio.sleep(2)
    await callback.message.edit_text(
        "📬 <b>Ваши идеи для бота:</b>",
        reply_markup=get_offer_main_menu()
    )


@dp.callback_query(F.data == "my_offers")
async def my_offers(callback: CallbackQuery):
    await callback.answer()
    user_id = callback.from_user.id
    keyboard = get_user_offers_keyboard(user_id)
    
    offers = get_user_offers(user_id)
    if not offers:
        await callback.message.edit_text(
            "📋 <b>У тебя пока нет заявок</b>",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📋 <b>Твои заявки:</b>",
            reply_markup=keyboard
        )


@dp.callback_query(F.data.startswith("my_offers_page:"))
async def my_offers_page(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    keyboard = get_user_offers_keyboard(user_id, page)
    
    await callback.message.edit_text(
        "📋 <b>Твои заявки:</b>",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("view_my_offer:"))
async def view_my_offer(callback: CallbackQuery):
    await callback.answer()
    offer_id = int(callback.data.split(":")[1])
    offer = get_offer_by_id(offer_id)
    
    if not offer:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data="my_offers")
    
    text = format_offer_text(offer, for_admin=False)
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data == "back_to_offer_main")
async def back_to_offer_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text(
        "📬 <b>Ваши идеи для бота:</b>",
        reply_markup=get_offer_main_menu()
    )


@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав для админ-панели.")
        return
    
    await state.clear()
    
    await message.answer(
        "🔧 Админ-панель:\nВыбери действие:",
        reply_markup=get_admin_menu()
    )


@dp.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    await state.set_state(MailingStates.waiting_for_text)
    
    await callback.message.edit_text(
        "📨 Введи текст для рассылки:\n"
        "(отправь сообщение с текстом)"
    )


@dp.message(MailingStates.waiting_for_text)
async def process_mailing_text(message: Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        await state.clear()
        return
    
    if not message.text:
        await message.answer("Отправь текстовое сообщение.")
        return
    
    text = message.text
    
    status_msg = await message.answer("⏳ Начинаю рассылку...")
    
    sent, failed = await send_mailing(bot, text)
    
    await status_msg.edit_text(
        f"✅ Рассылка завершена!\n"
        f"📨 Отправлено: {sent}\n"
        f"❌ Не удалось: {failed}"
    )
    
    await state.clear()


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    
    users = get_all_users()
    chats = get_all_verified_chats()
    
    text = f"📊 Статистика:\n\n"
    text += f"👤 Пользователей: {len(users)}\n"
    text += f"💬 Чатов: {len(chats)}"
    
    await callback.message.edit_text(text, reply_markup=get_admin_menu())


@dp.callback_query(F.data == "offers_menu")
async def offers_menu(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "📬 Управление заявками:",
        reply_markup=get_offers_menu()
    )


@dp.callback_query(F.data == "offers_pending")
async def offers_pending(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    keyboard = get_offers_list_keyboard(OfferStatus.PENDING)
    
    offers = get_offers_by_status(OfferStatus.PENDING)
    if not offers:
        await callback.message.edit_text(
            "📬 Нет заявок, ожидающих рассмотрения",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📬 Заявки, ожидающие рассмотрения:",
            reply_markup=keyboard
        )


@dp.callback_query(F.data == "offers_accepted")
async def offers_accepted(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    keyboard = get_offers_list_keyboard(OfferStatus.ACCEPTED)
    
    offers = get_offers_by_status(OfferStatus.ACCEPTED)
    if not offers:
        await callback.message.edit_text(
            "📬 Нет принятых заявок",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📬 Принятые заявки:",
            reply_markup=keyboard
        )


@dp.callback_query(F.data == "offers_rejected")
async def offers_rejected(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    keyboard = get_offers_list_keyboard(OfferStatus.REJECTED)
    
    offers = get_offers_by_status(OfferStatus.REJECTED)
    if not offers:
        await callback.message.edit_text(
            "📬 Нет отклоненных заявок",
            reply_markup=keyboard
        )
    else:
        await callback.message.edit_text(
            "📬 Отклоненные заявки:",
            reply_markup=keyboard
        )


@dp.callback_query(F.data.startswith("offers_pending_page:"))
@dp.callback_query(F.data.startswith("offers_accepted_page:"))
@dp.callback_query(F.data.startswith("offers_rejected_page:"))
async def offers_page(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    parts = callback.data.split(":")
    status = parts[0].split("_")[1]
    page = int(parts[1])
    
    status_map = {
        "pending": OfferStatus.PENDING,
        "accepted": OfferStatus.ACCEPTED,
        "rejected": OfferStatus.REJECTED
    }
    
    status_text_map = {
        "pending": "ожидающих рассмотрения",
        "accepted": "принятых",
        "rejected": "отклоненных"
    }
    
    keyboard = get_offers_list_keyboard(status_map[status], page)
    await callback.message.edit_text(
        f"📬 Заявки {status_text_map[status]}:",
        reply_markup=keyboard
    )


@dp.callback_query(F.data.startswith("admin_view_offer:"))
async def admin_view_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    offer_id = int(callback.data.split(":")[1])
    offer = get_offer_by_id(offer_id)
    
    if not offer:
        await callback.answer("Заявки нема", show_alert=True)
        return
    
    text = format_offer_text(offer, for_admin=True)
    
    builder = InlineKeyboardBuilder()
    
    if offer['status'] == OfferStatus.PENDING:
        builder.button(text="✅ Принять", callback_data=f"accept_offer:{offer_id}")
        builder.button(text="❌ Отклонить", callback_data=f"reject_offer:{offer_id}")
    
    builder.button(text="◀️ Назад", callback_data=f"offers_{offer['status']}")
    builder.adjust(1)
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@dp.callback_query(F.data.startswith("accept_offer:"))
async def accept_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    offer_id = int(callback.data.split(":")[1])
    offer = get_offer_by_id(offer_id)
    
    if not offer:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    
    update_offer_status(offer_id, OfferStatus.ACCEPTED, callback.from_user.id)
    await send_offer_notification(bot, offer['user_id'], offer['offer_name'], OfferStatus.ACCEPTED)
    
    await callback.message.edit_text(
        f"✅ заявка '{offer['offer_name']}' принята!"
    )
    
    await asyncio.sleep(1)
    await callback.message.edit_text(
        "📬 Управление заявками:",
        reply_markup=get_offers_menu()
    )


@dp.callback_query(F.data.startswith("reject_offer:"))
async def reject_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    offer_id = int(callback.data.split(":")[1])
    offer = get_offer_by_id(offer_id)
    
    if not offer:
        await callback.answer("Заявки нема", show_alert=True)
        return
    
    update_offer_status(offer_id, OfferStatus.REJECTED, callback.from_user.id)
    await send_offer_notification(bot, offer['user_id'], offer['offer_name'], OfferStatus.REJECTED)
    
    await callback.message.edit_text(
        f"❌ заявка '{offer['offer_name']}' отклонена!"
    )
    
    await asyncio.sleep(1)
    await callback.message.edit_text(
        "📬 Управление заявками:",
        reply_markup=get_offers_menu()
    )


@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    
    await callback.answer()
    await callback.message.edit_text(
        "🔧 Админ-панель:\nВыбери действие:",
        reply_markup=get_admin_menu()
    )


async def main():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())