import asyncio
import sqlite3
from typing import List, Dict, Any, Optional
from aiogram import Bot, Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import database

router = Router()

CREATOR_ID = 7306010609


class OfferStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_benefit = State()


class OfferStatus:
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

    @classmethod
    def get_text(cls, status: str) -> str:
        texts = {
            cls.PENDING: "⏳ На рассмотрении...",
            cls.ACCEPTED: "✅ Принято",
            cls.REJECTED: "❌ Отклонено"
        }
        return texts.get(status, status)


def init_offers_db():
    with sqlite3.connect("offers.db") as conn:
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


def create_offer(user_id: int, username: str, first_name: str,
                 offer_name: str, description: str, benefit: str) -> int:
    with sqlite3.connect("offers.db") as conn:
        cur = conn.execute("""
            INSERT INTO offers (user_id, username, first_name, offer_name, description, benefit, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING offer_id
        """, (user_id, username, first_name, offer_name, description, benefit, OfferStatus.PENDING))
        oid = cur.fetchone()[0]
        conn.commit()
        return oid


def get_user_offers(user_id: int) -> List[Dict[str, Any]]:
    with sqlite3.connect("offers.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM offers WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in cur.fetchall()]


def get_offers_by_status(status: str) -> List[Dict[str, Any]]:
    with sqlite3.connect("offers.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM offers WHERE status = ? ORDER BY created_at DESC", (status,))
        return [dict(row) for row in cur.fetchall()]


def get_offer_by_id(offer_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect("offers.db") as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.execute("SELECT * FROM offers WHERE offer_id = ?", (offer_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def update_offer_status(offer_id: int, status: str, reviewed_by: int) -> None:
    with sqlite3.connect("offers.db") as conn:
        conn.execute(
            "UPDATE offers SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ? WHERE offer_id = ?",
            (status, reviewed_by, offer_id)
        )
        conn.commit()


def get_offers_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    pending = len(get_offers_by_status(OfferStatus.PENDING))
    accepted = len(get_offers_by_status(OfferStatus.ACCEPTED))
    rejected = len(get_offers_by_status(OfferStatus.REJECTED))
    builder.button(text=f"⏳ Ждут рассмотрения ({pending})", callback_data="offers_pending")
    builder.button(text=f"✅ Приняты ({accepted})", callback_data="offers_accepted")
    builder.button(text=f"❌ Отклонены ({rejected})", callback_data="offers_rejected")
    builder.button(text="◀️ Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()


def get_user_offers_keyboard(user_id: int, page: int = 0) -> InlineKeyboardMarkup:
    offers = get_user_offers(user_id)
    if not offers:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="back_to_offer_main")
        return builder.as_markup()
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_offers = offers[start:end]
    builder = InlineKeyboardBuilder()
    for off in page_offers:
        emoji = {"pending": "⏳", "accepted": "✅", "rejected": "❌"}.get(off['status'], "📝")
        builder.button(text=f"{emoji} {off['offer_name'][:20]}...", callback_data=f"view_my_offer:{off['offer_id']}")
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="⬅️", callback_data=f"my_offers_page:{page-1}")
    nav.button(text="🏠", callback_data="back_to_offer_main")
    if end < len(offers):
        nav.button(text="➡️", callback_data=f"my_offers_page:{page+1}")
    if nav.buttons:
        builder.attach(nav)
    builder.adjust(1)
    return builder.as_markup()


def get_offers_list_keyboard(status: str, page: int = 0) -> InlineKeyboardMarkup:
    offers = get_offers_by_status(status)
    if not offers:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="offers_menu")
        return builder.as_markup()
    per_page = 5
    start = page * per_page
    end = start + per_page
    page_offers = offers[start:end]
    builder = InlineKeyboardBuilder()
    for off in page_offers:
        builder.button(text=f"{off['first_name']} - {off['offer_name'][:20]}...", callback_data=f"admin_view_offer:{off['offer_id']}")
    nav = InlineKeyboardBuilder()
    if page > 0:
        nav.button(text="⬅️", callback_data=f"offers_{status}_page:{page-1}")
    nav.button(text="🏠", callback_data="offers_menu")
    if end < len(offers):
        nav.button(text="➡️", callback_data=f"offers_{status}_page:{page+1}")
    if nav.buttons:
        builder.attach(nav)
    builder.adjust(1)
    return builder.as_markup()


def format_offer_text(offer: Dict[str, Any], for_admin: bool = False) -> str:
    text = f"<b>{offer['offer_name']}</b>\n\n"
    text += f"📝 <b>Описание:</b>\n{offer['description']}\n\n"
    text += f"💡 <b>Чем будет полезно:</b>\n{offer['benefit']}\n\n"
    text += f"📊 <b>Статус:</b> {OfferStatus.get_text(offer['status'])}\n"
    if for_admin:
        text += f"\n👤 <b>Отправитель:</b>\n"
        text += f"ID: {offer['user_id']}\n"
        text += f"Имя: {offer['first_name']}\n"
        if offer['username']:
            text += f"Юзернейм: @{offer['username']}\n"
        text += f"📅 Дата: {offer['created_at']}"
    return text


async def send_offer_notification(bot: Bot, user_id: int, offer_name: str, status: str):
    st = "принята" if status == OfferStatus.ACCEPTED else "отклонена"
    try:
        await bot.send_message(user_id, f"📬 <b>Заявка '{offer_name}' {st}!</b>\n\nСтатус: {OfferStatus.get_text(status)}")
    except:
        pass


def get_offer_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать заявку", callback_data="create_offer")
    builder.button(text="📋 Мои заявки", callback_data="my_offers")
    builder.adjust(1)
    return builder.as_markup()


# --- Handlers ---

@router.message(Command("offer"))
async def cmd_offer(message: Message, state: FSMContext):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    await state.clear()
    await message.answer("Ваши идеи для бота:", reply_markup=get_offer_main_menu())
    await message.delete()


@router.callback_query(F.data == "create_offer")
async def create_offer_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_offer")
    await callback.message.edit_text("Создание заявки\n\nШаг 1/3\nВведи название идеи:", reply_markup=b.as_markup())
    await state.set_state(OfferStates.waiting_for_name)


@router.callback_query(F.data == "cancel_offer")
async def cancel_offer(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Ваши идеи для бота:", reply_markup=get_offer_main_menu())


@router.message(OfferStates.waiting_for_name)
async def process_offer_name(message: Message, state: FSMContext):
    await state.update_data(offer_name=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_offer")
    await message.answer("Создание заявки\n\nШаг 2/3\nВведи описание/принцип работы:", reply_markup=b.as_markup())
    await state.set_state(OfferStates.waiting_for_description)
    await message.delete()


@router.message(OfferStates.waiting_for_description)
async def process_offer_description(message: Message, state: FSMContext):
    await state.update_data(description=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_offer")
    await message.answer("Создание заявки\n\nШаг 3/3\nВведи чем будет полезно:", reply_markup=b.as_markup())
    await state.set_state(OfferStates.waiting_for_benefit)
    await message.delete()


@router.message(OfferStates.waiting_for_benefit)
async def process_offer_benefit(message: Message, state: FSMContext):
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


@router.callback_query(F.data == "submit_offer")
async def submit_offer(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    create_offer(user.id, user.username, user.first_name, data['offer_name'], data['description'], data['benefit'])
    await state.clear()
    await callback.message.edit_text("Заявка отправлена на рассмотрение, ответ придет когда ее проверят.")
    await asyncio.sleep(2)
    await callback.message.edit_text("Ваши идеи для бота:", reply_markup=get_offer_main_menu())


@router.callback_query(F.data == "my_offers")
async def my_offers(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    kb = get_user_offers_keyboard(uid)
    offs = get_user_offers(uid)
    if not offs:
        await callback.message.edit_text("У тебя пока нет заявок", reply_markup=kb)
    else:
        await callback.message.edit_text("Твои заявки:", reply_markup=kb)


@router.callback_query(F.data.startswith("my_offers_page:"))
async def my_offers_page(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    uid = callback.from_user.id
    kb = get_user_offers_keyboard(uid, page)
    await callback.message.edit_text("Твои заявки:", reply_markup=kb)


@router.callback_query(F.data.startswith("view_my_offer:"))
async def view_my_offer(callback: CallbackQuery):
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    off = get_offer_by_id(oid)
    if not off:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    b = InlineKeyboardBuilder()
    b.button(text="Назад", callback_data="my_offers")
    await callback.message.edit_text(format_offer_text(off, False), reply_markup=b.as_markup())


@router.callback_query(F.data == "back_to_offer_main")
async def back_to_offer_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Ваши идеи для бота:", reply_markup=get_offer_main_menu())


# --- Admin offer handlers ---

@router.callback_query(F.data == "offers_menu")
async def offers_menu(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    await callback.message.edit_text("Управление заявками:", reply_markup=get_offers_menu())


@router.callback_query(F.data == "offers_pending")
async def offers_pending(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    kb = get_offers_list_keyboard(OfferStatus.PENDING)
    offs = get_offers_by_status(OfferStatus.PENDING)
    if not offs:
        await callback.message.edit_text("Нет заявок, ожидающих рассмотрения", reply_markup=kb)
    else:
        await callback.message.edit_text("Заявки, ожидающие рассмотрения:", reply_markup=kb)


@router.callback_query(F.data == "offers_accepted")
async def offers_accepted(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    kb = get_offers_list_keyboard(OfferStatus.ACCEPTED)
    offs = get_offers_by_status(OfferStatus.ACCEPTED)
    if not offs:
        await callback.message.edit_text("Нет принятых заявок", reply_markup=kb)
    else:
        await callback.message.edit_text("Принятые заявки:", reply_markup=kb)


@router.callback_query(F.data == "offers_rejected")
async def offers_rejected(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    kb = get_offers_list_keyboard(OfferStatus.REJECTED)
    offs = get_offers_by_status(OfferStatus.REJECTED)
    if not offs:
        await callback.message.edit_text("Нет отклоненных заявок", reply_markup=kb)
    else:
        await callback.message.edit_text("Отклоненные заявки:", reply_markup=kb)


@router.callback_query(F.data.startswith("offers_pending_page:"))
@router.callback_query(F.data.startswith("offers_accepted_page:"))
@router.callback_query(F.data.startswith("offers_rejected_page:"))
async def offers_page(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    parts = callback.data.split(":")
    status = parts[0].split("_")[1]
    page = int(parts[1])
    stat_map = {"pending": OfferStatus.PENDING, "accepted": OfferStatus.ACCEPTED, "rejected": OfferStatus.REJECTED}
    text_map = {"pending": "ожидающих рассмотрения", "accepted": "принятых", "rejected": "отклоненных"}
    kb = get_offers_list_keyboard(stat_map[status], page)
    await callback.message.edit_text(f"Заявки {text_map[status]}:", reply_markup=kb)


@router.callback_query(F.data.startswith("admin_view_offer:"))
async def admin_view_offer(callback: CallbackQuery):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    off = get_offer_by_id(oid)
    if not off:
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


@router.callback_query(F.data.startswith("accept_offer:"))
async def accept_offer(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    off = get_offer_by_id(oid)
    if not off:
        await callback.answer("Заявка не найдена", show_alert=True)
        return
    update_offer_status(oid, OfferStatus.ACCEPTED, callback.from_user.id)
    await send_offer_notification(bot, off['user_id'], off['offer_name'], OfferStatus.ACCEPTED)
    await callback.message.edit_text(f"заявка '{off['offer_name']}' принята!")
    await asyncio.sleep(1)
    await callback.message.edit_text("Управление заявками:", reply_markup=get_offers_menu())


@router.callback_query(F.data.startswith("reject_offer:"))
async def reject_offer(callback: CallbackQuery, bot: Bot):
    if callback.from_user.id != CREATOR_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
    await callback.answer()
    oid = int(callback.data.split(":")[1])
    off = get_offer_by_id(oid)
    if not off:
        await callback.answer("Заявки нема", show_alert=True)
        return
    update_offer_status(oid, OfferStatus.REJECTED, callback.from_user.id)
    await send_offer_notification(bot, off['user_id'], off['offer_name'], OfferStatus.REJECTED)
    await callback.message.edit_text(f"заявка '{off['offer_name']}' отклонена!")
    await asyncio.sleep(1)
    await callback.message.edit_text("Управление заявками:", reply_markup=get_offers_menu())
