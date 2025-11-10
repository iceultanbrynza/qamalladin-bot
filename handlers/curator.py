from utilities.keyboard import (
    createCardKeyboard,
    createAdminPanel,
    assessReport,
    nextKeyboard,
    exitKeyboard,
    addGoodKeyboard,
    addGoodButton,
    createStudentPanel,
    noButton,
    yesnoButton
)
from utilities.database_async import *
from utilities.other import (
    get_dict_with_offset,
    get_file_type
)
from utilities.cloud import get_url
from lexicon import lexicon
from filters import IsInteger, IsFioQcoins, IsFio
from fsm import Form
from utilities.authorizing import is_registered, UserRole
from qutypes import AccrualResult
from utilities.caching import delete_from_redis
from config import LOCAL_TZ

import re
from datetime import datetime
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, User, Chat
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto
from aiogram.types.input_file import URLInputFile
from aiogram.exceptions import TelegramBadRequest

import pandas as pd

router = Router()


# Карточки студентов
@router.message(F.text == '👥 Студенты')
async def get_students(message:Message, state: FSMContext, db):
    start = 0
    username = message.from_user.username
    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.student_card)
        await state.update_data(message_id=message.message_id, start=start)

        data = await query_students_async(db)
        sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
        students = await get_dict_with_offset(sorted_data, start)
        keyboard = createCardKeyboard(students)
        await message.answer('Список карточек студентов:', reply_markup=keyboard)

@router.callback_query(F.data.startswith('find:card'), StateFilter(Form.student_card,
                                                                   Form.student_choosing_for_accrual,
                                                                   Form.accrual,
                                                                   Form.student_choosing_for_fine,
                                                                   Form.fine,
                                                                   Form.get_report,
                                                                   Form.assess_report))
async def find_student(callback: CallbackQuery, state: FSMContext, db):
    # идея такая, мы проверяем в каком состоянии куратор и на основании состояния
    # вызываем нужный хэндлер который делает нужную функцию.
    await callback.message.answer('Введите фамилию и имя студента')
    await callback.answer()

@router.message(F.text, IsFio(), StateFilter(Form.student_card,
                                    Form.student_choosing_for_accrual,
                                    Form.student_choosing_for_fine,
                                    Form.get_report,
                                    Form.assess_report))
async def handle_find_student(message: Message, state: FSMContext, db):
    text = message.text
    try:
        parts = text.strip().split(" ")
        if len(parts) != 2:
            await message.answer('Ошибка в формате. Попробуйте еще раз.')
            return

        surname, name = parts

    except:
        await message.answer('Ошибка в формате. Попробуйте еще раз.')
        return

    student_id = await get_student_id_for_curator_async(db, name, surname)

    if student_id == ProgressResult.DUBLICATE:
        await message.answer('Ошибка, существует как минимум два студента с таким именем. Попробуйте найти нужного студента в списке студентов сверху.')
        return

    elif student_id == ProgressResult.FAILED:
        await message.answer('Ошибка поиска. Попробуйте найти нужного студента в списке сверху.')
        return

    else:
        user_state = await state.get_state()
        bot = message.bot
        message_id = message.message_id
        user = message.from_user
        chat = message.chat
        callback = await generate_callback(bot, message_id, chat, text, user, f"card:{student_id}")
        if user_state == Form.student_card.state:
            if callback:
                await get_card(callback, state, db)
                return

            else:
                await message.answer('Ошибка поиска. Попробуйте найти нужного студента в списке сверху.')
                return

        elif user_state == Form.student_choosing_for_accrual.state:
            if callback:
                await accrual(callback, state, db)
                return

            else:
                await message.answer('Ошибка поиска. Попробуйте найти нужного студента в списке сверху.')
                return

        elif user_state == Form.student_choosing_for_fine.state:
            if callback:
                await fine(callback, state, db)
                return

            else:
                await message.answer('Ошибка поиска. Попробуйте найти нужного студента в списке сверху.')
                return

        elif user_state == Form.assess_report.state or user_state == Form.get_report.state:
            if callback:
                await fetch_report(callback, state, db)
                return

            else:
                await message.answer('Ошибка поиска. Попробуйте найти нужного студента в списке сверху.')
                return


async def generate_callback(bot, message_id, chat, text, user, data):
    try:
        message = Message(
            message_id=message_id,
            date=datetime.now(),
            chat=chat,
            text=text,
            from_user=user
        )
        message._bot = bot

        callback = CallbackQuery(
            id="fake-callback-id",
            from_user=user,
            chat_instance="fake-instance",
            message=message,
            data=data
        )
        callback._bot = bot

        return callback

    except:
        return None

