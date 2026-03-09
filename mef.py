import asyncio
import json
import sqlite3
import aiofiles
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.utils.callback_data import CallbackData
from aiogram.utils.exceptions import MessageNotModified
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command, Text

BOT_TOKEN = "8377727368:AAHUmJu_dUSJ-ZmwDWHP4mNdtvQNP39kRZM"

bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

CREATOR_ID = 7306010609

CODES_PER_PAGE = 5

# Callback data factories
page_cb = CallbackData("page", "user_id", "page_num")
family_rarity_cb = CallbackData("family_rarity", "rarity_name")
family_cb = CallbackData("family", "rarity", "family_name")
mempage_cb = CallbackData("mempage", "rarity", "page")
memory_cb = CallbackData("memory", "rarity", "memory_name")

async def load_perks():
    try:
        async with aiofiles.open('perks.json', 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    except:
        return {"perks": {}}

async def load_memories():
    try:
        async with aiofiles.open('memories.json', 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    except:
        return {}

async def load_families():
    try:
        async with aiofiles.open('families.json', 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    except:
        return {"families": {}}

async def load_config():
    try:
        async with aiofiles.open('config.json', 'r', encoding='utf-8') as f:
            return json.loads(await f.read())
    except:
        return {}

async def load_codes():
    try:
        async with aiofiles.open("codes.json", "r", encoding="utf-8") as f:
            data = json.loads(await f.read())
        codes = data.get("codes", [])
        codes.sort(key=lambda x: not x.get("active", False))
        return codes
    except:
        return []

def init_db():
    conn = sqlite3.connect('verified_mega_aotr.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verified_chats (
            chat_id INTEGER PRIMARY KEY,
            verified BOOLEAN NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            user_id INTEGER,
            session_type TEXT,
            message_id INTEGER,
            PRIMARY KEY (user_id, session_type)
        )
    ''')
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA cache_size=10000")
    conn.commit()
    conn.close()

def save_user_session(user_id, session_type, message_id):
    conn = sqlite3.connect('verified_mega_aotr.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_sessions (user_id, session_type, message_id)
        VALUES (?, ?, ?)
    ''', (user_id, session_type, message_id))
    conn.commit()
    conn.close()

def get_user_session(user_id, session_type):
    conn = sqlite3.connect('verified_mega_aotr.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT message_id FROM user_sessions 
        WHERE user_id = ? AND session_type = ?
    ''', (user_id, session_type))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def check_session_access(user_id, message_id, session_type):
    saved_message_id = get_user_session(user_id, session_type)
    return saved_message_id == message_id

def check_chat_verification(chat_id):
    if chat_id > 0:
        return True
    
    conn = sqlite3.connect('verified_mega_aotr.db')
    cursor = conn.cursor()
    cursor.execute('SELECT verified FROM verified_chats WHERE chat_id = ?', (chat_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result is not None and result[0] == 1

def format_codes_page(codes, page):
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

def get_keyboard(page, max_page, user_id):
    buttons = []
    if page > 0:
        buttons.append(types.InlineKeyboardButton(text="⬅️ Назад", callback_data=page_cb.new(user_id=user_id, page_num=page-1)))
    if page < max_page:
        buttons.append(types.InlineKeyboardButton(text="Вперёд ➡️", callback_data=page_cb.new(user_id=user_id, page_num=page+1)))
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(*buttons)
    return keyboard

EMOJI_MAP = {
    "good": "🟢",
    "bad": "🔴", 
    "skill": "🔵",
    "cooldown": "⚪",
    "neutral": "⚫"
}

RARITY_COLORS = {
    "Обычная": "⚪",
    "Редкая": "🔵", 
    "Эпическая": "🟣",
    "Легендарная": "🟡",
    "Мифическая": "🔴"
}

PERK_TYPES = {
    "Основной": "main",
    "Атакующий": "attack", 
    "Дефенс": "defense",
    "Саппорт": "support"
}

async def get_main_menu_families():
    families_data = await load_families()
    keyboard = InlineKeyboardMarkup(row_width=1)
    for rarity in families_data["families"].keys():
        if rarity == "Секретная":
            emoji_circle = "⚫"
        else:
            emoji_circle = RARITY_COLORS.get(rarity, "⚪")
        keyboard.add(InlineKeyboardButton(
            text=f"{emoji_circle} {rarity} {emoji_circle}",
            callback_data=family_rarity_cb.new(rarity_name=rarity)
        ))
    return keyboard

def get_main_menu_guide():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="💰 Фарм", callback_data="menu_farm"),
        InlineKeyboardButton(text="⭐ Престиж", callback_data="prestige"),
        InlineKeyboardButton(text="⚡ Билды", callback_data="menu_builds")
    )
    return keyboard

def get_farm_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="🪙 Золото", callback_data="farm_gold"),
        InlineKeyboardButton(text="👹 Титаны", callback_data="farm_titans"),
        InlineKeyboardButton(text="🎯 Рейды", callback_data="farm_raids"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")
    )
    return keyboard

def get_builds_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="👑 Fritz", callback_data="build_fritz"),
        InlineKeyboardButton(text="⚡ Helos", callback_data="build_helos"),
        InlineKeyboardButton(text="🗡️ Ackerman", callback_data="build_ackerman"),
        InlineKeyboardButton(text="🎭 Leonhart", callback_data="build_leonhart"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="back_main")
    )
    return keyboard

def get_fritz_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="🛡️ ОДМ", callback_data="fritz_odm"),
        InlineKeyboardButton(text="👊 Атак титан", callback_data="fritz_attack"),
        InlineKeyboardButton(text="💃 Фем титан", callback_data="fritz_female"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_builds")
    )
    return keyboard

def get_helos_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="🛡️ ОДМ", callback_data="helos_odm"),
        InlineKeyboardButton(text="⚡ Громовые Копья", callback_data="helos_spears"),
        InlineKeyboardButton(text="📈 Баффер", callback_data="helos_buffer"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_builds")
    )
    return keyboard

def get_ackerman_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="🛡️ ОДМ", callback_data="ackerman_odm"),
        InlineKeyboardButton(text="⚡ Громовые Копья", callback_data="ackerman_spears"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_builds")
    )
    return keyboard

def get_leonhart_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="💃 Фемка", callback_data="leonhart_female"),
        InlineKeyboardButton(text="◀️ Назад", callback_data="menu_builds")
    )
    return keyboard

def get_main_menu_memories():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="⭐", callback_data="mem_1"),
        InlineKeyboardButton(text="⭐⭐", callback_data="mem_2"),
        InlineKeyboardButton(text="⭐⭐⭐", callback_data="mem_3"),
        InlineKeyboardButton(text="⭐⭐⭐⭐", callback_data="mem_4")
    )
    return keyboard

def get_memories_keyboard(memories_dict, page=0, rarity=""):
    memories_list = list(memories_dict.items())
    start_idx = page * 5
    end_idx = start_idx + 5
    page_memories = memories_list[start_idx:end_idx]
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    
    for memory_name, _ in page_memories:
        keyboard.add(InlineKeyboardButton(
            text=memory_name,
            callback_data=memory_cb.new(rarity=rarity, memory_name=memory_name)
        ))
    
    navigation_buttons = []
    if page > 0:
        navigation_buttons.append(InlineKeyboardButton(
            text="⬅️", 
            callback_data=mempage_cb.new(rarity=rarity, page=page-1)
        ))
    
    navigation_buttons.append(InlineKeyboardButton(
        text="🏠", 
        callback_data="mem_home"
    ))
    
    if end_idx < len(memories_list):
        navigation_buttons.append(InlineKeyboardButton(
            text="➡️", 
            callback_data=mempage_cb.new(rarity=rarity, page=page+1)
        ))
    
    if navigation_buttons:
        keyboard.row(*navigation_buttons)
    
    return keyboard

async def find_family(family_name):
    families_data = await load_families()
    for rarity, families in families_data["families"].items():
        for family in families:
            if family["name"].lower() == family_name.lower():
                return family, rarity
    return None, None

@dp.message_handler(Command("AotrOn"))
async def cmd_verification_on(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect('verified_mega_aotr.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO verified_chats (chat_id, verified) VALUES (?, ?)', (chat_id, 1))
    conn.commit()
    conn.close()
    await message.answer("Успех.")

@dp.message_handler(Command("AotrOff"))
async def cmd_verification_off(message: types.Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        return
    
    chat_id = message.chat.id
    conn = sqlite3.connect('verified_mega_aotr.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO verified_chats (chat_id, verified) VALUES (?, ?)', (chat_id, 0))
    conn.commit()
    conn.close()
    await message.answer("Отключение...")

@dp.message_handler(Command("start_aotrcode"))
async def start_handler(message: types.Message):
    await message.answer("Бот активен все збс.")

@dp.message_handler(Command("code"))
async def code_command(message: types.Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    
    user_id = message.from_user.id
    codes = await load_codes()
    max_page = (len(codes) - 1) // CODES_PER_PAGE
    
    text = format_codes_page(codes, 0)
    keyboard = get_keyboard(0, max_page, user_id)
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await message.delete()

@dp.callback_query_handler(page_cb.filter())
async def process_callback_page(callback: types.CallbackQuery, callback_data: dict):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = int(callback_data["user_id"])
    page = int(callback_data["page_num"])
    
    if callback.from_user.id != user_id:
        return

    codes = await load_codes()
    max_page = (len(codes) - 1) // CODES_PER_PAGE

    text = format_codes_page(codes, page)
    keyboard = get_keyboard(page, max_page, user_id)

    try:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except MessageNotModified:
        pass

@dp.message_handler(Command("families"))
async def cmd_families(message: types.Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    
    keyboard = await get_main_menu_families()
    user_id = message.from_user.id
    
    if message.reply_to_message:
        msg = await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=message.reply_to_message.message_id,
            text="Фамилии:",
            reply_markup=keyboard
        )
        save_user_session(user_id, "families", msg.message_id)
    else:
        msg = await message.answer("Фамилии:", reply_markup=keyboard)
        save_user_session(user_id, "families", msg.message_id)
    
    await message.delete()

@dp.message_handler(Command("search"))
async def cmd_search(message: types.Message):
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
    
    if rarity == "Секретная":
        emoji_circle = "⚫"
    else:
        emoji_circle = RARITY_COLORS.get(rarity, "⚪")
    
    text = f"{emoji_circle} Фамилия: {family_data['name']}\n📊 Редкость: {rarity}\n\n"
    
    for buff in family_data["buffs"]:
        emoji = EMOJI_MAP.get(buff["type"], "⚫")
        if buff["description"]:
            text += f"{emoji} {buff['name']}\n   📝 {buff['description']}\n\n"
        else:
            text += f"{emoji} {buff['name']}\n\n"
    
    await message.answer(text)
    await message.delete()

@dp.callback_query_handler(family_rarity_cb.filter())
async def show_families(callback: CallbackQuery, callback_data: dict):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    
    rarity = callback_data["rarity_name"]
    families_data = await load_families()
    families = families_data["families"].get(rarity, [])
    
    keyboard = InlineKeyboardMarkup(row_width=1)
    if rarity == "Секретная":
        emoji_circle = "⚫"
    else:
        emoji_circle = RARITY_COLORS.get(rarity, "⚪")
    
    for family in families:
        keyboard.add(InlineKeyboardButton(
            text=f"{emoji_circle} {family['name']} {emoji_circle}",
            callback_data=family_cb.new(rarity=rarity, family_name=family['name'])
        ))
    
    keyboard.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data="back_to_main_families"
    ))
    
    try:
        await callback.message.edit_text(
            f"🎲 Фамилия: {rarity}\nВыбирай:",
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(family_cb.filter())
async def show_family_info(callback: CallbackQuery, callback_data: dict):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    
    rarity = callback_data["rarity"]
    family_name = callback_data["family_name"]
    
    families_data = await load_families()
    family_data = None
    for family in families_data["families"][rarity]:
        if family["name"] == family_name:
            family_data = family
            break
    
    if not family_data:
        return
    
    if rarity == "Секретная":
        emoji_circle = "⚫"
    else:
        emoji_circle = RARITY_COLORS.get(rarity, "⚪")
    
    text = f"{emoji_circle} Фамилия: {family_name}\n📊 Редкость: {rarity}\n\n"
    
    for buff in family_data["buffs"]:
        emoji = EMOJI_MAP.get(buff["type"], "⚫")
        if buff["description"]:
            text += f"{emoji} {buff['name']}\n   📝 {buff['description']}\n\n"
        else:
            text += f"{emoji} {buff['name']}\n\n"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(
        text="⬅️ Назад к фамилиям",
        callback_data=family_rarity_cb.new(rarity_name=rarity)
    ))
    
    try:
        await callback.message.edit_text(text, reply_markup=keyboard)
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="back_to_main_families"))
async def back_to_main_families(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    
    keyboard = await get_main_menu_families()
    try:
        await callback.message.edit_text("Фамилии:", reply_markup=keyboard)
    except MessageNotModified:
        pass

@dp.message_handler(Command("guide"))
async def cmd_guide(message: Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате..")
        return
    
    user_id = message.from_user.id
    
    msg = await message.answer(
        "🎮 Выбирай:",
        reply_markup=get_main_menu_guide()
    )
    
    save_user_session(user_id, "guide", msg.message_id)
    await message.delete()

@dp.callback_query_handler(Text(equals="menu_farm"))
async def menu_farm(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "💰 Фарм:",
            reply_markup=get_farm_menu()
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="menu_builds"))
async def menu_builds(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "⚡ Билды:",
            reply_markup=get_builds_menu()
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="prestige"))
async def menu_prestige(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    config_data = await load_config()
    text = config_data.get("prestige", {}).get("text", "Информация о престиже")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="back_main"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="farm_gold"))
async def farm_gold(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    config_data = await load_config()
    text = config_data.get("farm", {}).get("gold", "Информация о фарме золота")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_farm"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="farm_titans"))
async def farm_titans(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    config_data = await load_config()
    text = config_data.get("farm", {}).get("titans", "Информация о фарме титанов")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_farm"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="farm_raids"))
async def farm_raids(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    config_data = await load_config()
    text = config_data.get("farm", {}).get("raids", "Информация о рейдах")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="menu_farm"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="build_fritz"))
async def build_fritz(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "👑 Билды Fritz:",
            reply_markup=get_fritz_menu()
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="build_helos"))
async def build_helos(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "⚡ Билды Helos:",
            reply_markup=get_helos_menu()
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="build_ackerman"))
async def build_ackerman(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "🗡️ Билды Ackerman:",
            reply_markup=get_ackerman_menu()
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="build_leonhart"))
async def build_leonhart(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "🎭 Билды Leonhart:",
            reply_markup=get_leonhart_menu()
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(lambda c: c.data.startswith("fritz_"))
async def handle_fritz(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    build_type = callback.data
    config_data = await load_config()
    text = config_data.get("builds", {}).get("fritz", {}).get(build_type, "Информация о билде")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="build_fritz"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(lambda c: c.data.startswith("helos_"))
async def handle_helos(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    build_type = callback.data
    config_data = await load_config()
    text = config_data.get("builds", {}).get("helos", {}).get(build_type, "Информация о билде")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="build_helos"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(lambda c: c.data.startswith("ackerman_"))
async def handle_ackerman(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    build_type = callback.data
    config_data = await load_config()
    text = config_data.get("builds", {}).get("ackerman", {}).get(build_type, "Информация о билде")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="build_ackerman"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(lambda c: c.data.startswith("leonhart_"))
async def handle_leonhart(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    build_type = callback.data
    config_data = await load_config()
    text = config_data.get("builds", {}).get("leonhart", {}).get(build_type, "Информация о билде")
    
    if not text or text.strip() == "":
        text = "нихуя нема"
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton(text="◀️ Назад", callback_data="build_leonhart"))
    
    try:
        await callback.message.edit_text(
            text,
            reply_markup=keyboard
        )
    except MessageNotModified:
        pass

@dp.callback_query_handler(Text(equals="back_main"))
async def back_main(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "guide"):
        return
    
    try:
        await callback.message.edit_text(
            "🎮 Выбирай:",
            reply_markup=get_main_menu_guide()
        )
    except MessageNotModified:
        pass

@dp.message_handler(Command("memories"))
async def cmd_memories(message: types.Message):
    if not check_chat_verification(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    
    user_id = message.from_user.id
    
    msg = await message.answer(
        "Мемори:",
        reply_markup=get_main_menu_memories()
    )
    
    save_user_session(user_id, "memories", msg.message_id)
    await message.delete()

@dp.callback_query_handler(lambda c: c.data in ["mem_1", "mem_2", "mem_3", "mem_4"])
async def show_memories(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
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
        await callback.message.edit_text("выбери нужное мемори:", reply_markup=keyboard)
    except MessageNotModified:
        pass

@dp.callback_query_handler(mempage_cb.filter())
async def change_memory_page(callback: CallbackQuery, callback_data: dict):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "memories"):
        return
    
    try:
        rarity = callback_data["rarity"]
        page = int(callback_data["page"])
        
        memories_data = await load_memories()
        memories = memories_data.get(f"{rarity}_star", {})
        
        if not memories:
            return
        
        keyboard = get_memories_keyboard(memories, page, rarity)
        await callback.message.edit_text("выбери нужное мемори:", reply_markup=keyboard)
    except:
        return

@dp.callback_query_handler(memory_cb.filter())
async def show_memory_info(callback: CallbackQuery, callback_data: dict):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "memories"):
        return
    
    try:
        rarity = callback_data["rarity"]
        memory_name = callback_data["memory_name"]
        
        memories_data = await load_memories()
        memories = memories_data.get(f"{rarity}_star", {})
        memory_description = memories.get(memory_name)
        
        if not memory_description:
            return
        
        text = f"<b>{memory_name}</b>\n\n{memory_description}"
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(text="⬅️", callback_data=f"mem_{rarity}"))
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    except:
        return

@dp.callback_query_handler(Text(equals="mem_home"))
async def back_to_memories_main(callback: CallbackQuery):
    await callback.answer()
    
    if not check_chat_verification(callback.message.chat.id):
        return
    
    user_id = callback.from_user.id
    message_id = callback.message.message_id
    
    if not check_session_access(user_id, message_id, "memories"):
        return
    
    try:
        await callback.message.edit_text("Мемори:", reply_markup=get_main_menu_memories())
    except MessageNotModified:
        pass

async def main():
    init_db()
    await dp.start_polling()

if __name__ == "__main__":
    asyncio.run(main())