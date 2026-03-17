import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram import BaseMiddleware
from typing import Dict, Any, Callable, Awaitable

import database
import codes
import families
import guide
import memories
import perks
import config
from admin import MailingStates, get_admin_menu, send_mailing
from offer import (
    OfferStates, OfferStatus, init_offers_db, create_offer, get_user_offers,
    get_offers_by_status, get_offer_by_id, update_offer_status,
    get_offers_menu, get_user_offers_keyboard, get_offers_list_keyboard,
    format_offer_text, send_offer_notification, get_offer_main_menu
)
from trade import (
    TradeStates, TradeStatus, init_trades_db, create_trade, get_active_trades,
    get_user_trades, get_trade_by_id, delete_trade,
    get_trades_keyboard, get_user_trades_keyboard, get_trade_main_menu, get_trade_menu
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8377727368:AAHUmJu_dUSJ-ZmwDWHP4mNdtvQNP39kRZM"
CREATOR_ID = 7306010609

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Middleware классы
class TrackUsersMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user:
            logger.info(f"New message from user: {event.from_user.id} - {event.from_user.username}")
            database.add_user(event.from_user.id, event.from_user.first_name, event.from_user.username)
        return await handler(event, data)

class CheckVerificationMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[CallbackQuery, Dict[str, Any]], Awaitable[Any]],
        event: CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        if not database.check_chat_verified(event.message.chat.id):
            logger.warning(f"Unverified chat attempted access: {event.message.chat.id}")
            await event.answer("Чат не верифицирован", show_alert=True)
            return
        logger.info(f"Verified callback from user {event.from_user.id} in chat {event.message.chat.id}")
        return await handler(event, data)

# Регистрация middleware
dp.message.middleware(TrackUsersMiddleware())
dp.callback_query.middleware(CheckVerificationMiddleware())

def init_all_dbs():
    logger.info("Initializing all databases...")
    database.init_users_db()
    database.init_chats_db()
    database.init_sessions_db()
    init_offers_db()
    init_trades_db()
    logger.info("All databases initialized successfully")

@dp.message(Command("AotrOn"))
async def cmd_verification_on(message: Message):
    logger.info(f"Verification on command from user {message.from_user.id}")
    if message.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized verification attempt by user {message.from_user.id}")
        await message.answer("Нет прав.")
        return
    database.add_verified_chat(message.chat.id, message.chat.title or "Личный чат")
    logger.info(f"Chat {message.chat.id} verified by admin")
    await message.answer("✅ Чат верифицирован.")

@dp.message(Command("AotrOff"))
async def cmd_verification_off(message: Message):
    logger.info(f"Verification off command from user {message.from_user.id}")
    if message.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized verification removal attempt by user {message.from_user.id}")
        await message.answer("Нет прав.")
        return
    database.remove_verified_chat(message.chat.id)
    logger.info(f"Chat {message.chat.id} unverified by admin")
    await message.answer("❌ Верификация отключена.")

@dp.message(Command("start_aotrcode"))
async def start_handler(message: Message):
    logger.info(f"Start command from user {message.from_user.id}")
    await message.answer("Бот активен все збс.")

@dp.message(Command("code"))
async def code_command(message: Message):
    logger.info(f"Code command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /code")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    user_id = message.from_user.id
    cds = await codes.load_codes()
    max_page = (len(cds) - 1) // codes.CODES_PER_PAGE
    text = codes.format_codes_page(cds, 0)
    kb = codes.get_codes_keyboard(0, max_page, user_id)
    await message.answer(text, reply_markup=kb)
    await message.delete()

