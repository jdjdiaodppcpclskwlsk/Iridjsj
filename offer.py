import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from aiogram import Bot, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
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


def create_offer(user_id: int, username: str, first_name: str, 
                 offer_name: str, description: str, benefit: str) -> int:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        cursor = conn.execute("""
            INSERT INTO offers (user_id, username, first_name, offer_name, 
                               description, benefit, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING offer_id
        """, (user_id, username, first_name, offer_name, description, benefit, OfferStatus.PENDING))
        offer_id = cursor.fetchone()[0]
        conn.commit()
        return offer_id


def get_user_offers(user_id: int) -> List[Dict[str, Any]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM offers 
            WHERE user_id = ? 
            ORDER BY created_at DESC
        """, (user_id,))
        return [dict(row) for row in cursor.fetchall()]


def get_offers_by_status(status: str) -> List[Dict[str, Any]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM offers 
            WHERE status = ? 
            ORDER BY created_at DESC
        """, (status,))
        return [dict(row) for row in cursor.fetchall()]


def get_offer_by_id(offer_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM offers 
            WHERE offer_id = ?
        """, (offer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_offer_status(offer_id: int, status: str, reviewed_by: int) -> None:
    with sqlite3.connect("verified_mega_aotr.db") as conn:
        conn.execute("""
            UPDATE offers 
            SET status = ?, reviewed_at = CURRENT_TIMESTAMP, reviewed_by = ?
            WHERE offer_id = ?
        """, (status, reviewed_by, offer_id))
        conn.commit()


def get_offers_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    pending_count = len(get_offers_by_status(OfferStatus.PENDING))
    accepted_count = len(get_offers_by_status(OfferStatus.ACCEPTED))
    rejected_count = len(get_offers_by_status(OfferStatus.REJECTED))
    
    builder.button(text=f"⏳ Ждут рассмотрения ({pending_count})", callback_data="offers_pending")
    builder.button(text=f"✅ Приняты ({accepted_count})", callback_data="offers_accepted")
    builder.button(text=f"❌ Отклонены ({rejected_count})", callback_data="offers_rejected")
    builder.button(text="◀️ Назад", callback_data="back_to_admin")
    builder.adjust(1)
    return builder.as_markup()


def get_user_offers_keyboard(user_id: int, page: int = 0) -> InlineKeyboardMarkup:
    offers = get_user_offers(user_id)
    if not offers:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="back_to_offer_main")
        return builder.as_markup()
    
    PER_PAGE = 5
    start = page * PER_PAGE
    end = start + PER_PAGE
    page_offers = offers[start:end]
    
    builder = InlineKeyboardBuilder()
    
    for offer in page_offers:
        status_emoji = {
            OfferStatus.PENDING: "⏳",
            OfferStatus.ACCEPTED: "✅",
            OfferStatus.REJECTED: "❌"
        }.get(offer['status'], "📝")
        
        builder.button(
            text=f"{status_emoji} {offer['offer_name'][:20]}...",
            callback_data=f"view_my_offer:{offer['offer_id']}"
        )
    
    nav_builder = InlineKeyboardBuilder()
    if page > 0:
        nav_builder.button(text="⬅️", callback_data=f"my_offers_page:{page-1}")
    nav_builder.button(text="🏠", callback_data="back_to_offer_main")
    if end < len(offers):
        nav_builder.button(text="➡️", callback_data=f"my_offers_page:{page+1}")
    
    if nav_builder.buttons:
        builder.attach(nav_builder)
    
    builder.adjust(1)
    return builder.as_markup()


def get_offers_list_keyboard(status: str, page: int = 0) -> InlineKeyboardMarkup:
    offers = get_offers_by_status(status)
    if not offers:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="offers_menu")
        return builder.as_markup()
    
    PER_PAGE = 5
    start = page * PER_PAGE
    end = start + PER_PAGE
    page_offers = offers[start:end]
    
    builder = InlineKeyboardBuilder()
    
    for offer in page_offers:
        builder.button(
            text=f"{offer['first_name']} - {offer['offer_name'][:20]}...",
            callback_data=f"admin_view_offer:{offer['offer_id']}"
        )
    
    nav_builder = InlineKeyboardBuilder()
    if page > 0:
        nav_builder.button(text="⬅️", callback_data=f"offers_{status}_page:{page-1}")
    nav_builder.button(text="🏠", callback_data="offers_menu")
    if end < len(offers):
        nav_builder.button(text="➡️", callback_data=f"offers_{status}_page:{page+1}")
    
    if nav_builder.buttons:
        builder.attach(nav_builder)
    
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
    status_text = "принята" if status == OfferStatus.ACCEPTED else "отклонена"
    try:
        await bot.send_message(
            user_id,
            f"📬 <b>Заявка '{offer_name}' {status_text}!</b>\n\n"
            f"Статус: {OfferStatus.get_text(status)}"
        )
    except:
        pass


def get_offer_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="📝 Создать заявку", callback_data="create_offer")
    builder.button(text="📋 Мои заявки", callback_data="my_offers")
    builder.adjust(1)
    return builder.as_markup()