@router.callback_query(F.data.startswith('next:card'), StateFilter(Form.student_card,
                                                                   Form.student_choosing_for_accrual,
                                                                   Form.accrual,
                                                                   Form.student_choosing_for_fine,
                                                                   Form.fine,
                                                                   Form.get_report,
                                                                   Form.assess_report))
async def get_next_students(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    start = data.get('start', None)
    message_id = data.get('message_id', None)
    chat_id = callback.message.chat.id

    if start is None or message_id is None:
        await callback.answer('Истек срок действия функции. Заново выберите команду Студенты.')
        return

    data = await query_students_async(db)
    sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
    students = await get_dict_with_offset(sorted_data, start+1)
    keyboard = createCardKeyboard(students)

    try:
        await callback.message.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id+1, reply_markup=keyboard)
        await state.update_data(start=start+1)
        await callback.answer()

    except TelegramBadRequest:
        await callback.answer("Не нажимайте на кнопки слишком быстро")

@router.callback_query(F.data.startswith('back:card'), StateFilter(Form.student_card,
                                                                   Form.student_choosing_for_accrual,
                                                                   Form.accrual,
                                                                   Form.student_choosing_for_fine,
                                                                   Form.fine,
                                                                   Form.get_report,
                                                                   Form.assess_report))
async def get_previous_students(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    start = data.get('start', '')
    message_id = data.get('message_id', '')
    chat_id = callback.message.chat.id

    if start is None or message_id is None:
        await callback.answer('Истек срок действия функции. Заново выберите команду Студенты.')
        return

    if start>=1:
        data = await query_students_async(db)
        sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
        students = await get_dict_with_offset(sorted_data, start-1)
        keyboard = createCardKeyboard(students)

        try:
            await callback.message.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id+1, reply_markup=keyboard)
            await state.update_data(start=start-1)
            await callback.answer()

        except TelegramBadRequest:
            await callback.answer("Не нажимайте на кнопки слишком быстро")

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.student_card))
async def get_card(callback:CallbackQuery, state: FSMContext, db):
    id = str(callback.data.split(':')[1])

    document:dict = await query_card_async(db, id=id)

    if not document:
        await callback.message.answer(text="Студент не найден")
        return

    level_goal = document.get('goal')
    student_goal = level_goal - document.get('balance-per-level')

    info = [document.get('name'),
            document.get('surname'),
            document.get('level'),
            document.get('tasks'),
            document.get('fine'),
            document.get('balance'),
            student_goal]
    card = lexicon['ru']['general']['card'].format(*info)

    await callback.message.answer(text=card)


# Начисление Qcoins
@router.message(F.text == "💰 Начислить Qcoins")
async def give_coins(message: Message, state: FSMContext, db):
    start=0
    username = message.from_user.username
    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.student_choosing_for_accrual)
        await state.update_data(message_id=message.message_id, start=start)

        data = await query_students_async(db)
        sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
        students = await get_dict_with_offset(sorted_data, start)
        keyboard = createCardKeyboard(students)
        text = lexicon['ru']['curator']['accrual']['give_accrual']
        answer = {
            "text": text,
            "reply_markup": keyboard
        }

        await message.answer(**answer)

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.student_choosing_for_accrual))
async def accrual(callback:CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])
    await state.update_data(student_id=student_id)

    text = lexicon['ru']['curator']['accrual']['enter']
    await callback.message.answer(text=text)
    data = await state.get_data()
    start = data.get('start')
    await state.set_state(Form.accrual)
    await state.update_data(start=start)

@router.message(F.text, IsFioQcoins(), StateFilter(Form.student_choosing_for_accrual))
async def manual_accrual(message: Message, state:FSMContext, db):
    try:
        amount_of_people = len(message.text.split('\n'))

    except:
        await message.answer("Ошибка в формате сообщения. Отправьте заново в последовательности Имя, Фамилия, Количество Qcoins.")

    for i in range(amount_of_people):
        try:
            name, surname, qcoins = message.text.split('\n')[i].split(' ')

        except :
            await message.answer("Ошибка в формате сообщения. Отправьте заново в последовательности Имя, Фамилия, Количество Qcoins.")

        response_state, msg = await write_qcoins_async(int(qcoins), db, mode='fio', name=name, surname=surname)
        await message.answer(text=msg)
        if response_state in (AccrualResult.FAILED, AccrualResult.DUBLICATE, AccrualResult.VALUE_ERROR):
            continue

        student_id = await get_student_id_for_curator_async(db, name, surname)
        chat_id = await get_student_chat_id(db, student_id)
        response = await write_accrual_to_log_async(db, int(qcoins), student_id)
        progress, msg = await is_balance_per_level_enough(db, student_id)
        if chat_id is not None:
            feedback = lexicon["ru"]["student"]["accrual"].format(int(qcoins.group()))
            await message.bot.send_message(chat_id=chat_id, text=feedback)
            if msg is not None:
                await message.bot.send_message(chat_id=chat_id, text=msg)

