"""
game.py — вся игровая логика для AOTR бота.
mef.py только регистрирует роутер dp.include_router(game_router).
"""

import asyncio
import json
import random
import os
from typing import Optional

from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

import game_database as gdb

game_router = Router()

# ── REPLICS ────────────────────────────────────────────────────────────────────
_replics_path = os.path.join(os.path.dirname(__file__), "config", "battle_replics.json")
with open(_replics_path, encoding="utf-8") as _f:
    REPLICS = json.load(_f)

def rnd(lst): return random.choice(lst)

# ── FSM STATES ─────────────────────────────────────────────────────────────────
class GameStates(StatesGroup):
    choosing_titan      = State()
    in_game             = State()
    upgrading_stat      = State()
    upgrading_confirm   = State()
    outside_wall        = State()
    battle_pve          = State()
    combo_input         = State()
    duel_battle         = State()

# ── SKILL LABELS ───────────────────────────────────────────────────────────────
SKILL_NAMES = {
    "punch":        "Удар",
    "uppercut":     "Апперкот",
    "dodge":        "Уклонение",
    "kick":         "Удар ногой",
    "side_strike":  "Боковой удар",
    "suplex":       "Бросок на прогиб",
    "choke":        "Удушение",
    "titan_scream": "Крик титана",
}
SKILL_TO_KEY = {v: k for k, v in SKILL_NAMES.items()}

RANK_EMOJI = {"E": "🔵", "D": "🟢", "C": "🟡", "B": "🟠", "A": "🔴", "S": "💜"}

TITAN_INFO = {
    "attacking": {
        "name": "Атакующий титан",
        "emoji": "⚔️",
        "desc": (
            "Атакующий титан — самое универсальное и смертоносное оружие. "
            "Скорость и сила — его главные козыри. Идеален для агрессивного стиля боя."
        ),
        "stats": {"hp": 100, "defense": 20, "strength": 50, "agility": 15},
    },
    "armored": {
        "name": "Бронированный титан",
        "emoji": "🛡️",
        "desc": (
            "Бронированный титан покрыт непробиваемой бронёй. "
            "Медленный, но невероятно прочный — способен выдержать любую атаку."
        ),
        "stats": {"hp": 150, "defense": 50, "strength": 30, "agility": 5},
    },
}

# ══════════════════════════════════════════════════════════════════════════════
#  /game — ВЫБОР ТИТАНА
# ══════════════════════════════════════════════════════════════════════════════
@game_router.message(Command("game"))
async def cmd_game(message: Message, state: FSMContext):
    user_id = message.from_user.id
    player  = gdb.get_player(user_id)

    if player:
        await state.set_state(GameStates.in_game)
        await message.answer("🗺️ <b>Навигация:</b>", reply_markup=_nav_kb())
        try:
            await message.delete()
        except:
            pass
        return

    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ Атакующий титан",   callback_data="titan_info:attacking")
    kb.button(text="🛡️ Бронированный титан", callback_data="titan_info:armored")
    kb.adjust(1)
    await state.set_state(GameStates.choosing_titan)
    msg = await message.answer("🔮 <b>Выбери своего титана:</b>", reply_markup=kb.as_markup())
    try:
        await message.delete()
    except:
        pass

# ── Инфо о титане ──────────────────────────────────────────────────────────────
@game_router.callback_query(F.data.startswith("titan_info:"))
async def titan_info(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    titan_key = cb.data.split(":")[1]
    info  = TITAN_INFO[titan_key]
    stats = info["stats"]

    text = (
        f"{info['emoji']} <b>{info['name']}</b> — {info['desc']}\n\n"
        f"<b>Начальные статистики:</b>\n"
        f"❤️ Здоровье: <b>{stats['hp']}</b>\n"
        f"🛡️ Защита:   <b>{stats['defense']}</b>\n"
        f"⚔️ Сила:     <b>{stats['strength']}</b>\n"
        f"💨 Ловкость: <b>{stats['agility']}</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Выбрать",  callback_data=f"titan_choose:{titan_key}")
    kb.button(text="⬅️ Назад",   callback_data="titan_back")
    kb.adjust(1)
    try:
        await cb.message.edit_text(text, reply_markup=kb.as_markup())
    except:
        pass

@game_router.callback_query(F.data == "titan_back")
async def titan_back(cb: CallbackQuery):
    await cb.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="⚔️ Атакующий титан",    callback_data="titan_info:attacking")
    kb.button(text="🛡️ Бронированный титан", callback_data="titan_info:armored")
    kb.adjust(1)
    try:
        await cb.message.edit_text("🔮 <b>Выбери своего титана:</b>", reply_markup=kb.as_markup())
    except:
        pass

