import aiofiles
import json
from typing import Dict, List, Any, Optional, Tuple
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database

router = Router()

RARITY_EMOJI = {
    "Обычная": "⚪",
    "Редкая": "🔵",
    "Эпическая": "🟣",
    "Легендарная": "🟡",
    "Мифическая": "🔴"
}

CATEGORY_EMOJI = {
    "main": "🔑",
    "attack": "🗡️",
    "defense": "🛡️",
    "support": "🎗️"
}

CATEGORY_NAMES = {
    "main": "Основные",
    "attack": "Атакующие",
    "defense": "Защитные",
    "support": "Саппорт"
}

EFFECT_EMOJI = {
    "good": "🟢",
    "bad": "🔴"
}


async def load_perks_data() -> Dict[str, Any]:
    try:
        async with aiofiles.open("config/perks.json", "r", encoding="utf-8") as f:
            return json.loads(await f.read())
    except:
        return {"perks": {}}


def get_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for rarity, emoji in RARITY_EMOJI.items():
        builder.button(text=f"{emoji} {rarity} {emoji}", callback_data=f"perk_rarity:{rarity}")
    builder.adjust(1)
    return builder.as_markup()


def get_categories_keyboard(rarity: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for key, name in CATEGORY_NAMES.items():
        emoji = CATEGORY_EMOJI.get(key, "•")
        builder.button(text=f"{emoji} {name} {emoji}", callback_data=f"perk_category:{rarity}:{key}")
    builder.button(text="◀️ Назад", callback_data="back_to_main_perks")
    builder.adjust(1)
    return builder.as_markup()


def get_perks_list_keyboard(perks: List[Dict], rarity: str, category: str, page: int = 0) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_perks = perks[start:end]
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    for perk in page_perks:
        builder.button(text=f"{emoji}{perk['name']}{emoji}", callback_data=f"perk_info:{rarity}:{category}:{perk['name']}")
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="⬅️", callback_data=f"perk_page:{rarity}:{category}:{page-1}")
    nav.button(text="🏠", callback_data=f"perk_category:{rarity}")
    if end < len(perks):
        nav.button(text="➡️", callback_data=f"perk_page:{rarity}:{category}:{page+1}")
    if nav.buttons:
        builder.attach(nav)
    builder.adjust(1)
    return builder.as_markup()


def format_perk_effects(perk: Dict) -> str:
    good = []
    bad = []
    for effect in perk.get("effects", []):
        etype = effect.get("type", "neutral")
        desc = effect.get("description", "")
        emoji = EFFECT_EMOJI.get(etype, "⚪")
        if etype == "good":
            good.append(f"{emoji} {desc}")
        else:
            bad.append(f"{emoji} {desc}")
    text = "\n\n".join(good)
    if good and bad:
        text += "\n\n"
    text += "\n\n".join(bad)
    return text.strip()


async def find_perk(perk_name: str) -> Tuple[Optional[Dict], Optional[str], Optional[str]]:
    data = await load_perks_data()
    perks = data.get("perks", {})
    for rarity, cats in perks.items():
        for key, perks_list in cats.items():
            for perk in perks_list:
                if perk["name"].lower() == perk_name.lower():
                    return perk, rarity, key
    return None, None, None


@router.message(Command("perks"))
async def cmd_perks(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    uid = message.from_user.id
    msg = await message.answer("⚡ Перки:\nВыбери редкость:", reply_markup=get_main_menu())
    database.save_session(uid, "perks", msg.message_id)
    await message.delete()


@router.message(Command("searchp"))
async def cmd_search_perk(message: Message):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    if len(message.text.split()) < 2:
        await message.answer("Правильный формат: /searchp [название перка]")
        return
    name = " ".join(message.text.split()[1:])
    perk, rarity, cat = await find_perk(name)
    if not perk:
        await message.answer(f"Перк '{name}' не найден")
        return
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    cat_name = CATEGORY_NAMES.get(cat, "")
    cat_emoji = CATEGORY_EMOJI.get(cat, "•")
    text = f"{emoji} <b>{name}</b>\n📊 Редкость: {rarity}\n{cat_emoji} Категория: {cat_name}\n\n{format_perk_effects(perk)}"
    await message.answer(text)
    await message.delete()


@router.callback_query(F.data.startswith("perk_rarity:"))
async def process_perk_rarity(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    rarity = callback.data.split(":", 1)[1]
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    try:
        await callback.message.edit_text(f"{emoji} {rarity}:\nВыбери категорию:", reply_markup=get_categories_keyboard(rarity))
    except:
        pass


@router.callback_query(F.data.startswith("perk_category:"))
async def process_perk_category(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
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
    _, rarity, cat = parts
    data = await load_perks_data()
    pk = data.get("perks", {}).get(rarity, {}).get(cat, [])
    if not pk:
        return
    cat_name = CATEGORY_NAMES.get(cat, "")
    cat_emoji = CATEGORY_EMOJI.get(cat, "•")
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    try:
        await callback.message.edit_text(
            f"{emoji} {rarity} • {cat_emoji} {cat_name}\nВыбери перк:",
            reply_markup=get_perks_list_keyboard(pk, rarity, cat)
        )
    except:
        pass


@router.callback_query(F.data.startswith("perk_info:"))
async def process_perk_info(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    _, rarity, cat, name = callback.data.split(":", 3)
    data = await load_perks_data()
    pk = data.get("perks", {}).get(rarity, {}).get(cat, [])
    perk = None
    for p in pk:
        if p["name"] == name:
            perk = p
            break
    if not perk:
        return
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    cat_name = CATEGORY_NAMES.get(cat, "")
    cat_emoji = CATEGORY_EMOJI.get(cat, "•")
    text = f"{emoji} <b>{name}</b>\n📊 Редкость: {rarity}\n{cat_emoji} Категория: {cat_name}\n\n{format_perk_effects(perk)}"
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data=f"perk_category:{rarity}")
    try:
        await callback.message.edit_text(text, reply_markup=b.as_markup())
    except:
        pass


@router.callback_query(F.data.startswith("perk_page:"))
async def process_perk_page(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    _, rarity, cat, p = callback.data.split(":")
    p = int(p)
    data = await load_perks_data()
    pk = data.get("perks", {}).get(rarity, {}).get(cat, [])
    if not pk:
        return
    cat_name = CATEGORY_NAMES.get(cat, "")
    cat_emoji = CATEGORY_EMOJI.get(cat, "•")
    emoji = RARITY_EMOJI.get(rarity, "⚪")
    try:
        await callback.message.edit_text(
            f"{emoji} {rarity} • {cat_emoji} {cat_name}\nВыбери перк:",
            reply_markup=get_perks_list_keyboard(pk, rarity, cat, p)
        )
    except:
        pass


@router.callback_query(F.data == "back_to_main_perks")
async def back_to_main_perks(callback: CallbackQuery):
    await callback.answer()
    uid, mid = callback.from_user.id, callback.message.message_id
    if not database.check_session_access(uid, mid, "perks"):
        await callback.answer("Не твои кнопки, используй /perks", show_alert=True)
        return
    try:
        await callback.message.edit_text("⚡ Перки:\nВыбери редкость:", reply_markup=get_main_menu())
    except:
        pass