@router.message(F.text, IsInteger(), StateFilter(Form.accrual))
async def writing_accrual(message: Message, state:FSMContext, db):
    data = await state.get_data()
    student_id = data.get('student_id')
    qcoins = re.search(r"\d+", message.text)

    if not qcoins:
        await message.answer(f"В сообщении нет числа")
        return

    if not student_id:
        await message.answer(f"Истек срок ответа.")
        return

    response_state, msg = await write_qcoins_async(int(qcoins.group()), db, student_id=student_id)
    await message.answer(text=msg)
    log_id = await write_accrual_to_log_async(db, int(qcoins.group()), student_id)
    progress, msg = await is_balance_per_level_enough(db, student_id)
    chat_id = await get_student_chat_id(db, student_id)

    if chat_id is not None:
        feedback = lexicon["ru"]["student"]["accrual"].format(int(qcoins.group()))
        await message.bot.send_message(chat_id=chat_id, text=feedback)
        if msg is not None:
            await message.bot.send_message(chat_id=chat_id, text=msg)

    if log_id and response_state == AccrualResult.SUCCESS:
        text = lexicon['ru']['curator']['accrual']['comment']
        await message.answer(text=text, reply_markup=noButton())
        await state.set_state(Form.comment)
        await state.update_data(log_id=log_id, student_id=student_id)

    else:
        await state.set_state(Form.student_choosing_for_accrual)

@router.message(F.text, StateFilter(Form.comment))
async def comment(message:Message, state:FSMContext, db):
    comment = message.text.strip()
    if len(comment) > 50:
        await message.answer(text="Слишком большой комментарий... Попробуйте еще раз")
        return

    text = f"{comment}"
    await message.answer(text=text, reply_markup=yesnoButton())

@router.callback_query(F.data.startswith('comment:yes'), StateFilter(Form.comment))
async def confirm_comment(callback:CallbackQuery, state:FSMContext, db):
    comment = callback.message.text.strip()
    await state.set_state(Form.student_choosing_for_accrual)
    data = await state.get_data()
    log_id = data.get("log_id", None)
    student_id = data.get('student_id', None)
    if log_id is None or student_id is None:
        await callback.message.answer(f"Истек срок ответа.")
        return

    chat_id = await get_student_chat_id(db, student_id)
    if chat_id is not None:
        text = lexicon['ru']['curator']['log']['comment'].format(comment)
        await callback.bot.send_message(chat_id=chat_id, text=text)

    response = await write_comment_async(db, log_id, comment)
    if response:
        await callback.answer("Комментарий сохранен в логах.")
        await callback.message.delete()

    else:
        await callback.answer("Не получилось сохранить комментарий(")


@router.callback_query(F.data.startswith('comment:no'), StateFilter(Form.comment))
async def deny_comment(callback:CallbackQuery, state:FSMContext, db):
    await callback.message.delete()
    await callback.answer("Напишите новый комментарий")

@router.callback_query(F.data.startswith('comment:skip'), StateFilter(Form.comment))
async def skip_commenting(callback:CallbackQuery, state:FSMContext, db):
    await state.set_state(Form.student_choosing_for_accrual)
    await callback.message.delete()
    await callback.answer()

# Выдача штрафов
@router.message(F.text=='🚫 Выдать штраф')
async def give_fine(message: Message, state: FSMContext, db):
    start = 0
    username = message.from_user.username
    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.student_choosing_for_fine)
        await state.update_data(message_id=message.message_id, start=start)

        data = await query_students_async(db)
        sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
        students = await get_dict_with_offset(sorted_data, start)
        keyboard = createCardKeyboard(students)
        await message.answer('Выберите студента, которого необходимо оштрафовать или наберите ФИО вручную по шаблону "Имя Фамилия Qcoins" (можно начислить сразу нескольким, написав через Enter)', reply_markup=keyboard)

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.student_choosing_for_fine))
async def fine(callback:CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])

    await callback.message.answer("Введите штраф (количество Qcoins):")
    data = await state.get_data()
    start = data.get('start')
    await state.set_state(Form.fine)
    await state.update_data(start=start, student_id=student_id)

@router.message(F.text, IsFioQcoins(), StateFilter(Form.student_choosing_for_fine))
async def manual_fine(message: Message, state:FSMContext, db):
    try:
        amount_of_people = len(message.text.split('\n'))

    except:
        await message.answer("Ошибка в формате сообщения. Отправьте заново в последовательности Имя, Фамилия, Количество Qcoins.")

    for i in range(amount_of_people):
        name, surname, qcoins = message.text.split('\n')[i].split(' ')
        response_state, msg = await write_qcoins_async(-int(qcoins), db, mode='fio', name=name, surname=surname)
        await message.answer(text=msg)
        if response_state in (AccrualResult.FAILED, AccrualResult.DUBLICATE, AccrualResult.VALUE_ERROR):
            continue
        
        await add_fine_async(db, mode='fio', name=name, surname=surname)
        student_id = await get_student_id_for_curator_async(db, name, surname)
        if student_id:
            log_id = await write_accrual_to_log_async(db, -int(qcoins), student_id)
            chat_id = await get_student_chat_id(db, student_id)

            if chat_id is not None:
                feedback = lexicon["ru"]["student"]["fine"].format(int(qcoins.group()))
                await message.bot.send_message(chat_id=chat_id, text=feedback)

