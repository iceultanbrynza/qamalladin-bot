from filters import IsAdmin
from utilities.keyboard import createStudentPanel
from utilities.database_async import query_students_tags_async
from config import redis_client
from lexicon import lexicon

import json

from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.text=='/makeMeStudent', IsAdmin())
async def makeMeStudent(message:Message, db):
    await query_students_tags_async(db)
    keyboard = createStudentPanel()

    await redis_client.rpush("students_tags", *[json.dumps(message.from_user.username)]) # since all commands can be executed if and only if person is registered as a student
    await message.answer(lexicon['ru']['student']['greeting'], reply_markup=keyboard, resize_keyboard=True)