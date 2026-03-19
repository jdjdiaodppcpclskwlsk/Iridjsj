import asyncio
import sqlite3
from typing import List, Dict, Any, Optional
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import database

router = Router()

CREATOR_ID = 7306010609


class TradeStates(StatesGroup):
    WAITING_TITLE = State()
    WAITING_OFFER = State()
    WAITING_WANT = State()


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
        cursor = conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def delete_trade(trade_id: int) -> None:
    with sqlite3.connect("trade.db") as conn:
        conn.execute("UPDATE trades SET status = ? WHERE trade_id = ?", (TradeStatus.DELETED, trade_id))
        conn.commit()


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
        builder.button(text=trade['title'][:30], callback_data=f"view_trade:{trade['trade_id']}")
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
        builder.button(text=trade['title'][:30], callback_data=f"my_trade:{trade['trade_id']}")
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
    builder.button(text="◀️ Назад", callback_data="back_to_trade_main")
    builder.adjust(1)
    return builder.as_markup()


# --- Handlers ---

@router.message(Command("trade"))
async def cmd_trade(message: Message, state: FSMContext):
    if not database.check_chat_verified(message.chat.id):
        await message.answer("Бот не верифицирован в этом чате.")
        return
    await state.clear()
    await message.answer("Торговая площадка:", reply_markup=get_trade_main_menu())
    await message.delete()


@router.callback_query(F.data == "trade_menu")
async def trade_menu(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Трейд:", reply_markup=get_trade_menu())


@router.callback_query(F.data == "back_to_trade_main")
async def back_to_trade_main(callback: CallbackQuery):
    await callback.answer()
    await callback.message.edit_text("Торговая площадка:", reply_markup=get_trade_main_menu())


@router.callback_query(F.data == "trade_platform")
async def trade_platform(callback: CallbackQuery):
    await callback.answer()
    kb = get_trades_keyboard(0)
    tr = get_active_trades()
    if not tr:
        await callback.message.edit_text("Нет предложений", reply_markup=kb)
    else:
        await callback.message.edit_text("Все предложения:", reply_markup=kb)


@router.callback_query(F.data.startswith("trades_page:"))
async def trades_page(callback: CallbackQuery):
    await callback.answer()
    page = int(callback.data.split(":")[1])
    await callback.message.edit_text("Все предложения:", reply_markup=get_trades_keyboard(page))


@router.callback_query(F.data.startswith("view_trade:"))
async def view_trade(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split(":")[1])
    tr = get_trade_by_id(tid)
    if not tr:
        await callback.answer("Предложение нема", show_alert=True)
        return
    text = (f"Ник: {tr['first_name']}\nЮзер: @{tr['username'] if tr['username'] else 'нет'}\n"
            f"Айди: {tr['user_id']}\n\nТрейдит:\n{tr['offer']}\n\nИщет:\n{tr['want']}")
    b = InlineKeyboardBuilder()
    b.button(text="◀️ Назад", callback_data="trade_platform")
    await callback.message.edit_text(text, reply_markup=b.as_markup())


@router.callback_query(F.data == "create_trade")
async def create_trade_start(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_trade")
    await callback.message.edit_text("Создание предложения\n\nШаг 1/3\nВведи название предложения:", reply_markup=b.as_markup())
    await state.set_state(TradeStates.WAITING_TITLE)


@router.callback_query(F.data == "cancel_trade")
async def cancel_trade(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await state.clear()
    await callback.message.edit_text("Трейд:", reply_markup=get_trade_menu())


@router.message(TradeStates.WAITING_TITLE)
async def process_trade_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_trade")
    await message.answer("Создание предложения\n\nШаг 2/3\nВведи что трейдишь:", reply_markup=b.as_markup())
    await state.set_state(TradeStates.WAITING_OFFER)
    await message.delete()


@router.message(TradeStates.WAITING_OFFER)
async def process_trade_offer(message: Message, state: FSMContext):
    await state.update_data(offer=message.text)
    b = InlineKeyboardBuilder()
    b.button(text="Отмена", callback_data="cancel_trade")
    await message.answer("Создание предложения\n\nШаг 3/3\nВведи что хочешь получить взамен:", reply_markup=b.as_markup())
    await state.set_state(TradeStates.WAITING_WANT)
    await message.delete()


@router.message(TradeStates.WAITING_WANT)
async def process_trade_want(message: Message, state: FSMContext):
    await state.update_data(want=message.text)
    data = await state.get_data()
    b = InlineKeyboardBuilder()
    b.button(text="Подтвердить", callback_data="submit_trade")
    b.button(text="Отменить", callback_data="cancel_trade")
    b.adjust(1)
    text = f"Название: {data['title']}\n\nТрейдит:\n{data['offer']}\n\nИщет:\n{data['want']}"
    await message.answer(text, reply_markup=b.as_markup())
    await message.delete()


@router.callback_query(F.data == "submit_trade")
async def submit_trade(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user = callback.from_user
    create_trade(user.id, user.username, user.first_name, data['title'], data['offer'], data['want'])
    await state.clear()
    await callback.message.edit_text("Предложение сделано")
    await asyncio.sleep(1)
    await callback.message.edit_text("Трейд:", reply_markup=get_trade_menu())


@router.callback_query(F.data == "my_trades")
async def my_trades(callback: CallbackQuery):
    await callback.answer()
    uid = callback.from_user.id
    kb = get_user_trades_keyboard(uid)
    tr = get_user_trades(uid)
    if not tr:
        await callback.message.edit_text("У тебя нет предложений", reply_markup=kb)
    else:
        await callback.message.edit_text("Твои предложения:", reply_markup=kb)


@router.callback_query(F.data.startswith("my_trade:"))
async def my_trade_detail(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split(":")[1])
    tr = get_trade_by_id(tid)
    if not tr:
        await callback.answer("Предложение нема", show_alert=True)
        return
    text = f"Название: {tr['title']}\n\nТрейдит:\n{tr['offer']}\n\nИщет:\n{tr['want']}"
    b = InlineKeyboardBuilder()
    b.button(text="Удалить предложение", callback_data=f"delete_trade:{tid}")
    b.button(text="◀️ Назад", callback_data="my_trades")
    b.adjust(1)
    await callback.message.edit_text(text, reply_markup=b.as_markup())


@router.callback_query(F.data.startswith("delete_trade:"))
async def delete_trade_handler(callback: CallbackQuery):
    await callback.answer()
    tid = int(callback.data.split(":")[1])
    tr = get_trade_by_id(tid)
    if not tr:
        await callback.answer("Предложение нема", show_alert=True)
        return
    if tr['user_id'] != callback.from_user.id and callback.from_user.id != CREATOR_ID:
        await callback.answer("Это не твое предложение", show_alert=True)
        return
    delete_trade(tid)
    await callback.message.edit_text("Предложение удалено")
    await asyncio.sleep(1)
    await callback.message.edit_text("Твои предложения:", reply_markup=get_user_trades_keyboard(callback.from_user.id))
