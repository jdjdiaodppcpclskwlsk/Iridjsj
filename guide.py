from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database
import config

router = Router()


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


@router.message(Command("guide"))
async def cmd_guide(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    msg = await message.answer("🎮 Выбирай:", reply_markup=get_main_menu())
    database.save_session(uid, "guide", msg.message_id)
    await message.delete()


@router.callback_query(F.data == "menu_farm")
async def menu_farm(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("💰 Фарм:", reply_markup=get_farm_menu())
    except:
        pass


@router.callback_query(F.data == "menu_builds")
async def menu_builds(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("⚡ Билды:", reply_markup=get_builds_menu())
    except:
        pass


@router.callback_query(F.data == "prestige")
async def menu_prestige(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    cfg = await config.load_config()
    text = cfg.get("prestige", {}).get("text", "Информация о престиже")
    if not text or text.strip() == "":
        text = "нихуя нема"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="back_main")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data == "farm_gold")
async def farm_gold(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    cfg = await config.load_config()
    text = cfg.get("farm", {}).get("gold", "Информация о фарме золота")
    if not text or text.strip() == "":
        text = "нихуя нема"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu_farm")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data == "farm_titans")
async def farm_titans(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    cfg = await config.load_config()
    text = cfg.get("farm", {}).get("titans", "Информация о фарме титанов")
    if not text or text.strip() == "":
        text = "нихуя нема"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu_farm")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data == "farm_raids")
async def farm_raids(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    cfg = await config.load_config()
    text = cfg.get("farm", {}).get("raids", "Информация о рейдах")
    if not text or text.strip() == "":
        text = "нихуя нема"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="menu_farm")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data == "build_fritz")
async def build_fritz(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("👑 Билды Fritz:", reply_markup=get_fritz_menu())
    except:
        pass


@router.callback_query(F.data == "build_helos")
async def build_helos(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("⚡ Билды Helos:", reply_markup=get_helos_menu())
    except:
        pass


@router.callback_query(F.data == "build_ackerman")
async def build_ackerman(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("🗡️ Билды Ackerman:", reply_markup=get_ackerman_menu())
    except:
        pass


@router.callback_query(F.data == "build_leonhart")
async def build_leonhart(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("🎭 Билды Leonhart:", reply_markup=get_leonhart_menu())
    except:
        pass


@router.callback_query(F.data.startswith(("fritz_", "helos_", "ackerman_", "leonhart_")))
async def handle_builds(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    bt = callback.data
    char = bt.split("_")[0]
    cfg = await config.load_config()
    text = cfg.get("builds", {}).get(char, {}).get(bt, "Информация о билде")
    if not text or text.strip() == "":
        text = "нихуя нема"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=f"build_{char}")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data == "back_main")
async def back_main(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "guide"):
        return
    try:
        await callback.message.edit_text("🎮 Выбирай:", reply_markup=get_main_menu())
    except:
        pass