@router.message(F.text, IsInteger(), StateFilter(Form.fine))
async def writing_fine(message: Message, state:FSMContext, db):
    data = await state.get_data()
    student_id = data['student_id']
    qcoins = re.search(r"\d+", message.text)

    if not qcoins:
        await message.answer(f"В сообщении нет числа")
        return

    if not student_id:
        await message.answer(f"Истек срок ответа.")
        return

    response_state, msg = await write_qcoins_async(-int(qcoins.group()), db, student_id=student_id)
    await message.answer(text=msg)
    await add_fine_async(db, student_id=student_id)
    log_id = await write_accrual_to_log_async(db, -int(qcoins.group()), student_id)
    chat_id = await get_student_chat_id(db, student_id)

    if chat_id is not None:
        feedback = lexicon["ru"]["student"]["fine"].format(int(qcoins.group()))
        await message.bot.send_message(chat_id=chat_id, text=feedback)

    if log_id and response_state == AccrualResult.SUCCESS:
        text = lexicon['ru']['curator']['accrual']['comment']
        await message.answer(text=text, reply_markup=noButton())
        await state.set_state(Form.comment)
        await state.update_data(log_id=log_id, student_id=student_id)

    else:
        await state.set_state(Form.student_choosing_for_accrual)

@router.message(F.text, StateFilter(Form.comment))
async def comment(message:Message, state:FSMContext, db):
    comment = message.text.strip()
    if len(comment) > 100:
        await message.answer(text="Слишком большой комментарий... Попробуйте еще раз")
        return

    text = f"{comment}"
    await message.answer(text=text, reply_markup=yesnoButton())

@router.callback_query(F.data.startswith('comment:yes'), StateFilter(Form.comment))
async def confirm_comment(callback:CallbackQuery, state:FSMContext, db):
    comment = callback.message.text.strip()
    await state.set_state(Form.student_choosing_for_accrual)
    data = await state.get_data()
    log_id = data.get("log_id", None)
    student_id = data.get('student_id', None)
    if log_id is None or student_id is None:
        await callback.message.answer(f"Истек срок ответа.")
        return

    chat_id = await get_student_chat_id(db, student_id)
    if chat_id is not None:
        text = lexicon['ru']['curator']['log']['comment'].format(comment)
        await callback.bot.send_message(chat_id=chat_id, text=text)

    response = await write_comment_async(db, log_id, comment)
    if response:
        await callback.answer("Комментарий сохранен в логах.")
        await callback.message.delete()

    else:
        await callback.answer("Не получилось сохранить комментарий(")


@router.callback_query(F.data.startswith('comment:no'), StateFilter(Form.comment))
async def deny_comment(callback:CallbackQuery, state:FSMContext, db):
    await callback.message.delete()
    await callback.answer("Напишите новый комментарий")

@router.callback_query(F.data.startswith('comment:skip'), StateFilter(Form.comment))
async def skip_commenting(callback:CallbackQuery, state:FSMContext, db):
    await state.set_state(Form.student_choosing_for_accrual)
    await callback.message.delete()
    await callback.answer()

# Смотреть отчеты студентов
@router.message(F.text == "📈 Отчеты")
async def get_report(message: Message, state: FSMContext, db):
    start = 0
    username = message.from_user.username
    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.get_report)
        await state.update_data(message_id=message.message_id, start=start)
        data = await query_students_async(db)
        sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
        students = await get_dict_with_offset(sorted_data, start)
        keyboard = createCardKeyboard(students)
        await message.answer(lexicon['ru']['curator']['Curator asks to get report'], reply_markup=keyboard)

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.get_report,
                                                               Form.assess_report))
