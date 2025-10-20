from utilities.database_async import query_card_async, send_task_async, retrieve_tasks_async, get_student_id_async
from utilities.authorizing import is_registered, UserRole
from utilities.keyboard import createInlineTaskButton
from utilities.other import get_file_type
from lexicon import lexicon
from config import ALLOWED_FILE_TYPES
from fsm import Form


import asyncio
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext

router = Router()

@router.message(F.text=="📊 Мой прогресс")
async def my_card(message: Message, state: FSMContext, db):
    username = message.from_user.username
    is_student = await is_registered(username, db, UserRole.STUDENT)
    if is_student:
        username = message.from_user.username
        document = await query_card_async(db, telegram=username)
        if not document:
            await message.answer(text="Студент не найден")

        info = [document['name'],
                document['surname'],
                document['level'],
                document['tasks'],
                document['fine'],
                document['balance']]
        card = lexicon['ru']['general']['card'].format(*info)

        await message.answer(text=card)

@router.message(F.text == "📝 Отправить отчет")
async def sends_tasks(message: Message, state: FSMContext, db):
    username = message.from_user.username
    is_student = await is_registered(username, db, UserRole.STUDENT)
    if is_student:
        await state.set_state(Form.send_report)

        document = await query_card_async(db, telegram=username)
        if not document:
            await message.answer(text="Студент не найден")

        level = str(document.get('level', ''))
        faculty = str(document.get('faculty', ''))

        tasks_dict_of_dicts = await retrieve_tasks_async(db, level, faculty)

        for task_id, task_content in tasks_dict_of_dicts.items():
            keyboard = createInlineTaskButton(task_id)
            info = [
                task_content['number'],
                task_content['block'],
                task_content['content']
            ]

            response = lexicon['ru']['student']['task'].format(*info)

            await message.answer(text=response, reply_markup=keyboard)

@router.callback_query(F.data.startswith("report:"), StateFilter(Form.send_report))
async def send_report(callback: CallbackQuery, state: FSMContext, db):
    task_id = str(callback.data.split(':')[1])
    await state.update_data(task_id=task_id)

    await callback.message.answer('Вышлите Фото/Видео/PDF')

@router.message(F.document, StateFilter(Form.send_report))
async def handle_document(message: Message, state: FSMContext, db):
    file_type = await get_file_type(message)
    if file_type in ALLOWED_FILE_TYPES:
        task_id_dict = await state.get_data()
        task_id = task_id_dict.get('task_id')
        username = message.from_user.username
        document = await query_card_async(db, telegram=username)
        if not document:
            await message.answer(text="Студент не найден")

        student_id = await get_student_id_async(db, username)
        doc = message.document
        file_id = doc.file_id
        file = await message.bot.get_file(file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        file_bytes.seek(0)

        await send_task_async(db, username, task_id, file_bytes, student_id, file_type)
        await message.answer('Ваш ответ сохранен')

    else:
        await message.answer('Бот принимает только фото, видео или pdf.')