@dp.callback_query(F.data.startswith("page:"))
async def process_page(callback: CallbackQuery):
    logger.info(f"Page callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    _, uid, p = callback.data.split(":")
    uid, p = int(uid), int(p)
    if callback.from_user.id != uid:
        logger.warning(f"User {callback.from_user.id} tried to access another user's page")
        return
    cds = await codes.load_codes()
    max_page = (len(cds) - 1) // codes.CODES_PER_PAGE
    text = codes.format_codes_page(cds, p)
    kb = codes.get_codes_keyboard(p, max_page, uid)
    try:
        await callback.message.edit_text(text, reply_markup=kb)
        logger.info(f"Page {p} displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error editing message for page {p}: {e}")

@dp.message(Command("families"))
async def cmd_families(message: Message):
    logger.info(f"Families command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /families")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    kb = await families.get_families_keyboard()
    if message.reply_to_message:
        msg = await bot.edit_message_text(chat_id=message.chat.id, message_id=message.reply_to_message.message_id,
                                          text="Фамилии:", reply_markup=kb)
    else:
        msg = await message.answer("Фамилии:", reply_markup=kb)
    database.save_session(uid, "families", msg.message_id)
    await message.delete()
    logger.info(f"Families menu displayed for user {uid}")

@dp.message(Command("search"))
async def cmd_search(message: Message):
    logger.info(f"Search command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /search")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    if len(message.text.split()) < 2:
        logger.info(f"Invalid search format from user {message.from_user.id}")
        await message.answer("Правильный формат: /search [фамилия]")
        return
    name = " ".join(message.text.split()[1:])
    logger.info(f"Searching for family: {name}")
    fam, rarity = await families.find_family(name)
    if not fam:
        logger.info(f"Family '{name}' not found")
        await message.answer(f"Фамилии '{name}' нема")
        return
    await message.answer(families.format_family_text(fam, rarity))
    await message.delete()

@dp.callback_query(F.data.startswith("family_rarity:"))
async def show_families(callback: CallbackQuery):
    logger.info(f"Family rarity callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "families"):
        logger.warning(f"User {uid} tried to access families without session")
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    rarity = callback.data.split(":", 1)[1]
    data = await families.load_families()
    fml = data["families"].get(rarity, [])
    b = InlineKeyboardBuilder()
    emoji = families.get_rarity_emoji(rarity)
    for f in fml:
        b.button(text=f"{emoji} {f['name']} {emoji}", callback_data=f"family:{rarity}:{f['name']}")
    b.button(text="⬅️ Назад", callback_data="back_to_main_families")
    b.adjust(1)
    try:
        await callback.message.edit_text(f"🎲 Фамилия: {rarity}\nВыбирай:", reply_markup=b.as_markup())
        logger.info(f"Displayed families of rarity {rarity} for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying families: {e}")

@dp.callback_query(F.data.startswith("family:"))
async def show_family_info(callback: CallbackQuery):
    logger.info(f"Family info callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "families"):
        logger.warning(f"User {uid} tried to access family info without session")
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    _, rarity, name = callback.data.split(":", 2)
    data = await families.load_families()
    fam = None
    for f in data["families"][rarity]:
        if f["name"] == name:
            fam = f
            break
    if not fam:
        logger.error(f"Family {name} not found in rarity {rarity}")
        return
    text = families.format_family_text(fam, rarity)
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад к фамилиям", callback_data=f"family_rarity:{rarity}")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Displayed info for family {name}")
    except Exception as e:
        logger.error(f"Error displaying family info: {e}")

@dp.callback_query(F.data == "back_to_main_families")
async def back_to_main_families(callback: CallbackQuery):
    logger.info(f"Back to main families from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "families"):
        logger.warning(f"User {uid} tried to go back without session")
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    kb = await families.get_families_keyboard()
    try:
        await callback.message.edit_text("Фамилии:", reply_markup=kb)
        logger.info(f"Returned to main families menu for user {uid}")
    except Exception as e:
        logger.error(f"Error returning to main families: {e}")

@dp.message(Command("guide"))
async def cmd_guide(message: Message):
    logger.info(f"Guide command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /guide")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    msg = await message.answer("🎮 Выбирай:", reply_markup=guide.get_main_menu())
    database.save_session(uid, "guide", msg.message_id)
    await message.delete()
    logger.info(f"Guide menu displayed for user {uid}")

@dp.callback_query(F.data == "menu_farm")
async def menu_farm(callback: CallbackQuery):
    logger.info(f"Farm menu callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access farm menu without session")
        return
    try:
        await callback.message.edit_text("💰 Фарм:", reply_markup=guide.get_farm_menu())
        logger.info(f"Farm menu displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying farm menu: {e}")

@dp.callback_query(F.data == "menu_builds")
async def menu_builds(callback: CallbackQuery):
    logger.info(f"Builds menu callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access builds menu without session")
        return
    try:
        await callback.message.edit_text("⚡ Билды:", reply_markup=guide.get_builds_menu())
        logger.info(f"Builds menu displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying builds menu: {e}")

@dp.callback_query(F.data == "prestige")
async def menu_prestige(callback: CallbackQuery):
    logger.info(f"Prestige menu callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access prestige without session")
        return
    cfg = await config.load_config()
    text = cfg.get("prestige", {}).get("text", "Информация о престиже")
    if not text or text.strip() == "":
        text = "нихуя нема"
        logger.warning(f"Prestige text not found in config")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="back_main")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Prestige info displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying prestige info: {e}")

@dp.callback_query(F.data == "farm_gold")
async def farm_gold(callback: CallbackQuery):
    logger.info(f"Farm gold callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access farm gold without session")
        return
    cfg = await config.load_config()
    text = cfg.get("farm", {}).get("gold", "Информация о фарме золота")
    if not text or text.strip() == "":
        text = "нихуя нема"
        logger.warning(f"Farm gold text not found in config")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu_farm")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Farm gold info displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying farm gold: {e}")

@dp.callback_query(F.data == "farm_titans")
async def farm_titans(callback: CallbackQuery):
    logger.info(f"Farm titans callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access farm titans without session")
        return
    cfg = await config.load_config()
    text = cfg.get("farm", {}).get("titans", "Информация о фарме титанов")
    if not text or text.strip() == "":
        text = "нихуя нема"
        logger.warning(f"Farm titans text not found in config")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu_farm")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Farm titans info displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying farm titans: {e}")

@dp.callback_query(F.data == "farm_raids")
async def farm_raids(callback: CallbackQuery):
    logger.info(f"Farm raids callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access farm raids without session")
        return
    cfg = await config.load_config()
    text = cfg.get("farm", {}).get("raids", "Информация о рейдах")
    if not text or text.strip() == "":
        text = "нихуя нема"
        logger.warning(f"Farm raids text not found in config")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu_farm")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Farm raids info displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying farm raids: {e}")

