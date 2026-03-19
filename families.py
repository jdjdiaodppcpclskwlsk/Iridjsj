import json
import aiofiles
from typing import Dict, Any, Optional, Tuple
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database

router = Router()

RARITY_COLORS = {
    "Обычная": "⚪",
    "Редкая": "🔵",
    "Эпическая": "🟣",
    "Легендарная": "🟡",
    "Мифическая": "🔴",
}

EMOJI_MAP = {
    "good": "🟢",
    "bad": "🔴",
    "skill": "🔵",
    "cooldown": "⚪",
    "neutral": "⚫",
}


async def load_families() -> Dict[str, Any]:
    try:
        async with aiofiles.open("config/families.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {"families": {}}


def get_rarity_emoji(rarity: str) -> str:
    if rarity == "Секретная":
        return "⚫"
    return RARITY_COLORS.get(rarity, "⚪")


async def get_families_keyboard() -> InlineKeyboardMarkup:
    families_data = await load_families()
    builder = InlineKeyboardBuilder()
    for rarity in families_data["families"].keys():
        emoji = get_rarity_emoji(rarity)
        builder.button(text=f"{emoji} {rarity} {emoji}", callback_data=f"family_rarity:{rarity}")
    builder.adjust(1)
    return builder.as_markup()


async def find_family(family_name: str) -> Tuple[Optional[Dict], Optional[str]]:
    families_data = await load_families()
    for rarity, families in families_data["families"].items():
        for family in families:
            if family["name"].lower() == family_name.lower():
                return family, rarity
    return None, None


def format_family_text(family: Dict, rarity: str) -> str:
    emoji = get_rarity_emoji(rarity)
    text = f"{emoji} Фамилия: {family['name']}\n📊 Редкость: {rarity}\n\n"
    for buff in family["buffs"]:
        e = EMOJI_MAP.get(buff["type"], "⚫")
        if buff["description"]:
            text += f"{e} {buff['name']}\n   📝 {buff['description']}\n\n"
        else:
            text += f"{e} {buff['name']}\n\n"
    return text


@router.message(Command("families"))
async def cmd_families(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    kb = await get_families_keyboard()
    msg = await message.answer("Фамилии:", reply_markup=kb)
    database.save_session(uid, "families", msg.message_id)
    await message.delete()


@router.message(Command("search"))
async def cmd_search(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    if len(message.text.split()) < 2:
        await message.answer("Правильный формат: /search [фамилия]")
        return
    name = " ".join(message.text.split()[1:])
    fam, rarity = await find_family(name)
    if not fam:
        await message.answer(f"Фамилии '{name}' нема")
        return
    await message.answer(format_family_text(fam, rarity))
    await message.delete()


@router.callback_query(F.data.startswith("family_rarity:"))
async def show_families(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    rarity = callback.data.split(":", 1)[1]
    data = await load_families()
    fml = data["families"].get(rarity, [])
    b = InlineKeyboardBuilder()
    emoji = get_rarity_emoji(rarity)
    for f in fml:
        b.button(text=f"{emoji} {f['name']} {emoji}", callback_data=f"family:{rarity}:{f['name']}")
    b.button(text="⬅️ Назад", callback_data="back_to_main_families")
    b.adjust(1)
    try:
        await callback.message.edit_text(f"🎲 Фамилия: {rarity}\nВыбирай:", reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data.startswith("family:"))
async def show_family_info(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    _, rarity, name = callback.data.split(":", 2)
    data = await load_families()
    fam = None
    for f in data["families"][rarity]:
        if f["name"] == name:
            fam = f
            break
    if not fam:
        return
    text = format_family_text(fam, rarity)
    b = InlineKeyboardBuilder()
    b.button(text="⬅️ Назад к фамилиям", callback_data=f"family_rarity:{rarity}")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data == "back_to_main_families")
async def back_to_main_families(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "families"):
        await callback.answer("Не твои кнопки, используй /families", show_alert=True)
        return
    kb = await get_families_keyboard()
    try:
        await callback.message.edit_text("Фамилии:", reply_markup=kb)
    except:
        pass
