import asyncio
from typing import Dict, Any, Callable, Awaitable

from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import Message, CallbackQuery

import database
from offer import init_offers_db
from trade import init_trades_db

import codes
import families
import guide
import memories
import perks
import admin
import offer
import trade

BOT_TOKEN = "8377727368:AAHUmJu_dUSJ-ZmwDWHP4mNdtvQNP39kRZM"
CREATOR_ID = 7306010609

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


class TrackUsersMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        if event.from_user:
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
            await event.answer("Чат не верифицирован", show_alert=True)
            return
        return await handler(event, data)


dp.message.middleware(TrackUsersMiddleware())
dp.callback_query.middleware(CheckVerificationMiddleware())


def init_all_dbs():
    database.init_users_db()
    database.init_chats_db()
    database.init_sessions_db()
    init_offers_db()
    init_trades_db()


@dp.message(Command("AotrOn"))
async def cmd_verification_on(message: Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        return
    database.add_verified_chat(message.chat.id, message.chat.title or "Личный чат")
    await message.answer("✅ Чат верифицирован.")


@dp.message(Command("AotrOff"))
async def cmd_verification_off(message: Message):
    if message.from_user.id != CREATOR_ID:
        await message.answer("Нет прав.")
        return
    database.remove_verified_chat(message.chat.id)
    await message.answer("❌ Верификация отключена.")


@dp.message(Command("start_aotrcode"))
async def start_handler(message: Message):
    await message.answer("Бот активен все збс.")


# Подключаем роутеры модулей
dp.include_router(codes.router)
dp.include_router(families.router)
dp.include_router(guide.router)
dp.include_router(memories.router)
dp.include_router(perks.router)
dp.include_router(admin.router)
dp.include_router(offer.router)
dp.include_router(trade.router)


async def main():
    init_all_dbs()
    print("Бот запущен...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