@game_router.callback_query(F.data.startswith("titan_choose:"))
async def titan_choose(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    titan_key = cb.data.split(":")[1]
    user = cb.from_user
    gdb.create_player(user.id, user.username or "", user.first_name, titan_key)
    await state.set_state(GameStates.in_game)
    info = TITAN_INFO[titan_key]
    try:
        await cb.message.edit_text(
            f"✅ Ты выбрал <b>{info['name']}</b>! Добро пожаловать за стену, солдат.\n\n"
            f"🗺️ <b>Навигация:</b>",
            reply_markup=_nav_kb()
        )
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  NAV MENU
# ══════════════════════════════════════════════════════════════════════════════
def _nav_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="👤 Мой титан",       callback_data="g_profile")
    kb.button(text="📋 Задания",          callback_data="g_quests")
    kb.button(text="⬆️ Прокачка",         callback_data="g_upgrade")
    kb.button(text="🎓 Навыки",           callback_data="g_skills")
    kb.button(text="🏔️ Вылазка за стену", callback_data="g_expedition")
    kb.adjust(1)
    return kb.as_markup()

@game_router.callback_query(F.data == "g_nav")
async def g_nav(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(GameStates.in_game)
    try:
        await cb.message.edit_text("🗺️ <b>Навигация:</b>", reply_markup=_nav_kb())
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  МОЙ ТИТАН (профиль)
# ══════════════════════════════════════════════════════════════════════════════
@game_router.callback_query(F.data == "g_profile")
async def g_profile(cb: CallbackQuery):
    await cb.answer()
    p = gdb.get_player(cb.from_user.id)
    if not p:
        await cb.answer("Сначала создай персонажа через /game", show_alert=True)
        return

    titan_name = TITAN_INFO[p["titan_type"]]["name"]
    titan_emoji = TITAN_INFO[p["titan_type"]]["emoji"]
    exp_need   = gdb.exp_for_level(p["level"])
    uname      = f"@{cb.from_user.username}" if cb.from_user.username else "—"

    text = (
        f"👤 <b>Профиль</b>\n\n"
        f"📛 Ник:  <b>{cb.from_user.first_name}</b>\n"
        f"🏷️ Юз:  <b>{uname}</b>\n"
        f"🆔 Айди: <code>{cb.from_user.id}</code>\n"
        f"{titan_emoji} Титан: <b>{titan_name}</b>\n\n"
        f"<b>Характеристики:</b>\n"
        f"❤️ HP:       <b>{p['hp']}/{p['max_hp']}</b>\n"
        f"🛡️ Защита:  <b>{p['defense']}</b>\n"
        f"⚔️ Сила:    <b>{p['strength']}</b>\n"
        f"💨 Ловкость:<b>{p['agility']}</b>\n\n"
        f"⭐ Уровень: <b>{p['level']}</b>\n"
        f"🔮 Опыт:    <b>{p['exp']}/{exp_need}</b>\n"
        f"💀 Убийств: <b>{p['kills']}</b>"
    )

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="g_nav")
    try:
        await cb.message.edit_text(text, reply_markup=kb.as_markup())
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  ЗАДАНИЯ (заглушка)
# ══════════════════════════════════════════════════════════════════════════════
@game_router.callback_query(F.data == "g_quests")
async def g_quests(cb: CallbackQuery):
    await cb.answer()
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="g_nav")
    try:
        await cb.message.edit_text(
            "📋 <b>Задания</b>\n\n🔧 Раздел заданий ещё в разработке.\nСледи за обновлениями!",
            reply_markup=kb.as_markup()
        )
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  ПРОКАЧКА
# ══════════════════════════════════════════════════════════════════════════════
@game_router.callback_query(F.data == "g_upgrade")
async def g_upgrade(cb: CallbackQuery):
    await cb.answer()
    p = gdb.get_player(cb.from_user.id)
    if not p:
        await cb.answer("Создай персонажа через /game", show_alert=True)
        return

    kb = InlineKeyboardBuilder()
    for stat in ["Здоровье", "Защита", "Сила", "Ловкость"]:
        kb.button(text=stat, callback_data=f"g_upg_stat:{stat}")
    kb.button(text="⬅️ Назад", callback_data="g_nav")
    kb.adjust(2, 2, 1)

    try:
        await cb.message.edit_text(
            f"⬆️ <b>Прокачка</b>\n\nУ тебя <b>{p['upgrade_points']}</b> очков прокачки.\n\nВыбери что прокачать:",
            reply_markup=kb.as_markup()
        )
    except:
        pass

