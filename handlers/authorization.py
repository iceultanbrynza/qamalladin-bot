from utilities.keyboard import createAdminPanel, createStudentPanel
from utilities.authorizing import get_role
from utilities.database_async import record_chat_id_async, rewrite_cached_students
from lexicon import lexicon
from config import (
    UserRole,
    CURATORS_CHAT_ID
)
from fsm import Form

import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(CommandStart())
async def start(message:Message, state: FSMContext, db):
    username = message.from_user.username
    chat_id = message.chat.id
    role = await get_role(username, db)

    if role == UserRole.CURATOR:
        if message.chat.id not in CURATORS_CHAT_ID:
            CURATORS_CHAT_ID.append(message.chat.id)
        keyboard = createAdminPanel()
        await message.answer(lexicon['ru']['curator']['greeting'], reply_markup=keyboard, resize_keyboard=True)

    elif role == UserRole.STUDENT:
        keyboard = createStudentPanel()
        await message.answer(lexicon['ru']['student']['greeting'], reply_markup=keyboard, resize_keyboard=True)

    await record_chat_id_async(db, username, role, chat_id)
    await rewrite_cached_students(db)