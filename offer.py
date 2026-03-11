import sqlite3
from typing import List, Dict, Any, Optional
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
        conn.execute("UPDATE offers SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ? WHERE offer_id = ?",
                     (status, reviewed_by, offer_id))
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