@game_router.callback_query(F.data.startswith("g_upg_stat:"))
async def g_upg_stat(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    stat = cb.data.split(":")[1]
    p    = gdb.get_player(cb.from_user.id)
    if not p or p["upgrade_points"] < 1:
        await cb.answer("Нет очков прокачки!", show_alert=True)
        return

    await state.set_state(GameStates.upgrading_stat)
    await state.update_data(upg_stat=stat, upg_msg_id=cb.message.message_id)

    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="g_upgrade")
    try:
        await cb.message.edit_text(
            f"⬆️ <b>Прокачка: {stat}</b>\n\n"
            f"У тебя <b>{p['upgrade_points']}</b> очков.\n\n"
            f"Сколько очков вложить? (напиши число от 1 до {p['upgrade_points']})",
            reply_markup=kb.as_markup()
        )
    except:
        pass

@game_router.message(GameStates.upgrading_stat)
async def g_upg_amount(message: Message, state: FSMContext):
    data   = await state.get_data()
    stat   = data.get("upg_stat")
    try:
        pts = int(message.text.strip())
        assert pts >= 1
    except:
        await message.answer("Введи корректное число!", reply_markup=_back_upg_kb())
        try:
            await message.delete()
        except:
            pass
        return

    p = gdb.get_player(message.from_user.id)
    if not p or pts > p["upgrade_points"]:
        await message.answer("Недостаточно очков!", reply_markup=_back_upg_kb())
        try:
            await message.delete()
        except:
            pass
        return

    mult = gdb.TITAN_UPGRADE_PER_POINT[p["titan_type"]]
    col_map = {"Здоровье": "max_hp", "Защита": "defense", "Сила": "strength", "Ловкость": "agility"}
    col     = col_map[stat]
    hp_key  = col.replace("max_hp", "hp")
    gain    = mult[hp_key] * pts
    old_val = p[col]
    new_val = old_val + gain

    await state.set_state(GameStates.upgrading_confirm)
    await state.update_data(upg_pts=pts, upg_gain=gain, upg_new_val=new_val, upg_old_val=old_val)

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить", callback_data="g_upg_confirm")
    kb.button(text="⬅️ Назад",      callback_data="g_upgrade")
    kb.adjust(1)

    try:
        await message.answer(
            f"⬆️ <b>Подтверждение прокачки</b>\n\n"
            f"📊 {stat}: <b>{old_val}</b> ➡️ <b>{new_val}</b>\n"
            f"💡 Потратишь: <b>{pts}</b> очков\n"
            f"✨ Прирост: <b>+{gain}</b>",
            reply_markup=kb.as_markup()
        )
    except:
        pass
    try:
        await message.delete()
    except:
        pass

def _back_upg_kb():
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="g_upgrade")
    return kb.as_markup()