async def fetch_report(callback: CallbackQuery, state:FSMContext, db):
    await state.set_state(Form.assess_report)
    student_id = str(callback.data.split(':')[1])
    chat_id = callback.message.chat.id
    reports = await retrieve_report_async(db, student_id)
    if not reports:
        await callback.message.answer('У пользователя нет непроверенных заданий')
        return

    for task_id, content in reports.items():
        is_checked = content.pop('is_checked', None)
        text = lexicon['ru']['curator']['Curator obtained report'].format(task_id, is_checked)
        keyboard = assessReport(student_id, task_id)

        answer = {}
        answer['text'] = text
        answer['reply_markup'] = keyboard

        await callback.message.answer(**answer)

        for key, value in content.items():
            tz = pytz.timezone("Asia/Almaty")
            data = datetime.now(tz).strftime("%d/%m/%Y_%H:%M:%S")
            if value[1] in ['jpg', 'jpeg', 'png']:
                file = URLInputFile(url=value[0], filename=f"{data}.png")
                await callback.bot.send_document(chat_id, file)

            elif value[1] in ['mp4', 'mov']:
                file = URLInputFile(url=value[0], filename=f"{data}.mp4")
                await callback.bot.send_document(chat_id, file)

            elif value[1] in ['pdf']:
                await callback.bot.send_document(chat_id, URLInputFile(url=value[0], filename=f'{data}.pdf'))

            elif value[1]=='heic':
                await callback.bot.send_document(chat_id, URLInputFile(url=value[0], filename=f'{data}.heic'))

@router.callback_query(F.data.startswith('assess:'), StateFilter(Form.assess_report))
async def assess(callback:CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])
    task_id = str(callback.data.split(':')[2])
    task_message_id = callback.message.message_id

    await state.update_data(student_id=student_id, task_message_id=task_message_id, task_id=task_id)

    await callback.message.answer("Введите количество баллов для этого студента:")
    await callback.answer()

@router.callback_query(F.data.startswith('fail:'), StateFilter(Form.assess_report))
async def give_back_report(callback:CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])
    task_id = str(callback.data.split(':')[2])
    await delete_task_async(db, student_id, task_id)
    chat_id = await get_student_chat_id(db, student_id)

    await callback.answer("Студенту возвращено задание")
    await callback.message.bot.send_message(chat_id=chat_id, text=f"Куратор вернул Вашу задачу {task_id}, поскольку посчитал, что Вы сделали ее не до конца.")

@router.message(F.text, IsInteger(), StateFilter(Form.assess_report))
async def writing_assess(message: Message, state:FSMContext, db):
    chat_id = message.chat.id
    data = await state.get_data()
    student_id = data['student_id']
    task_id = data['task_id']
    message_id = data['task_message_id']
    qcoins = re.search(r"\d+", message.text)

    text = lexicon['ru']['curator']['Curator obtained report'].format(task_id, 'True')
    await message.bot.edit_message_text(chat_id=chat_id, text=text, message_id=message_id, reply_markup=None)

    response_state, msg = await write_qcoins_async(int(qcoins.group()), db, student_id=student_id)
    await message.answer(text=msg)

    if response_state == AccrualResult.SUCCESS:
        await mark_as_checked_async(db, student_id, task_id)
        await write_accrual_to_log_async(db, int(qcoins.group()), student_id, task_id)
        progress, msg = await is_balance_per_level_enough(db, student_id)
        chat_id = await get_student_chat_id(db, student_id)
        if msg is not None:
            await message.bot.send_message(chat_id=chat_id, text=msg)


# Логгирование
@router.message(F.text == '🗒️ Лог действий')
async def get_log(message: Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.get_log)
        response = await get_log_async(db)
        last_timestamp = response.get('last_timestamp')
        if last_timestamp is not None:
            last_timestamp = last_timestamp.isoformat()
        await state.update_data(last_timestamp=last_timestamp)

        logs = response.get('logs')
        if logs:
            text = await get_log_text(logs)
            keyboard = nextKeyboard()
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

        else:
            await message.answer(text="Логов еще нет")

@router.callback_query(F.data.startswith('next:logs'), StateFilter(Form.get_log))
async def get_next_log(callback:CallbackQuery, state:FSMContext, db):
    data = await state.get_data()
    last_timestamp = data.get('last_timestamp')

    if not last_timestamp:
        await callback.answer('Ошибка. Вернитесь на главное меню')
        return

    last_timestamp = datetime.fromisoformat(last_timestamp)

    response = await get_log_async(db, last_timestamp=last_timestamp)

    text = await parse_log(response, state)

    keyboard = nextKeyboard()

    if text is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

    else:
        await callback.answer("Логи закончились")

async def parse_log(response, state):
    last_timestamp = response.get('last_timestamp')
    if last_timestamp:
        last_timestamp = last_timestamp.isoformat()
    await state.update_data(last_timestamp=last_timestamp)

    logs = response.get('logs')

    if not logs:
        return None

    return await get_log_text(logs)

