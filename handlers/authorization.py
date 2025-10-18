from utilities.keyboard import createAdminPanel, createStudentPanel
from utilities.authorizing import get_role
from lexicon import lexicon
from config import UserRole
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
    role = await get_role(username, db)

    if role == UserRole.CURATOR:
        keyboard = createAdminPanel()
        await message.answer(lexicon['ru']['curator']['greeting'], reply_markup=keyboard, resize_keyboard=True)

    elif role == UserRole.STUDENT:
        keyboard = createStudentPanel()
        await message.answer(lexicon['ru']['student']['greeting'], reply_markup=keyboard, resize_keyboard=True)