@game_router.callback_query(F.data == "g_upg_confirm", GameStates.upgrading_confirm)
async def g_upg_confirm(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data = await state.get_data()
    res  = gdb.spend_upgrade_points(cb.from_user.id, data["upg_stat"], data["upg_pts"])

    if not res.get("ok"):
        await cb.answer("Ошибка прокачки", show_alert=True)
        return

    await state.set_state(GameStates.in_game)
    p = gdb.get_player(cb.from_user.id)

    kb = InlineKeyboardBuilder()
    kb.button(text="⬆️ Ещё прокачать", callback_data="g_upgrade")
    kb.button(text="🗺️ Навигация",      callback_data="g_nav")
    kb.adjust(1)

    try:
        await cb.message.edit_text(
            f"✅ <b>Прокачка выполнена!</b>\n\n"
            f"📊 {data['upg_stat']}: <b>{res['old_val']}</b> ➡️ <b>{res['new_val']}</b>\n"
            f"💎 Осталось очков: <b>{res['new_pts']}</b>",
            reply_markup=kb.as_markup()
        )
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  НАВЫКИ
# ══════════════════════════════════════════════════════════════════════════════
@game_router.callback_query(F.data == "g_skills")
async def g_skills(cb: CallbackQuery):
    await cb.answer()
    p = gdb.get_player(cb.from_user.id)
    if not p:
        await cb.answer("Создай персонажа через /game", show_alert=True)
        return

    unlocked = gdb.get_unlocked_skills(p)
    kb       = InlineKeyboardBuilder()

    for key in gdb.ALL_SKILLS:
        name  = SKILL_NAMES[key]
        check = "✅" if key in unlocked else "❌"
        req   = gdb.SKILL_UNLOCK_LEVELS.get(key)
        label = f"{check} {name}" + (f" (🔒{req} лвл)" if key not in unlocked and req else "")
        kb.button(text=label, callback_data=f"g_skill_info:{key}")

    kb.button(text="⬅️ Назад", callback_data="g_nav")
    kb.adjust(1)

    try:
        await cb.message.edit_text(
            f"🎓 <b>Твои навыки</b> (уровень {p['level']}):",
            reply_markup=kb.as_markup()
        )
    except:
        pass

@game_router.callback_query(F.data.startswith("g_skill_info:"))
async def g_skill_info(cb: CallbackQuery):
    await cb.answer()
    key  = cb.data.split(":")[1]
    name = SKILL_NAMES.get(key, key)
    p    = gdb.get_player(cb.from_user.id)
    unlocked = gdb.get_unlocked_skills(p)
    req  = gdb.SKILL_UNLOCK_LEVELS.get(key)
    status = "✅ Разблокирован" if key in unlocked else f"❌ Разблокируется на {req} уровне"
    phrases = REPLICS["attack_phrases"].get(key, [])
    example = rnd(phrases) if phrases else "—"
    text = (
        f"🎓 <b>{name}</b>\n\n"
        f"Статус: {status}\n\n"
        f"Пример: <i>{example}</i>"
    )
    kb = InlineKeyboardBuilder()
    kb.button(text="⬅️ Назад", callback_data="g_skills")
    try:
        await cb.message.edit_text(text, reply_markup=kb.as_markup())
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  ВЫЛАЗКА ЗА СТЕНУ
# ══════════════════════════════════════════════════════════════════════════════
@game_router.callback_query(F.data == "g_expedition")
async def g_expedition(cb: CallbackQuery):
    await cb.answer()
    kb = InlineKeyboardBuilder()
    for rank in ["E", "D", "C", "B", "A", "S"]:
        emoji = RANK_EMOJI[rank]
        desc  = REPLICS["rank_descriptions"][rank]
        kb.button(text=f"{emoji} {rank}-Ранг", callback_data=f"g_rank:{rank}")
    kb.button(text="⬅️ Назад", callback_data="g_nav")
    kb.adjust(2, 2, 2, 1)
    try:
        await cb.message.edit_text("🏔️ <b>Вылазка за стену</b>\n\nВыбери ранг:", reply_markup=kb.as_markup())
    except:
        pass

@game_router.callback_query(F.data.startswith("g_rank:"))
async def g_rank(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    rank  = cb.data.split(":")[1]
    emoji = RANK_EMOJI[rank]
    desc  = REPLICS["rank_descriptions"][rank]

    kb = InlineKeyboardBuilder()
    kb.button(text="🚀 Вперёд", callback_data=f"g_go_wall:{rank}")
    kb.button(text="⬅️ Назад", callback_data="g_expedition")
    kb.adjust(1)

    try:
        await cb.message.edit_text(
            f"{emoji} <b>{rank}-Ранг</b>\n\n"
            f"<i>{desc}</i>\n\n"
            f"Ты отправляешься за стену, будь готов к битве с титанами.",
            reply_markup=kb.as_markup()
        )
    except:
        pass

@game_router.callback_query(F.data.startswith("g_go_wall:"))
async def g_go_wall(cb: CallbackQuery, state: FSMContext):
    await cb.answer("Выдвигаешься за стену...", show_alert=False)
    rank = cb.data.split(":")[1]

    # Прогрес бар
    bar = "▓" * 0 + "░" * 10
    msg_text = f"⏳ Ты за стеной:\n[{bar}] 0%"
    try:
        await cb.message.edit_text(msg_text)
    except:
        pass

    for i in range(1, 11):
        await asyncio.sleep(1)
        filled = "▓" * i + "░" * (10 - i)
        try:
            await cb.message.edit_text(f"⏳ Выдвигаешься...\n[{filled}] {i*10}%")
        except:
            pass

    kb = InlineKeyboardBuilder()
    kb.button(text="🔍 Найти титана", callback_data=f"g_find_titan:{rank}")
    kb.button(text="🏠 Уйти",         callback_data="g_nav")
    kb.adjust(1)

    await state.set_state(GameStates.outside_wall)
    await state.update_data(expedition_rank=rank)

    try:
        await cb.message.edit_text(
            f"🌫️ <b>Ты за стеной!</b>\n\nРанг: {RANK_EMOJI[rank]} {rank}\n\nЧто будешь делать?",
            reply_markup=kb.as_markup()
        )
    except:
        pass

@game_router.callback_query(F.data.startswith("g_find_titan:"))
async def g_find_titan(cb: CallbackQuery, state: FSMContext):
    await cb.answer("Ищешь титана...")
    rank   = cb.data.split(":")[1]
    enemy  = gdb.generate_enemy(rank)
    player = gdb.get_player(cb.from_user.id)

    # Создаём запись боя
    battle_id = gdb.create_battle(
        player_id=cb.from_user.id,
        player_hp=player["hp"],
        opponent_hp=enemy["hp"],
        battle_type="pve",
        rank=rank,
    )

    await state.set_state(GameStates.battle_pve)
    await state.update_data(
        battle_id=battle_id,
        enemy=enemy,
        rank=rank,
        attack_count=0,
        combo_pending=False,
    )

    found_phrase = rnd(REPLICS["found_titan"])
    text = (
        f"{found_phrase}\n\n"
        f"👾 <b>Титан найден!</b>\n"
        f"❤️ Здоровье: <b>{enemy['hp']}</b>\n"
        f"🛡️ Защита:   <b>{enemy['defense']}</b>\n"
        f"⚔️ Сила:     <b>{enemy['strength']}</b>\n"
        f"💨 Ловкость: <b>{enemy['agility']}</b>\n\n"
        f"──────────────────\n"
        f"<b>Ты:</b>\n"
        f"❤️ HP: <b>{player['hp']}/{player['max_hp']}</b>\n"
        f"⚔️ Сила: <b>{player['strength']}</b> | 🛡️ Защита: <b>{player['defense']}</b>"
    )

    await cb.message.edit_text(text, reply_markup=_battle_kb(cb.from_user.id))

def _battle_kb(user_id: int) -> InlineKeyboardMarkup:
    p        = gdb.get_player(user_id)
    unlocked = gdb.get_unlocked_skills(p)
    combat   = [s for s in unlocked if s != "dodge"]  # dodge отдельно
    kb       = InlineKeyboardBuilder()
    for sk in combat:
        kb.button(text=SKILL_NAMES[sk], callback_data=f"g_attack:{sk}")
    if "dodge" in unlocked:
        kb.button(text="💨 Уклонение", callback_data="g_attack:dodge")
    kb.button(text="🏃 Убежать", callback_data="g_run_away")
    kb.adjust(2)
    return kb.as_markup()

# ── АТАКА ──────────────────────────────────────────────────────────────────────
@game_router.callback_query(F.data.startswith("g_attack:"), GameStates.battle_pve)
async def g_attack_pve(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    data   = await state.get_data()
    skill  = cb.data.split(":")[1]
    battle = gdb.get_battle(data["battle_id"])
    player = gdb.get_player(cb.from_user.id)
    enemy  = data["enemy"]

    player_hp   = battle["player_hp"]
    enemy_hp    = battle["opponent_hp"]
    attack_count = data.get("attack_count", 0) + 1
    lines        = []

    # ── АТАКА ИГРОКА ──────────────────────────────────────────────────────────
    if skill == "dodge":
        dodge_roll = random.random()
        if dodge_roll < gdb.dodge_chance(player["agility"]):
            lines.append(rnd(REPLICS["dodge_success"]))
            lines.append(rnd(REPLICS["attack_phrases"]["dodge"]))
        else:
            lines.append(rnd(REPLICS["dodge_fail"]))
            dmg = gdb.calc_damage(enemy["strength"], player["defense"], "punch")
            player_hp = max(0, player_hp - dmg)
            lines.append(f"💥 Титан воспользовался моментом и нанёс <b>{dmg}</b> урона!")
    else:
        phrase = rnd(REPLICS["attack_phrases"].get(skill, REPLICS["attack_phrases"]["punch"]))
        lines.append(phrase)
        dmg_to_enemy = gdb.calc_damage(player["strength"], enemy["defense"], skill)
        enemy_hp = max(0, enemy_hp - dmg_to_enemy)
        lines.append(f"🗡️ Урон: <b>-{dmg_to_enemy}</b> HP противнику")

    # ── КОМБО ПОСЛЕ 3 АТАК ────────────────────────────────────────────────────
    combo_bonus = 0
    if attack_count % 3 == 0 and skill != "dodge":
        combo_len = random.randint(2, 5)
        combo_announce = rnd(REPLICS["combo_announce"]).format(combo=combo_len)
        lines.append(f"\n🔥 <b>{combo_announce}</b>")
        for _ in range(combo_len - 1):
            extra_skill = random.choice([s for s in gdb.get_unlocked_skills(player) if s != "dodge"])
            extra_dmg   = gdb.calc_damage(player["strength"], enemy["defense"], extra_skill)
            enemy_hp    = max(0, enemy_hp - extra_dmg)
            combo_bonus += extra_dmg
            lines.append(f"  ⚡ {SKILL_NAMES[extra_skill]} — <b>-{extra_dmg}</b> HP")

    # ── ОТВЕТНАЯ АТАКА ТИТАНА ─────────────────────────────────────────────────
    if enemy_hp > 0 and skill != "dodge":
        dodge_roll = random.random()
        enemy_atk_phrase = rnd(REPLICS["enemy_attack_phrases"])
        lines.append(f"\n{enemy_atk_phrase}")
        if dodge_roll < gdb.dodge_chance(player["agility"]):
            lines.append(rnd(REPLICS["dodge_success"]))
        else:
            dmg = gdb.calc_damage(enemy["strength"], player["defense"], "punch")
            player_hp = max(0, player_hp - dmg)
            lines.append(f"💀 Ты получил <b>{dmg}</b> урона!")

    # ── ОБНОВЛЯЕМ БД ──────────────────────────────────────────────────────────
    gdb.update_battle(data["battle_id"], player_hp=player_hp, opponent_hp=enemy_hp)
    await state.update_data(attack_count=attack_count, enemy={**enemy, "hp": enemy_hp})

    battle_text = "\n".join(lines)

    # ── КОНЕЦ БОЯ ─────────────────────────────────────────────────────────────
    if enemy_hp <= 0:
        gdb.end_battle(data["battle_id"])
        # +50 exp
        exp_res = gdb.add_exp(cb.from_user.id, 50)
        gdb.update_stat(cb.from_user.id, "hp", player_hp)
        with __import__("sqlite3").connect(gdb.GAME_DB) as conn:
            conn.execute("UPDATE game_players SET kills=kills+1 WHERE user_id=?", (cb.from_user.id,))

        kb = InlineKeyboardBuilder()
        kb.button(text="🔍 Найти ещё титана", callback_data=f"g_find_titan:{data['rank']}")
        kb.button(text="🏠 Уйти домой",        callback_data="g_nav")
        kb.adjust(1)

        lvl_msg = f"\n🆙 <b>Уровень повышен до {exp_res['new_level']}!</b>" if exp_res.get("leveled_up") else ""
        result_text = (
            f"{battle_text}\n\n"
            f"{rnd(REPLICS['titan_defeated'])}\n\n"
            f"🏆 <b>+50 опыта!</b>{lvl_msg}\n"
            f"❤️ Твоё HP: <b>{player_hp}/{player['max_hp']}</b>"
        )
        await state.set_state(GameStates.outside_wall)
        try:
            await cb.message.edit_text(result_text, reply_markup=kb.as_markup())
        except:
            pass
        return

    if player_hp <= 0:
        gdb.end_battle(data["battle_id"])
        gdb.update_stat(cb.from_user.id, "hp", 1)  # оставим 1 HP
        kb = InlineKeyboardBuilder()
        kb.button(text="🏠 Вернуться", callback_data="g_nav")

        result_text = (
            f"{battle_text}\n\n"
            f"{rnd(REPLICS['player_defeated'])}"
        )
        await state.set_state(GameStates.in_game)
        try:
            await cb.message.edit_text(result_text, reply_markup=kb.as_markup())
        except:
            pass
        return

    # ── ХОД ПРОДОЛЖАЕТСЯ ──────────────────────────────────────────────────────
    status = (
        f"{battle_text}\n\n"
        f"──────────────────\n"
        f"👾 Титан: ❤️ <b>{enemy_hp}</b> HP\n"
        f"👤 Ты:    ❤️ <b>{player_hp}/{player['max_hp']}</b> HP"
    )
    try:
        await cb.message.edit_text(status, reply_markup=_battle_kb(cb.from_user.id))
    except:
        pass

@game_router.callback_query(F.data == "g_run_away")
async def g_run_away(cb: CallbackQuery, state: FSMContext):
    await cb.answer("Ты убежал!")
    data = await state.get_data()
    if data.get("battle_id"):
        gdb.end_battle(data["battle_id"])
    await state.set_state(GameStates.in_game)
    kb = InlineKeyboardBuilder()
    kb.button(text="🏔️ Обратно за стену", callback_data="g_expedition")
    kb.button(text="🗺️ Навигация",         callback_data="g_nav")
    kb.adjust(1)
    try:
        await cb.message.edit_text("🏃 Ты спасся бегством! Может, в другой раз...", reply_markup=kb.as_markup())
    except:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  /duel  — ДУЭЛЬ
# ══════════════════════════════════════════════════════════════════════════════
@game_router.message(Command("duel"))
async def cmd_duel(message: Message, state: FSMContext):
    challenger = gdb.get_player(message.from_user.id)
    if not challenger:
        await message.answer("Сначала зарегистрируйся через /game")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: /duel @username или /duel user_id")
        return

    target_str = args[1].strip().lstrip("@")
    target_uid = None

    # Попробуем найти по ID
    if target_str.isdigit():
        target_uid = int(target_str)
    else:
        # Поиск по username в users.db
        import sqlite3 as _sq
        with _sq.connect("users.db") as conn:
            row = conn.execute("SELECT user_id FROM users WHERE username=?", (target_str,)).fetchone()
            if row:
                target_uid = row[0]

    if not target_uid:
        await message.answer("Игрок не найден. Убедись что он писал в этом чате.")
        return

    if target_uid == message.from_user.id:
        await message.answer("Нельзя вызвать самого себя на дуэль 😄")
        return

    target_player = gdb.get_player(target_uid)
    if not target_player:
        await message.answer("Этот игрок ещё не зарегистрирован в игре.")
        return

    duel_id = gdb.create_duel_request(message.from_user.id, target_uid)

    challenger_name  = message.from_user.first_name
    challenger_titan = TITAN_INFO[challenger["titan_type"]]["name"]

    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Принять",  callback_data=f"duel_accept:{duel_id}")
    kb.button(text="❌ Отказать", callback_data=f"duel_decline:{duel_id}")
    kb.adjust(2)

    try:
        from mef import bot  # импортируем bot из mef
        await bot.send_message(
            target_uid,
            f"⚔️ <b>Вызов на дуэль!</b>\n\n"
            f"👤 <b>{challenger_name}</b> вызывает тебя на бой!\n"
            f"🤖 Его титан: {challenger_titan}\n\n"
            f"Принимаешь вызов?",
            reply_markup=kb.as_markup()
        )
        await message.answer(f"✅ Вызов отправлен игроку!")
    except Exception as e:
        await message.answer(f"Не удалось отправить вызов. Убедись что игрок писал боту лично.")

    try:
        await message.delete()
    except:
        pass

@game_router.callback_query(F.data.startswith("duel_accept:"))
async def duel_accept(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    duel_id = int(cb.data.split(":")[1])
    duel    = gdb.get_duel_request(duel_id)

    if not duel or duel["status"] != "pending":
        await cb.answer("Дуэль уже недействительна.", show_alert=True)
        return

    if cb.from_user.id != duel["target_id"]:
        await cb.answer("Этот вызов не для тебя.", show_alert=True)
        return

    gdb.update_duel_status(duel_id, "accepted")

    challenger = gdb.get_player(duel["challenger_id"])
    target     = gdb.get_player(duel["target_id"])

    # Создаём бой для обоих
    battle_id = gdb.create_battle(
        player_id=duel["challenger_id"],
        player_hp=challenger["hp"],
        opponent_hp=target["hp"],
        battle_type="pvp",
        opponent_id=duel["target_id"],
    )
    # Сохраняем в state для target
    await state.set_state(GameStates.duel_battle)
    await state.update_data(
        duel_battle_id=battle_id,
        duel_role="target",
        duel_opponent_id=duel["challenger_id"],
        attack_count=0,
    )

    c_name = TITAN_INFO[challenger["titan_type"]]["name"]
    t_name = TITAN_INFO[target["titan_type"]]["name"]

    text = (
        f"⚔️ <b>ДУЭЛЬ!</b>\n\n"
        f"👤 Ты ({t_name}): ❤️ <b>{target['hp']}/{target['max_hp']}</b>\n"
        f"⚔️ Соперник ({c_name}): ❤️ <b>{challenger['hp']}/{challenger['max_hp']}</b>\n\n"
        f"<i>Первый ход за тобой!</i>"
    )

    await cb.message.edit_text(text, reply_markup=_duel_kb(cb.from_user.id))

    # Уведомляем challenger
    try:
        from mef import bot
        await bot.send_message(
            duel["challenger_id"],
            f"⚔️ <b>Дуэль принята!</b>\n\n"
            f"Бой начинается!\n"
            f"👤 Ты ({c_name}): ❤️ <b>{challenger['hp']}</b>\n"
            f"Жди своей очереди...",
        )
    except:
        pass

def _duel_kb(user_id: int) -> InlineKeyboardMarkup:
    p        = gdb.get_player(user_id)
    unlocked = gdb.get_unlocked_skills(p)
    combat   = [s for s in unlocked if s != "dodge"]
    kb       = InlineKeyboardBuilder()
    for sk in combat:
        kb.button(text=SKILL_NAMES[sk], callback_data=f"g_duel_attack:{sk}")
    if "dodge" in unlocked:
        kb.button(text="💨 Уклонение", callback_data="g_duel_attack:dodge")
    kb.adjust(2)
    return kb.as_markup()

@game_router.callback_query(F.data == "duel_decline")
@game_router.callback_query(F.data.startswith("duel_decline:"))
async def duel_decline(cb: CallbackQuery):
    await cb.answer()
    try:
        duel_id = int(cb.data.split(":")[1])
        gdb.update_duel_status(duel_id, "declined")
        duel = gdb.get_duel_request(duel_id)
        try:
            from mef import bot
            await bot.send_message(duel["challenger_id"], "❌ Твой вызов на дуэль был отклонён.")
        except:
            pass
    except:
        pass
    try:
        await cb.message.edit_text("❌ Ты отклонил вызов на дуэль.")
    except:
        pass

@game_router.callback_query(F.data.startswith("g_duel_attack:"), GameStates.duel_battle)
async def g_duel_attack(cb: CallbackQuery, state: FSMContext):
    """Упрощённый PvP — атака по данным из БД."""
    await cb.answer()
    data     = await state.get_data()
    skill    = cb.data.split(":")[1]
    battle   = gdb.get_battle(data["duel_battle_id"])
    attacker = gdb.get_player(cb.from_user.id)
    role     = data.get("duel_role", "target")

    # Роли
    if role == "target":
        atk_hp  = battle["opponent_hp"]
        def_hp  = battle["player_hp"]
        opp_id  = battle["player_id"]
        atk_col = "opponent_hp"
        def_col = "player_hp"
    else:
        atk_hp  = battle["player_hp"]
        def_hp  = battle["opponent_hp"]
        opp_id  = battle["opponent_id"]
        atk_col = "player_hp"
        def_col = "opponent_hp"

    defender = gdb.get_player(opp_id)
    lines    = []
    attack_count = data.get("attack_count", 0) + 1

    if skill == "dodge":
        if random.random() < gdb.dodge_chance(attacker["agility"]):
            lines.append(rnd(REPLICS["dodge_success"]))
        else:
            dmg = gdb.calc_damage(defender["strength"], attacker["defense"], "punch")
            atk_hp = max(0, atk_hp - dmg)
            lines.append(f"💥 Уклонение не удалось! -{dmg} HP!")
    else:
        phrase = rnd(REPLICS["attack_phrases"].get(skill, REPLICS["attack_phrases"]["punch"]))
        lines.append(phrase)
        dmg = gdb.calc_damage(attacker["strength"], defender["defense"], skill)
        def_hp = max(0, def_hp - dmg)
        lines.append(f"⚔️ -{dmg} HP сопернику!")

        # комбо рандомное в pvp
        if attack_count % 3 == 0:
            combo_len = random.randint(2, 5)
            lines.append(f"\n🔥 КОМБО x{combo_len}!")
            for _ in range(combo_len - 1):
                ex = random.choice([s for s in gdb.get_unlocked_skills(attacker) if s != "dodge"])
                ed = gdb.calc_damage(attacker["strength"], defender["defense"], ex)
                def_hp = max(0, def_hp - ed)
                lines.append(f"  ⚡ {SKILL_NAMES[ex]} — -{ed} HP")

    # Обновляем БД
    gdb.update_battle(battle["battle_id"], **{atk_col: atk_hp, def_col: def_hp})
    await state.update_data(attack_count=attack_count)

    battle_text = "\n".join(lines)

    # Проверяем конец
    if def_hp <= 0 or atk_hp <= 0:
        gdb.end_battle(battle["battle_id"])
        winner = cb.from_user.id if def_hp <= 0 else opp_id
        loser  = opp_id if def_hp <= 0 else cb.from_user.id
        exp_res = gdb.add_exp(winner, 100)
        lvl_msg = f"\n🆙 Уровень {exp_res['new_level']}!" if exp_res.get("leveled_up") else ""

        result = "🏆 Ты победил!" if winner == cb.from_user.id else "💀 Ты проиграл!"
        kb = InlineKeyboardBuilder()
        kb.button(text="🗺️ Навигация", callback_data="g_nav")
        await state.set_state(GameStates.in_game)
        try:
            await cb.message.edit_text(
                f"{battle_text}\n\n{result}{lvl_msg}",
                reply_markup=kb.as_markup()
            )
        except:
            pass

        try:
            from mef import bot
            opp_result = "🏆 Ты победил!" if loser == opp_id else "💀 Ты проиграл!"
            await bot.send_message(opp_id, f"⚔️ Дуэль завершена!\n\n{opp_result}")
        except:
            pass
        return

    # Уведомляем соперника о его ходе
    try:
        from mef import bot
        await bot.send_message(
            opp_id,
            f"⚔️ <b>Ход соперника прошёл!</b>\n\n{battle_text}\n\n"
            f"❤️ Твоё HP: <b>{atk_hp if role != 'target' else def_hp}</b>\n\n"
            f"<b>Твой ход!</b>",
        )
    except:
        pass

    try:
        await cb.message.edit_text(
            f"{battle_text}\n\n"
            f"❤️ Твоё HP: <b>{atk_hp}</b>\n"
            f"👾 Соперник: ❤️ <b>{def_hp}</b>\n\n"
            f"<i>Ожидай ответный ход...</i>",
        )
    except:
        pass