@dp.callback_query(F.data == "build_fritz")
async def build_fritz(callback: CallbackQuery):
    logger.info(f"Build Fritz callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access Fritz builds without session")
        return
    try:
        await callback.message.edit_text("👑 Билды Fritz:", reply_markup=guide.get_fritz_menu())
        logger.info(f"Fritz builds menu displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying Fritz builds menu: {e}")

@dp.callback_query(F.data == "build_helos")
async def build_helos(callback: CallbackQuery):
    logger.info(f"Build Helos callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access Helos builds without session")
        return
    try:
        await callback.message.edit_text("⚡ Билды Helos:", reply_markup=guide.get_helos_menu())
        logger.info(f"Helos builds menu displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying Helos builds menu: {e}")

@dp.callback_query(F.data == "build_ackerman")
async def build_ackerman(callback: CallbackQuery):
    logger.info(f"Build Ackerman callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access Ackerman builds without session")
        return
    try:
        await callback.message.edit_text("🗡️ Билды Ackerman:", reply_markup=guide.get_ackerman_menu())
        logger.info(f"Ackerman builds menu displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying Ackerman builds menu: {e}")

@dp.callback_query(F.data == "build_leonhart")
async def build_leonhart(callback: CallbackQuery):
    logger.info(f"Build Leonhart callback from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access Leonhart builds without session")
        return
    try:
        await callback.message.edit_text("🎭 Билды Leonhart:", reply_markup=guide.get_leonhart_menu())
        logger.info(f"Leonhart builds menu displayed for user {uid}")
    except Exception as e:
        logger.error(f"Error displaying Leonhart builds menu: {e}")

@dp.callback_query(F.data.startswith(("fritz_", "helos_", "ackerman_", "leonhart_")))
async def handle_builds(callback: CallbackQuery):
    logger.info(f"Build details callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to access build details without session")
        return
    bt = callback.data
    char = bt.split("_")[0]
    cfg = await config.load_config()
    logger.info(f"Loading config for build: {bt}, character: {char}")
    text = cfg.get("builds", {}).get(char, {}).get(bt, "Информация о билде")
    if not text or text.strip() == "":
        text = "нихуя нема"
        logger.warning(f"Build text not found in config for {bt}")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=f"build_{char}")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Build details displayed for {bt}")
    except Exception as e:
        logger.error(f"Error displaying build details for {bt}: {e}")

