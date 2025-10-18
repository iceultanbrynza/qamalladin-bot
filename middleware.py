from utilities.authorizing import get_role, UserRole
from fsm import Form

import asyncio

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, message:Message, data:dict):
        username = message.from_user.username
        state: FSMContext = data.get('state')

        current_state = await state.get_state()

        if current_state is None:
            db = data['db']

            role = await get_role(username, db)

            if role == UserRole.CURATOR:
                await state.set_state(Form.curator)

            elif role == UserRole.STUDENT:
                await state.set_state(Form.student)

            elif role == UserRole.GUEST:
                await message.answer("Вы не зарегистрированы. Если Вы являетесь студентом QU, обратитесь к куратору по этому вопросу.")

        return await handler(message, data)