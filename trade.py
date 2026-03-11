import sqlite3
from typing import List, Dict, Any, Optional
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup

class TradeStates(StatesGroup):
    WAITING_TITLE = State()
    WAITING_OFFER = State()
    WAITING_WANT = State()
    WAITING_SEARCH = State()

class TradeStatus:
    ACTIVE = "active"
    DELETED = "deleted"

def init_trades_db():
    with sqlite3.connect("trade.db") as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                username TEXT,
                first_name TEXT,
                title TEXT NOT NULL,
                offer TEXT NOT NULL,
                want TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def create_trade(user_id: int, username: str, first_name: str, 
                 title: str, offer: str, want: str) -> int:
    with sqlite3.connect("trade.db") as conn:
        cursor = conn.execute("""
            INSERT INTO trades (user_id, username, first_name, title, offer, want, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            RETURNING trade_id
        """, (user_id, username, first_name, title, offer, want, TradeStatus.ACTIVE))
        trade_id = cursor.fetchone()[0]
        conn.commit()
        return trade_id

def get_active_trades() -> List[Dict[str, Any]]:
    with sqlite3.connect("trade.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM trades 
            WHERE status = ? 
            ORDER BY created_at DESC
        """, (TradeStatus.ACTIVE,))
        return [dict(row) for row in cursor.fetchall()]

def get_user_trades(user_id: int) -> List[Dict[str, Any]]:
    with sqlite3.connect("trade.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM trades 
            WHERE user_id = ? AND status = ?
            ORDER BY created_at DESC
        """, (user_id, TradeStatus.ACTIVE))
        return [dict(row) for row in cursor.fetchall()]

def get_trade_by_id(trade_id: int) -> Optional[Dict[str, Any]]:
    with sqlite3.connect("trade.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM trades 
            WHERE trade_id = ?
        """, (trade_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def delete_trade(trade_id: int) -> None:
    with sqlite3.connect("trade.db") as conn:
        conn.execute("""
            UPDATE trades SET status = ? WHERE trade_id = ?
        """, (TradeStatus.DELETED, trade_id))
        conn.commit()

def search_trades_by_want(query: str) -> List[Dict[str, Any]]:
    with sqlite3.connect("trade.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("""
            SELECT * FROM trades 
            WHERE status = ? AND LOWER(want) LIKE ?
            ORDER BY created_at DESC
        """, (TradeStatus.ACTIVE, f"%{query.lower()}%"))
        return [dict(row) for row in cursor.fetchall()]

def get_trades_keyboard(page: int = 0, items_per_page: int = 7) -> InlineKeyboardMarkup:
    trades = get_active_trades()
    
    if not trades:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="back_to_trade_main")
        return builder.as_markup()
    
    start = page * items_per_page
    end = start + items_per_page
    page_trades = trades[start:end]
    
    builder = InlineKeyboardBuilder()
    
    for trade in page_trades:
        builder.button(
            text=trade['title'][:30],
            callback_data=f"view_trade:{trade['trade_id']}"
        )
    
    nav_builder = InlineKeyboardBuilder()
    if page > 0:
        nav_builder.button(text="⬅️", callback_data=f"trades_page:{page-1}")
    nav_builder.button(text="🏠", callback_data="back_to_trade_main")
    if end < len(trades):
        nav_builder.button(text="➡️", callback_data=f"trades_page:{page+1}")
    
    if nav_builder.buttons:
        builder.attach(nav_builder)
    
    builder.adjust(1)
    return builder.as_markup()

def get_user_trades_keyboard(user_id: int) -> InlineKeyboardMarkup:
    trades = get_user_trades(user_id)
    
    if not trades:
        builder = InlineKeyboardBuilder()
        builder.button(text="◀️ Назад", callback_data="back_to_trade_main")
        return builder.as_markup()
    
    builder = InlineKeyboardBuilder()
    
    for trade in trades:
        builder.button(
            text=trade['title'][:30],
            callback_data=f"my_trade:{trade['trade_id']}"
        )
    
    builder.button(text="◀️ Назад", callback_data="back_to_trade_main")
    builder.adjust(1)
    return builder.as_markup()

def get_trade_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🔄 Трейд", callback_data="trade_menu")
    builder.button(text="📋 Мои предложения", callback_data="my_trades")
    builder.adjust(1)
    return builder.as_markup()

def get_trade_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🏪 Площадка", callback_data="trade_platform")
    builder.button(text="➕ Выставить Предложение", callback_data="create_trade")
    builder.button(text="🔍 Найти предложение", callback_data="search_trade")
    builder.button(text="◀️ Назад", callback_data="back_to_trade_main")
    builder.adjust(1)
    return builder.as_markup()

def get_back_keyboard(callback_data: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="◀️ Назад", callback_data=callback_data)
    return builder.as_markup()