@dp.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    logger.info(f"Back to main from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        logger.warning(f"User {uid} tried to go back without session")
        return
    try:
        await callback.message.edit_text("🎮 Выбирай:", reply_markup=guide.get_main_menu())
        logger.info(f"Returned to main menu for user {uid}")
    except Exception as e:
        logger.error(f"Error returning to main menu: {e}")

@dp.message(Command("memories"))
async def cmd_memories(message: Message):
    logger.info(f"Memories command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /memories")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    msg = await message.answer("Мемори:", reply_markup=memories.get_main_menu())
    database.save_session(uid, "memories", msg.message_id)
    await message.delete()
    logger.info(f"Memories menu displayed for user {uid}")

@dp.callback_query(F.data.in_(["mem_1", "mem_2", "mem_3", "mem_4"]))
async def show_memories(callback: CallbackQuery):
    logger.info(f"Memories rarity callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        logger.warning(f"User {uid} tried to access memories without session")
        return
    rarity = callback.data.split("_")[1]
    mems = await memories.load_memories()
    m = mems.get(f"{rarity}_star", {})
    if not m:
        logger.error(f"No memories found for rarity {rarity}")
        return
    kb = memories.get_memories_keyboard(m, 0, rarity)
    try:
        await callback.message.edit_text("выбери нужное мемори:", reply_markup=kb)
        logger.info(f"Memories list displayed for rarity {rarity}")
    except Exception as e:
        logger.error(f"Error displaying memories: {e}")

@dp.callback_query(F.data.startswith("mempage:"))
async def change_memory_page(callback: CallbackQuery):
    logger.info(f"Memory page callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        logger.warning(f"User {uid} tried to change memory page without session")
        return
    try:
        _, rarity, p = callback.data.split(":")
        p = int(p)
        mems = await memories.load_memories()
        m = mems.get(f"{rarity}_star", {})
        if not m:
            logger.error(f"No memories found for rarity {rarity}")
            return
        kb = memories.get_memories_keyboard(m, p, rarity)
        await callback.message.edit_text("выбери нужное мемори:", reply_markup=kb)
        logger.info(f"Memory page {p} displayed for rarity {rarity}")
    except Exception as e:
        logger.error(f"Error changing memory page: {e}")

@dp.callback_query(F.data.startswith("memory:"))
async def show_memory_info(callback: CallbackQuery):
    logger.info(f"Memory info callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        logger.warning(f"User {uid} tried to access memory info without session")
        return
    try:
        _, rarity, name = callback.data.split(":", 2)
        mems = await memories.load_memories()
        desc = mems.get(f"{rarity}_star", {}).get(name)
        if not desc:
            logger.error(f"Memory {name} not found in rarity {rarity}")
            return
        text = f"<b>{name}</b>\n\n{desc}"
        b = InlineKeyboardBuilder()
        b.button(text="⬅️", callback_data=f"mem_{rarity}")
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Memory info displayed for {name}")
    except Exception as e:
        logger.error(f"Error displaying memory info: {e}")

@dp.callback_query(F.data == "mem_home")
async def back_to_memories_main(callback: CallbackQuery):
    logger.info(f"Back to memories main from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "memories"):
        logger.warning(f"User {uid} tried to go back without session")
        return
    try:
        await callback.message.edit_text("Мемори:", reply_markup=memories.get_main_menu())
        logger.info(f"Returned to memories main menu for user {uid}")
    except Exception as e:
        logger.error(f"Error returning to memories main: {e}")

@dp.message(Command("perks"))
async def cmd_perks(message: Message):
    logger.info(f"Perks command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /perks")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    msg = await message.answer("⚡ Перки:\nВыбери редкость:", reply_markup=perks.get_main_menu())
    database.save_session(uid, "perks", msg.message_id)
    await message.delete()
    logger.info(f"Perks menu displayed for user {uid}")

@dp.message(Command("searchp"))
async def cmd_search_perk(message: Message):
    logger.info(f"Search perk command from user {message.from_user.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /searchp")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    if len(message.text.split()) < 2:
        logger.info(f"Invalid search perk format from user {message.from_user.id}")
        await message.answer("Правильный формат: /searchp [название перка]")
        return
    name = " ".join(message.text.split()[1:])
    logger.info(f"Searching for perk: {name}")
    perk, rarity, cat = await perks.find_perk(name)
    if not perk:
        logger.info(f"Perk '{name}' not found")
        await message.answer(f"Перк '{name}' не найден")
        return
    emoji = perks.RARITY_EMOJI.get(rarity, "⚪")
    cat_name = perks.CATEGORY_NAMES.get(cat, "")
    cat_emoji = perks.CATEGORY_EMOJI.get(cat, "•")
    text = f"{emoji} <b>{name}</b>\n📊 Редкость: {rarity}\n{cat_emoji} Категория: {cat_name}\n\n{perks.format_perk_effects(perk)}"
    await message.answer(text)
    await message.delete()

@dp.callback_query(F.data.startswith("perk_rarity:"))
async def process_perk_rarity(callback: CallbackQuery):
    logger.info(f"Perk rarity callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        logger.warning(f"User {uid} tried to access perk rarity without session")
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    rarity = callback.data.split(":", 1)[1]
    emoji = perks.RARITY_EMOJI.get(rarity, "⚪")
    try:
        await callback.message.edit_text(f"{emoji} {rarity}:\nВыбери категорию:", reply_markup=perks.get_categories_keyboard(rarity))
        logger.info(f"Perk categories displayed for rarity {rarity}")
    except Exception as e:
        logger.error(f"Error displaying perk categories: {e}")

@dp.callback_query(F.data.startswith("perk_category:"))
async def process_perk_category(callback: CallbackQuery):
    logger.info(f"Perk category callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        logger.warning(f"User {uid} tried to access perk category without session")
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    parts = callback.data.split(":")
    if len(parts) == 2:
        rarity = parts[1]
        try:
            await callback.message.edit_text(f"{perks.RARITY_EMOJI.get(rarity, '⚪')} {rarity}:\nВыбери категорию:",
                                            reply_markup=perks.get_categories_keyboard(rarity))
        except Exception as e:
            logger.error(f"Error displaying categories: {e}")
        return
    _, rarity, cat = parts
    data = await perks.load_perks_data()
    pk = data.get("perks", {}).get(rarity, {}).get(cat, [])
    if not pk:
        logger.error(f"No perks found for {rarity} - {cat}")
        return
    cat_name = perks.CATEGORY_NAMES.get(cat, "")
    cat_emoji = perks.CATEGORY_EMOJI.get(cat, "•")
    emoji = perks.RARITY_EMOJI.get(rarity, "⚪")
    try:
        await callback.message.edit_text(f"{emoji} {rarity} • {cat_emoji} {cat_name}\nВыбери перк:",
                                        reply_markup=perks.get_perks_list_keyboard(pk, rarity, cat))
        logger.info(f"Perks list displayed for {rarity} - {cat}")
    except Exception as e:
        logger.error(f"Error displaying perks list: {e}")

@dp.callback_query(F.data.startswith("perk_info:"))
async def process_perk_info(callback: CallbackQuery):
    logger.info(f"Perk info callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        logger.warning(f"User {uid} tried to access perk info without session")
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    _, rarity, cat, name = callback.data.split(":", 3)
    data = await perks.load_perks_data()
    pk = data.get("perks", {}).get(rarity, {}).get(cat, [])
    perk = None
    for p in pk:
        if p["name"] == name:
            perk = p
            break
    if not perk:
        logger.error(f"Perk {name} not found in {rarity} - {cat}")
        return
    emoji = perks.RARITY_EMOJI.get(rarity, "⚪")
    cat_name = perks.CATEGORY_NAMES.get(cat, "")
    cat_emoji = perks.CATEGORY_EMOJI.get(cat, "•")
    text = f"{emoji} <b>{name}</b>\n📊 Редкость: {rarity}\n{cat_emoji} Категория: {cat_name}\n\n{perks.format_perk_effects(perk)}"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=f"perk_category:{rarity}")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
        logger.info(f"Perk info displayed for {name}")
    except Exception as e:
        logger.error(f"Error displaying perk info: {e}")

@dp.callback_query(F.data.startswith("perk_page:"))
async def process_perk_page(callback: CallbackQuery):
    logger.info(f"Perk page callback from user {callback.from_user.id}: {callback.data}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        logger.warning(f"User {uid} tried to change perk page without session")
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    _, rarity, cat, p = callback.data.split(":")
    p = int(p)
    data = await perks.load_perks_data()
    pk = data.get("perks", {}).get(rarity, {}).get(cat, [])
    if not pk:
        logger.error(f"No perks found for {rarity} - {cat}")
        return
    cat_name = perks.CATEGORY_NAMES.get(cat, "")
    cat_emoji = perks.CATEGORY_EMOJI.get(cat, "•")
    emoji = perks.RARITY_EMOJI.get(rarity, "⚪")
    try:
        await callback.message.edit_text(f"{emoji} {rarity} • {cat_emoji} {cat_name}\nВыбери перк:",
                                        reply_markup=perks.get_perks_list_keyboard(pk, rarity, cat, p))
        logger.info(f"Perk page {p} displayed for {rarity} - {cat}")
    except Exception as e:
        logger.error(f"Error displaying perk page: {e}")

@dp.callback_query(F.data == "back_to_main_perks")
async def back_to_main_perks(callback: CallbackQuery):
    logger.info(f"Back to main perks from user {callback.from_user.id}")
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        logger.warning(f"User {uid} tried to go back without session")
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    try:
        await callback.message.edit_text("⚡ Перки:\nВыбери редкость:", reply_markup=perks.get_main_menu())
        logger.info(f"Returned to main perks menu for user {uid}")
    except Exception as e:
        logger.error(f"Error returning to main perks: {e}")

@dp.message(Command("offer"))
async def cmd_offer(message: Message, state: FSMContext):
    logger.info(f"Offer command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /offer")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    await state.clear()
    await message.answer("Ваши идеи для бота:", reply_markup=get_offer_main_menu())
    await message.delete()

@dp.callback_query(F.data == "create_offer")
async def create_offer_start(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Create offer started by user {callback.from_user.id}")
    await callback.answer()
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_offer")
    await callback.message.edit_text("Создание заявки\n\nШаг 1/3\nВведи название идеи:", reply_markup=b.as_markup())
    await state.set_state(OfferStates.waiting_for_name)

@dp.callback_query(F.data == "cancel_offer")
async def cancel_offer(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Offer creation cancelled by user {callback.from_user.id}")
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Ваши идеи для бота:", reply_markup=get_offer_main_menu())

@dp.message(OfferStates.waiting_for_name)
async def process_offer_name(message: Message, state: FSMContext):
    logger.info(f"Offer name received from user {message.from_user.id}: {message.text}")
    await state.update_data(offer_name=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_offer")
    await message.answer("Создание заявки\n\nШаг 2/3\nВведи описание/принцип работы:", reply_markup=b.as_markup())
    await state.set_state(OfferStates.waiting_for_description)
    await message.delete()

@dp.message(OfferStates.waiting_for_description)
async def process_offer_description(message: Message, state: FSMContext):
    logger.info(f"Offer description received from user {message.from_user.id}")
    await state.update_data(description=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_offer")
    await message.answer("Создание заявки\n\nШаг 3/3\nВведи чем будет полезно:", reply_markup=b.as_markup())
    await state.set_state(OfferStates.waiting_for_benefit)
    await message.delete()

@dp.message(OfferStates.waiting_for_benefit)
async def process_offer_benefit(message: Message, state: FSMContext):
    logger.info(f"Offer benefit received from user {message.from_user.id}")
    await state.update_data(benefit=message.text)
    data = await state.get_data()
    b = InlineKeyboardBuilder()
    b.button(text="Отправить", callback_data="submit_offer")
    b.button(text="Отменить", callback_data="cancel_offer")
    b.adjust(1)
    text = (f"Проверь данные:\n\n1. Название идеи:\n{data['offer_name']}\n\n"
            f"2. Описание/Принцип работы:\n{data['description']}\n\n3. Чем будет полезно:\n{data['benefit']}")
    await message.answer(text, reply_markup=b.as_markup())
    await message.delete()

@dp.callback_query(F.data == "submit_offer")
async def submit_offer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    logger.info(f"Offer submitted by user {user.id}: {data['offer_name']}")
    create_offer(user.id, user.username, user.first_name, data['offer_name'], data['description'], data['benefit'])
    await state.clear()
    await callback.message.edit_text("Заявка отправлена на рассмотрение, ответ придет когда ее проверят.")
    await asyncio.sleep(2)
    await callback.message.edit_text("Ваши идеи для бота:", reply_markup=get_offer_main_menu())

@dp.callback_query(F.data == "my_offers")
async def my_offers(callback: CallbackQuery):
    logger.info(f"My offers request from user {callback.from_user.id}")
    await callback.answer()
    uid = callback.from_user.id
    kb = get_user_offers_keyboard(uid)
    offs = get_user_offers(uid)
    if not offs:
        logger.info(f"No offers found for user {uid}")
        await callback.message.edit_text("У тебя пока нет заявок", reply_markup=kb)
    else:
        logger.info(f"Displaying {len(offs)} offers for user {uid}")
        await callback.message.edit_text("Твои заявки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("my_offers_page:"))
async def my_offers_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    logger.info(f"My offers page {page} for user {callback.from_user.id}")
    await callback.answer()
    uid = callback.from_user.id
    kb = get_user_offers_keyboard(uid, page)
    await callback.message.edit_text("Твои заявки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("view_my_offer:"))
async def view_my_offer(callback: CallbackQuery):
    oid = int(callback.data.split(":")[1])
    logger.info(f"View my offer {oid} for user {callback.from_user.id}")
    await callback.answer()
    off = get_offer_by_id(oid)
    if not off:
        logger.error(f"Offer {oid} not found")
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="Назад", callback_data="my_offers")
    await callback.message.edit_text(format_offer_text(off, False), reply_markup=b.as_markup())

@dp.callback_query(F.data == "back_to_offer_main")
async def back_to_offer_main(callback: CallbackQuery):
    logger.info(f"Back to offer main from user {callback.from_user.id}")
    await callback.answer()
    await callback.message.edit_text("Ваши идеи для бота:", reply_markup=get_offer_main_menu())

@dp.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext):
    logger.info(f"Admin command from user {message.from_user.id}")
    if message.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized admin access attempt by user {message.from_user.id}")
        await message.answer("Нет прав для админ-панели.")
        return
    await state.clear()
    await message.answer("Админ-панель:\nВыбери действие:", reply_markup=get_admin_menu())

@dp.callback_query(F.data == "admin_mailing")
async def admin_mailing(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Admin mailing started by {callback.from_user.id}")
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized mailing attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    await state.set_state(MailingStates.waiting_for_text)
    await callback.message.edit_text("Введи текст для рассылки:\n(отправь сообщение с текстом)")

@dp.message(MailingStates.waiting_for_text)
async def process_mailing_text(message: Message, state: FSMContext):
    if message.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized mailing text from {message.from_user.id}")
        await message.answer("Нет прав.")
        await state.clear()
        return
    if not message.text:
        await message.answer("Отправь текстовое сообщение.")
        return
    logger.info(f"Mailing text received from admin: {message.text[:50]}...")
    status = await message.answer("Начинаю рассылку...")
    sent, failed = await send_mailing(bot, message.text)
    logger.info(f"Mailing completed: {sent} sent, {failed} failed")
    await status.edit_text(f"Рассылка завершена!\nОтправлено: {sent}\nНе удалось: {failed}")
    await state.clear()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    logger.info(f"Admin stats requested by {callback.from_user.id}")
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized stats attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    users = database.get_all_users()
    chats = database.get_all_verified_chats()
    text = f"Статистика:\n\nПользователей: {len(users)}\nЧатов: {len(chats)}"
    logger.info(f"Stats: {len(users)} users, {len(chats)} chats")
    await callback.message.edit_text(text, reply_markup=get_admin_menu())

@dp.callback_query(F.data == "offers_menu")
async def offers_menu(callback: CallbackQuery):
    logger.info(f"Offers menu requested by {callback.from_user.id}")
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized offers menu attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text("Управление заявками:", reply_markup=get_offers_menu())

@dp.callback_query(F.data == "offers_pending")
async def offers_pending(callback: CallbackQuery):
    logger.info(f"Pending offers requested by {callback.from_user.id}")
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized pending offers attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    kb = get_offers_list_keyboard(OfferStatus.PENDING)
    offs = get_offers_by_status(OfferStatus.PENDING)
    if not offs:
        logger.info("No pending offers")
        await callback.message.edit_text("Нет заявок, ожидающих рассмотрения", reply_markup=kb)
    else:
        logger.info(f"Displaying {len(offs)} pending offers")
        await callback.message.edit_text("Заявки, ожидающие рассмотрения:", reply_markup=kb)

@dp.callback_query(F.data == "offers_accepted")
async def offers_accepted(callback: CallbackQuery):
    logger.info(f"Accepted offers requested by {callback.from_user.id}")
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized accepted offers attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    kb = get_offers_list_keyboard(OfferStatus.ACCEPTED)
    offs = get_offers_by_status(OfferStatus.ACCEPTED)
    if not offs:
        logger.info("No accepted offers")
        await callback.message.edit_text("Нет принятых заявок", reply_markup=kb)
    else:
        logger.info(f"Displaying {len(offs)} accepted offers")
        await callback.message.edit_text("Принятые заявки:", reply_markup=kb)

@dp.callback_query(F.data == "offers_rejected")
async def offers_rejected(callback: CallbackQuery):
    logger.info(f"Rejected offers requested by {callback.from_user.id}")
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized rejected offers attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    kb = get_offers_list_keyboard(OfferStatus.REJECTED)
    offs = get_offers_by_status(OfferStatus.REJECTED)
    if not offs:
        logger.info("No rejected offers")
        await callback.message.edit_text("Нет отклоненных заявок", reply_markup=kb)
    else:
        logger.info(f"Displaying {len(offs)} rejected offers")
        await callback.message.edit_text("Отклоненные заявки:", reply_markup=kb)

@dp.callback_query(F.data.startswith("offers_pending_page:"))
@dp.callback_query(F.data.startswith("offers_accepted_page:"))
@dp.callback_query(F.data.startswith("offers_rejected_page:"))
async def offers_page(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized offers page attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    parts = callback.data.split(":")
    status = parts[0].split("_")[1]
    page = int(parts[1])
    logger.info(f"Offers page {page} for status {status} requested by admin")
    stat_map = {"pending": OfferStatus.PENDING, "accepted": OfferStatus.ACCEPTED, "rejected": OfferStatus.REJECTED}
    text_map = {"pending": "ожидающих рассмотрения", "accepted": "принятых", "rejected": "отклоненных"}
    kb = get_offers_list_keyboard(stat_map[status], page)
    await callback.message.edit_text(f"Заявки {text_map[status]}:", reply_markup=kb)

@dp.callback_query(F.data.startswith("admin_view_offer:"))
async def admin_view_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized admin view offer attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    logger.info(f"Admin viewing offer {oid}")
    off = get_offer_by_id(oid)
    if not off:
        logger.error(f"Offer {oid} not found")
        await callback.answer("Заявки нема", show_alert=True)
        return
    text = format_offer_text(off, True)
    b = InlineKeyboardBuilder()
    if off['status'] == OfferStatus.PENDING:
        b.button(text="Принять", callback_data=f"accept_offer:{oid}")
        b.button(text="Отклонить", callback_data=f"reject_offer:{oid}")
    b.button(text="Назад", callback_data=f"offers_{off['status']}")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("accept_offer:"))
async def accept_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized accept offer attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    logger.info(f"Admin accepting offer {oid}")
    off = get_offer_by_id(oid)
    if not off:
        logger.error(f"Offer {oid} not found")
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    update_offer_status(oid, OfferStatus.ACCEPTED, callback.from_user.id)
    await send_offer_notification(bot, off['user_id'], off['offer_name'], OfferStatus.ACCEPTED)
    await callback.message.edit_text(f"заявка '{off['offer_name']}' принята!")
    await asyncio.sleep(1)
    await callback.message.edit_text("Управление заявками:", reply_markup=get_offers_menu())

@dp.callback_query(F.data.startswith("reject_offer:"))
async def reject_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized reject offer attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    logger.info(f"Admin rejecting offer {oid}")
    off = get_offer_by_id(oid)
    if not off:
        logger.error(f"Offer {oid} not found")
        await callback.answer("Заявки нема", show_alert=True)
        return
    update_offer_status(oid, OfferStatus.REJECTED, callback.from_user.id)
    await send_offer_notification(bot, off['user_id'], off['offer_name'], OfferStatus.REJECTED)
    await callback.message.edit_text(f"заявка '{off['offer_name']}' отклонена!")
    await asyncio.sleep(1)
    await callback.message.edit_text("Управление заявками:", reply_markup=get_offers_menu())

@dp.callback_query(F.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        logger.warning(f"Unauthorized back to admin attempt by {callback.from_user.id}")
        await callback.answer("Нет прав.", show_alert=True)
        return
    logger.info(f"Admin returning to main menu")
    await callback.answer()
    await callback.message.edit_text("Админ-панель:\nВыбери действие:", reply_markup=get_admin_menu())

@dp.message(Command("trade"))
async def cmd_trade(message: Message, state: FSMContext):
    logger.info(f"Trade command from user {message.from_user.id} in chat {message.chat.id}")
    if not database.check_chat_verified(message.chat.id):
        logger.warning(f"Unverified chat {message.chat.id} attempted to use /trade")
        await message.answer("Бот не верифицирован в этом чате.")
        return
    await state.clear()
    await message.answer("Торговая площадка:", reply_markup=get_trade_main_menu())
    await message.delete()

@dp.callback_query(F.data == "trade_menu")
async def trade_menu(callback: CallbackQuery):
    logger.info(f"Trade menu from user {callback.from_user.id}")
    await callback.answer()
    await callback.message.edit_text("Трейд:", reply_markup=get_trade_menu())

@dp.callback_query(F.data == "back_to_trade_main")
async def back_to_trade_main(callback: CallbackQuery):
    logger.info(f"Back to trade main from user {callback.from_user.id}")
    await callback.answer()
    await callback.message.edit_text("Торговая площадка:", reply_markup=get_trade_main_menu())

@dp.callback_query(F.data == "trade_platform")
async def trade_platform(callback: CallbackQuery):
    logger.info(f"Trade platform requested by user {callback.from_user.id}")
    await callback.answer()
    kb = get_trades_keyboard(0)
    tr = get_active_trades()
    if not tr:
        logger.info("No active trades")
        await callback.message.edit_text("Нет предложений", reply_markup=kb)
    else:
        logger.info(f"Displaying {len(tr)} active trades")
        await callback.message.edit_text("Все предложения:", reply_markup=kb)

@dp.callback_query(F.data.startswith("trades_page:"))
async def trades_page(callback: CallbackQuery):
    page = int(callback.data.split(":")[1])
    logger.info(f"Trades page {page} requested by user {callback.from_user.id}")
    await callback.answer()
    await callback.message.edit_text("Все предложения:", reply_markup=get_trades_keyboard(page))

@dp.callback_query(F.data.startswith("view_trade:"))
async def view_trade(callback: CallbackQuery):
    tid = int(callback.data.split(":")[1])
    logger.info(f"View trade {tid} requested by user {callback.from_user.id}")
    await callback.answer()
    tr = get_trade_by_id(tid)
    if not tr:
        logger.error(f"Trade {tid} not found")
        await callback.answer("Предложение нема", show_alert=True)
        return
    text = (f"Ник: {tr['first_name']}\nЮзер: @{tr['username'] if tr['username'] else 'нет'}\n"
            f"Айди: {tr['user_id']}\n\nТрейдит:\n{tr['offer']}\n\nИщет:\n{tr['want']}")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="trade_platform")
    await callback.message.edit_text(text, reply_markup=b.as_markup())

@dp.callback_query(F.data == "create_trade")
async def create_trade_start(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Create trade started by user {callback.from_user.id}")
    await callback.answer()
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_trade")
    await callback.message.edit_text("Создание предложения\n\nШаг 1/3\nВведи название предложения:", reply_markup=b.as_markup())
    await state.set_state(TradeStates.WAITING_TITLE)

@dp.callback_query(F.data == "cancel_trade")
async def cancel_trade(callback: CallbackQuery, state: FSMContext):
    logger.info(f"Trade creation cancelled by user {callback.from_user.id}")
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Трейд:", reply_markup=get_trade_menu())

@dp.message(TradeStates.WAITING_TITLE)
async def process_trade_title(message: Message, state: FSMContext):
    logger.info(f"Trade title received from user {message.from_user.id}: {message.text}")
    await state.update_data(title=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_trade")
    await message.answer("Создание предложения\n\nШаг 2/3\nВведи что трейдишь:", reply_markup=b.as_markup())
    await state.set_state(TradeStates.WAITING_OFFER)
    await message.delete()

@dp.message(TradeStates.WAITING_OFFER)
async def process_trade_offer(message: Message, state: FSMContext):
    logger.info(f"Trade offer received from user {message.from_user.id}")
    await state.update_data(offer=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_trade")
    await message.answer("Создание предложения\n\nШаг 3/3\nВведи что хочешь получить взамен:", reply_markup=b.as_markup())
    await state.set_state(TradeStates.WAITING_WANT)
    await message.delete()

@dp.message(TradeStates.WAITING_WANT)
async def process_trade_want(message: Message, state: FSMContext):
    logger.info(f"Trade want received from user {message.from_user.id}")
    await state.update_data(want=message.text)
    data = await state.get_data()
    b = InlineKeyboardBuilder()
    b.button(text="Подтвердить", callback_data="submit_trade")
    b.button(text="Отменить", callback_data="cancel_trade")
    b.adjust(1)
    text = f"Название: {data['title']}\n\nТрейдит:\n{data['offer']}\n\nИщет:\n{data['want']}"
    await message.answer(text, reply_markup=b.as_markup())
    await message.delete()

@dp.callback_query(F.data == "submit_trade")
async def submit_trade(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    logger.info(f"Trade submitted by user {user.id}: {data['title']}")
    create_trade(user.id, user.username, user.first_name, data['title'], data['offer'], data['want'])
    await state.clear()
    await callback.message.edit_text("Предложение сделано")
    await asyncio.sleep(1)
    await callback.message.edit_text("Трейд:", reply_markup=get_trade_menu())

@dp.callback_query(F.data == "my_trades")
async def my_trades(callback: CallbackQuery):
    logger.info(f"My trades requested by user {callback.from_user.id}")
    await callback.answer()
    uid = callback.from_user.id
    kb = get_user_trades_keyboard(uid)
    tr = get_user_trades(uid)
    if not tr:
        logger.info(f"No trades found for user {uid}")
        await callback.message.edit_text("У тебя нет предложений", reply_markup=kb)
    else:
        logger.info(f"Displaying {len(tr)} trades for user {uid}")
        await callback.message.edit_text("Твои предложения:", reply_markup=kb)

@dp.callback_query(F.data.startswith("my_trade:"))
async def my_trade_detail(callback: CallbackQuery):
    tid = int(callback.data.split(":")[1])
    logger.info(f"My trade detail {tid} requested by user {callback.from_user.id}")
    await callback.answer()
    tr = get_trade_by_id(tid)
    if not tr:
        logger.error(f"Trade {tid} not found")
        await callback.answer("Предложение нема", show_alert=True)
        return
    text = f"Название: {tr['title']}\n\nТрейдит:\n{tr['offer']}\n\nИщет:\n{tr['want']}"
    b = InlineKeyboardBuilder()
    b.button(text="Удалить предложение", callback_data=f"delete_trade:{tid}")
    b.button(text="◀️ Назад", callback_data="my_trades")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())

@dp.callback_query(F.data.startswith("delete_trade:"))
async def delete_trade_handler(callback: CallbackQuery):
    tid = int(callback.data.split(":")[1])
    logger.info(f"Delete trade {tid} requested by user {callback.from_user.id}")
    await callback.answer()
    tr = get_trade_by_id(tid)
    if not tr:
        logger.error(f"Trade {tid} not found")
        await callback.answer("Предложение нема", show_alert=True)
        return
    if tr['user_id'] != callback.from_user.id and callback.from_user.id != CREATOR_ID:
        logger.warning(f"User {callback.from_user.id} tried to delete trade {tid} belonging to {tr['user_id']}")
        await callback.answer("Это не твое предложение", show_alert=True)
        return
    delete_trade(tid)
    logger.info(f"Trade {tid} deleted by user {callback.from_user.id}")
    await callback.message.edit_text("Предложение удалено")
    await asyncio.sleep(1)
    await callback.message.edit_text("Твои предложения:", reply_markup=get_user_trades_keyboard(callback.from_user.id))

async def main():
    logger.info("Starting bot...")
    init_all_dbs()
    logger.info("Bot started successfully")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())