async def get_log_text(logs):
    text = ""
    for log in logs:
        student = log.get('student').get()

        if student.to_dict() is None:
            student_name = "Неизвестный студент"

        else:
            student_data = student.to_dict()  # извлекаем словарь
            name = student_data.get('name')
            surname = student_data.get('surname')
            student_name = name + " " + surname

        created_at = log.get('created_at')
        dt = datetime.fromisoformat(str(created_at))
        time = dt.strftime("%d %B %Y, %H:%M:%S")
        task_id = log.get('task_id', None)
        accrual = log.get('accrual', None)
        good = log.get('good_id', None)
        comment = log.get("comment", None)
        if task_id is not None:
            text += lexicon['ru']['curator']['log']['report'].format(time, student_name, task_id)

            if accrual is not None:
                accrualed_at = log.get('accrualed_at')
                dt = datetime.fromisoformat(str(accrualed_at))
                if dt.tzinfo is None:
                    dt = LOCAL_TZ.localize(dt)
                else:
                    dt = dt.astimezone(LOCAL_TZ)
                accrualed_time = dt.strftime("%d %B %Y, %H:%M:%S")
                text += ". "
                text += lexicon['ru']['curator']['accrual']['logging'].format(accrualed_time, student_name, accrual)

        elif accrual is not None:
            accrualed_at = log.get('accrualed_at')
            dt = datetime.fromisoformat(str(accrualed_at))

            if dt.tzinfo is None:
                    dt = LOCAL_TZ.localize(dt)
            else:
                dt = dt.astimezone(LOCAL_TZ)

            accrualed_time = dt.strftime("%d %B %Y, %H:%M:%S")
            if accrual > 0:
                text += lexicon['ru']['curator']['accrual']['logging'].format(accrualed_time, student_name, accrual)

            elif accrual < 0:
                text += lexicon['ru']['curator']['fine']['logging'].format(accrualed_time, student_name, accrual*-1)

        elif good is not None:
            desc = await get_good_desc_async(student_name, good, time)
            if desc is not None:
                text+=desc

            else:
                continue

        else:
            continue

        if comment is not None:
            text += ". "
            text+=lexicon['ru']['curator']['log']['comment'].format(comment)

        text+='\n'
    if text:
        text="<pre>"+text+"</pre>"
    return text


# Добавление новых студентов
@router.message(F.text == '👨‍🎓 Добавить студентов')
async def add_students(message: Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        message_id = message.message_id
        await state.set_state(Form.add_students)
        await state.update_data(message_id=message_id)
        text = lexicon['ru']['curator']['add student response']
        keyboard = exitKeyboard()
        answer = {
            "text": text,
            "reply_markup": keyboard
        }
        await message.answer(**answer)

@router.message(F.text, StateFilter(Form.add_students))
async def handle_text(message: Message, state:FSMContext, db):
    students = message.text
    await adding_students(message, students, db)

@router.message(F.document, StateFilter(Form.add_students))
async def handle_document(message: Message, state:FSMContext, db):
    document = message.document
    file_type = await get_file_type(message)
    file = await message.bot.download(document)
    students = ""
    error = 0
    if file_type == 'excel':
        try:
            df = pd.read_excel(file)
            preview = df.head().to_string()
            await message.answer(f"✅ Файл получен!\n\nПервые строки:\n<pre>{preview}</pre>", parse_mode="HTML")

            for index, row in df.iterrows():
                fio = row['ФИО']
                faculty = row['Направление']
                telegram = row['Телеграм']

                if pd.notna(fio) and pd.notna(faculty) and pd.notna(telegram):
                    fio = str(fio).strip()
                    faculty = str(faculty).strip()
                    telegram = str(telegram).strip()

                    if telegram.strip().startswith('@'):
                        telegram = telegram[1:]

                    row = fio + " " + faculty + " " + telegram + "\n"
                    students += row

                elif pd.isna(fio) and pd.isna(faculty) and pd.isna(telegram):
                    continue

                else:
                    error+=1
                    continue

        except Exception as e:
            await message.answer(f"⚠️ Ошибка при чтении файла:\n{e}")

        await message.answer(f"Строк с неправильным форматом обнаружено: {error}. Если ошибки есть, то загрузка студентов будет остановлена.")

        if error == 0:
            await adding_students(message, students, db)

async def adding_students(message, students, db):
    success = await add_students_async(db, students)

    if success:
        await delete_from_redis_by_group("students_tags")
        await delete_from_redis_by_group("students")
        await rewrite_cached_students(db)
        text = lexicon['ru']['curator']['add student']

    else:
        text = lexicon['ru']['curator']['didnt add student']

    await message.answer(text)

@router.message(F.text=='/updateLevels')
async def updateLevels(message:Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.update_levels)
        await message.answer('Скиньте список уровней в таком виде: Уровень (1,2,3...) Титул Лига Цель (количество Qcoins для перехода на следующий уровень) построчно (каждый уровень начинается с новой строки) и без запятых')

@router.message(F.text, StateFilter(Form.update_levels))
async def handle_text(message: Message, db):
    text = message.text
    success = await add_levels_async(db, text)

    if success:
        text = lexicon['ru']['curator']['add levels']

    else:
        text = lexicon['ru']['curator']['didnt add levels']

    await message.answer(text)

@router.message(F.text.startswith('/addCurator'))
async def addCurator(message:Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        args = message.text.split()
        if len(args) != 4:
            await message.answer("Использование: /addCurator Фамилия Имя телеграм-тэг")
            return

        surname = str(args[1])
        name = str(args[2])
        telegram = str(args[3])

        response = await add_curator_async(db, surname, name, telegram)

        if response:
            await message.answer("Куратор добавлен")

        else:
            await message.answer("Ошибка. Не получилось создать куратора")

@router.message(F.text.startswith('/deleteCurator'))
async def deleteCurator(message:Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Использование: /deleteCurator телеграм-тэг")
            return

        telegram = str(args[1])

        response = await delete_curator_async(db, telegram)

        if response:
            await message.answer("Куратор удален")

        else:
            await message.answer("Ошибка. Не получилось удалить куратора")

@router.message(F.text.startswith('/deleteStudent'))
async def deleteStudent(message:Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        args = message.text.split()
        if len(args) != 2:
            await message.answer("Использование: /deleteStudent телеграм-тэг")
            return

        telegram = str(args[1])

        response = await delete_student_async(db, telegram)

        if response:
            await message.answer("Студент удален")

        else:
            await message.answer("Ошибка. Не получилось удалить студента")


# Добавление новых задач
@router.message(F.text == '📥 Добавить задачу')
async def add_tasks(message: Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        message_id = message.message_id
        await state.set_state(Form.add_tasks)
        await state.update_data(message_id=message_id)
        text = lexicon['ru']['curator']['add task response']
        keyboard = exitKeyboard()
        answer = {
            "text": text,
            "reply_markup": keyboard
        }
        await message.answer(**answer)

@router.message(F.document, StateFilter(Form.add_tasks))
async def handle_document(message: Message, state:FSMContext, db):
    document = message.document
    file_type = await get_file_type(message)
    file = await message.bot.download(document)
    tasks = []
    if file_type == 'excel':
        try:
            df = pd.read_excel(file)
            preview = df.head().to_string()
            await message.answer(f"✅ Файл получен!\n\nПервые строки:\n<pre>{preview}</pre>", parse_mode="HTML")

            for index, row in df.iterrows():
                faculty = row['Факультет']
                level = row['Уровень']
                block = row['Блок']
                number = row['Номер']
                content = row['Контент']

                if (pd.notna(level) and
                    pd.notna(faculty) and
                    pd.notna(block) and
                    pd.notna(number) and
                    pd.notna(content)):

                    tasks.append(add_task_async(db, faculty, level, block, number, content))

                elif (pd.isna(level) and
                      pd.isna(faculty) and
                      pd.isna(block) and
                      pd.isna(number) and
                      pd.isna(content)):
                    continue

                else:
                    for t in tasks:
                        t.close()
                    await message.answer(f"⚠️ Ошибка при чтении файла:\n")
                    return

        except Exception as e:
            await message.answer(f"⚠️ Ошибка при чтении файла:\n{e}")
            return

        await asyncio.gather(*tasks)
        text = lexicon['ru']['curator']['add tasks']
        await message.answer(text)


# Магазин
@router.message(F.text == "🏪 Управление магазином")
async def shop_manager(message: Message, state: FSMContext, db):
    pos = 0
    username = message.from_user.username
    message_id = message.message_id
    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.add_goods)
        await state.update_data(message_id=message_id, pos=pos)
        good:tuple = await qyery_good(db,pos)

        if good:
            good_id, name, description, price, photo = await parse_good(good)
            keyboard = addGoodKeyboard(good_id)
            caption = lexicon['ru']['curator']['shop'].format(name, price, description)
            if photo:
                photo_url = get_url(photo)
                await message.answer_photo(photo=photo_url[0], caption=caption, reply_markup=keyboard)
                return

        else:
            keyboard = addGoodButton()
            await message.answer("Магазин пустует...", reply_markup=keyboard)

@router.callback_query(F.data.startswith('next:shop'), StateFilter(Form.add_goods))
async def get_next_good(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    pos = int(data.get('pos', ''))
    message_id = data.get('message_id', '')

    if pos == '' or message_id == '':
        await callback.message.answer('Вы не можете использовать эту функцию')
        return False

    good = await qyery_good(db, pos+1)
    if good:
        await state.update_data(pos=pos+1)
        good_id, name, description, price, photo = await parse_good(good)
        keyboard = addGoodKeyboard(good_id)
        caption = lexicon['ru']['curator']['shop'].format(name, price, description)
        if photo:
            photo_url = get_url(photo)
            media = InputMediaPhoto(media=photo_url[0], caption=caption)
            await callback.message.edit_media(media=media, reply_markup=keyboard)

        return True

    else:
        await callback.answer("Больше товаров нет")
        return False

@router.callback_query(F.data.startswith('back:shop'), StateFilter(Form.add_goods))
async def get_prev_good(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    pos = int(data.get('pos', ''))
    message_id = data.get('message_id', '')

    if pos == '' or message_id == '':
        await callback.message.answer('Вы не можете использовать эту функцию')
        return False

    good = await qyery_good(db, pos-1)
    if good:
        await state.update_data(pos=pos-1)
        good_id, name, description, price, photo = await parse_good(good)
        keyboard = addGoodKeyboard(good_id)
        caption = lexicon['ru']['curator']['shop'].format(name, price, description)
        if photo:
            photo_url = get_url(photo)
            media = InputMediaPhoto(media=photo_url[0], caption=caption)
            await callback.message.edit_media(media=media, reply_markup=keyboard)
        return True

    else:
        await callback.answer("Больше товаров нет")
        return False


async def parse_good(good:tuple):
    data:dict = good[1]
    id = good[0]
    name = data.get("name", "Товар")
    description = data.get("description", None)
    price = data.get("price", 0)
    photo = data.get("photo", None)
    return id, name, description, price, photo

@router.callback_query(F.data.startswith("add:shop"), StateFilter(Form.add_goods))
async def adds_good(callback: CallbackQuery, state: FSMContext, db):
    message_id=callback.message.message_id
    await state.update_data(message_id=message_id)
    await callback.message.answer("Создайте товар. За раз создается один товар. Формат: Название на первой строке, Цена - на второй, Описание - на третьей, фото. Отправьте и текст, и фото одним сообщением, иначе товар не получится создать.", reply_markup=exitKeyboard())

@router.message(F.photo, StateFilter(Form.add_goods))
async def adding_good(message: Message, state: FSMContext, db):
    photo = message.photo[-1].file_id
    file = await message.bot.get_file(photo)
    file_path = file.file_path
    caption = message.caption
    response = await uploading_goods(db, message, file_path, caption)
    await rewrite_cached_goods(db)

    if response:
        await message.answer("Товар успешно сохранен!")

async def uploading_goods(db, message, file_path, caption):
    try:
        parts = caption.split('\n')
        if len(parts) != 3:
            await message.answer(f"Ошибка: нарушен формат")
            return False
        tz = pytz.timezone("Asia/Almaty")
        current_time = datetime.now(tz)
        public_id = str(current_time.strftime("%Y%m%d_%H%M%S"))

        data = {
            "name": parts[0],
            "price": int(parts[1]),
            "description": parts[2],
            "photo": public_id
        }
        file_bytes = await message.bot.download_file(file_path)
        file_bytes.seek(0)

        response = await upload_goods_async(db, data, file_bytes, public_id)
        await rewrite_cached_goods(db)
        return response

    except ValueError as e:
        await message.answer(f"Ошибка: нарушен формат \n{e}")
        return False

    except:
        return False

@router.callback_query(F.data.startswith("delete:"), StateFilter(Form.add_goods))
async def delete_good(callback: CallbackQuery, state: FSMContext, db):
    good_id = callback.data.split(":")[1]
    message_id=callback.message.message_id
    await state.update_data(message_id=message_id)
    response = await delete_good_async(db, good_id)

    if response:
        await delete_from_redis("shop", good_id)
        got = await get_next_good(callback, state, db)
        if not got:
            got_prev = await get_prev_good(callback, state, db)

            if not got_prev:
                await callback.message.delete()

        text = lexicon['ru']['curator']["deletion"]
        await callback.message.answer(text=text)
        await callback.answer()

    else:
        text = lexicon['ru']['curator']["error deletion"]
        await callback.message.answer(text=text)
        await callback.answer()


# Выход
@router.callback_query(F.data.startswith('exit'))
async def exit(callback: CallbackQuery, state:FSMContext, db):
    username = callback.from_user.username
    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        keyboard = createAdminPanel()

    else:
        keyboard = createStudentPanel()

    data = await state.get_data()
    message_id = data.get('message_id', None)

    if message_id is not None:
        chat_id = callback.message.chat.id

        try:
            await callback.message.bot.delete_message(chat_id=chat_id, message_id=message_id)
            await callback.message.bot.delete_message(chat_id=chat_id, message_id=message_id+1)

        except:
            pass

    await callback.message.answer(text='Вы вышли.', reply_markup=keyboard)
    await callback.answer()

    await state.clear()

# Куратор не находится в состоянии, но использует кнопки
@router.callback_query(F.data.startswith('card:'), StateFilter(None))
async def callback_no_state(callback:CallbackQuery, state:FSMContext, db):
    await callback.answer('Выберите действие')
