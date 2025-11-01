from utilities.keyboard import (
    createCardKeyboard,
    createAdminPanel,
    assessReport,
    nextKeyboard,
    exitKeyboard
)
from utilities.database_async import (
    query_students_async,
    query_card_async,
    write_qcoins_async,
    retrieve_report_async,
    mark_as_checked_async,
    get_log_async,
    add_fine_async,
    add_students_async,
    is_balance_per_level_enough,
    add_levels_async,
    rewrite_cached_students,
    add_task_async
)
from utilities.other import (
    get_dict_with_offset,
    get_file_type
)
from lexicon import lexicon
from filters import IsInteger, IsFioQcoins
from fsm import Form
from utilities.authorizing import is_registered, UserRole

import re
from datetime import datetime
import asyncio

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InputMediaPhoto,
    InputMediaVideo
)
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

@router.callback_query(F.data.startswith('next:card'), StateFilter(Form.student_card,
                                                                   Form.student_choosing_for_accrual,
                                                                   Form.accrual,
                                                                   Form.student_choosing_for_fine,
                                                                   Form.fine,
                                                                   Form.get_report,
                                                                   Form.assess_report))
async def get_next_students(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    start = int(data.get('start', ''))
    message_id = data.get('message_id', '')

    if start == '' or message_id == '':
        callback.message.answer('Вы не можете использовать эту функцию')
        return

    data = await query_students_async(db)
    sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
    students = await get_dict_with_offset(sorted_data, start+1)
    keyboard = createCardKeyboard(students)

    chat_id = callback.message.chat.id

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
    start = int(data.get('start', ''))
    message_id = data.get('message_id', '')

    if start == '' or message_id == '':
        callback.message.answer('Вы не можете использовать эту функцию')
        return

    if start>=1:
        data = await query_students_async(db)
        sorted_data = dict(sorted(data.items(), key=lambda item: item[1]['surname']))
        students = await get_dict_with_offset(sorted_data, start-1)
        keyboard = createCardKeyboard(students)

        chat_id = callback.message.chat.id
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

    info = [document['name'],
            document['surname'],
            document['level'],
            document['tasks'],
            document['fine'],
            document['balance']]
    card = lexicon['ru']['general']['card'].format(*info)

    await callback.message.answer(text=card)
    await callback.answer()


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
    await callback.answer()

@router.message(F.text, IsFioQcoins(), StateFilter(Form.student_choosing_for_accrual))
async def manual_accrual(message: Message, state:FSMContext, db):
    amount_of_people = len(message.text.split('\n'))
    for i in range(amount_of_people):
        name, surname, qcoins = message.text.split('\n')[i].split(' ')
        await write_qcoins_async(int(qcoins), db, mode='fio', name=name, surname=surname)

        await message.answer(f"✅ Начислено {qcoins} Qcoins студенту {name} {surname}")

@router.message(F.text, IsInteger(), StateFilter(Form.accrual))
async def writing_accrual(message: Message, state:FSMContext, db):
    data = await state.get_data()
    student_id = data['student_id']
    qcoins = re.search(r"\d+", message.text)

    if not qcoins:
        await message.answer(f"В сообщении нет числа")
    await write_qcoins_async(int(qcoins.group()), db, student_id=student_id)
    progress, msg = await is_balance_per_level_enough(db, student_id)

    if msg is not None:
        await message.answer(text=msg)

    await message.answer(f"✅ Начислено {int(qcoins.group())} Qcoins студенту {student_id}")
    await state.set_state(Form.student_choosing_for_accrual)

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

    await state.update_data(student_id=student_id)

    await callback.message.answer("Введите штраф (количество Qcoins):")
    data = await state.get_data()
    start = data.get('start')
    await state.set_state(Form.fine)
    await state.update_data(start=start)
    await callback.answer()

@router.message(F.text, IsFioQcoins(), StateFilter(Form.student_choosing_for_fine))
async def manual_fine(message: Message, state:FSMContext, db):
    amount_of_people = len(message.text.split('\n'))
    for i in range(amount_of_people):
        name, surname, qcoins = message.text.split('\n')[i].split(' ')
        await write_qcoins_async(-int(qcoins), db, mode='fio', name=name, surname=surname)
        await add_fine_async(db, mode='fio', name=name, surname=surname)

        await message.answer(f"✅ Студент {name} {surname} оштрафован на {qcoins}")

@router.message(F.text, IsInteger(), StateFilter(Form.fine))
async def writing_fine(message: Message, state:FSMContext, db):
    data = await state.get_data()
    student_id = data['student_id']
    qcoins = re.search(r"\d+", message.text)

    if not qcoins:
        await message.answer(f"В сообщении нет числа")
    await write_qcoins_async(-int(qcoins.group()), db, student_id=student_id)
    await add_fine_async(db, student_id=student_id)
    await message.answer(f"✅ Студент {student_id} оштрафован на {int(qcoins.group())}")
    await state.set_state(Form.student_choosing_for_fine)


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
        await callback.answer('У пользователя нет непроверенных заданий')
        return

    for task_id, content in reports.items():
        answer = {}
        is_checked = content.pop('is_checked', None)

        text = lexicon['ru']['curator']['Curator obtained report'].format(task_id, is_checked)

        answer['text'] = text
        keyboard = assessReport(student_id, task_id)
        answer['reply_markup'] = keyboard

        await callback.message.answer(**answer)

        media = []
        for key, value in content.items():
            if value[1] in ['jpg', 'jpeg', 'png']:
                file = InputMediaPhoto(media=value[0])
                media.append(file)
            elif value[1] in ['mp4', 'mov']:
                file = InputMediaVideo(media=value[0])
                media.append(file)
            elif value[1] in ['pdf']:
                await callback.bot.send_document(chat_id, URLInputFile(url=value[0], filename='document.pdf'))
            elif value[1]=='heic':
                await callback.bot.send_document(chat_id, URLInputFile(url=value[0], filename='photo.heic'))
        if media:
            for i in range(0, len(media), 10):
                await callback.bot.send_media_group(chat_id, media[i:i+10])

@router.callback_query(F.data.startswith('assess:'), StateFilter(Form.assess_report))
async def assess(callback:CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])
    task_id = str(callback.data.split(':')[2])
    task_message_id = callback.message.message_id

    await state.update_data(student_id=student_id, task_message_id=task_message_id, task_id=task_id)

    await callback.message.answer("Введите количество баллов для этого студента:")
    await callback.answer()

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

    await write_qcoins_async(int(qcoins.group()), db, student_id=student_id)
    await mark_as_checked_async(db, student_id, task_id)
    progress, msg = await is_balance_per_level_enough(db, student_id)

    if msg is not None:
        await message.answer(text=msg)

    await message.answer(f"✅ Начислено {int(qcoins.group())} Qcoins студенту {student_id}")


# Логгирование
@router.message(F.text == '🗒️ Лог действий')
async def get_log(message: Message, state:FSMContext, db):
    username = message.from_user.username

    is_curator = await is_registered(username, db, UserRole.CURATOR)

    if is_curator:
        await state.set_state(Form.get_log)
        response = await get_log_async(db)
        last_timestamp = response.get('last_timestamp')
        if last_timestamp:
            last_timestamp = last_timestamp.isoformat()
        await state.update_data(last_timestamp=last_timestamp)

        logs = response.get('logs')
        if logs:
            text = await get_log_text(logs)

        keyboard = nextKeyboard()

        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith('next:logs'), StateFilter(Form.get_log))
async def get_next_log(callback:CallbackQuery, state:FSMContext, db):
    data = await state.get_data()
    last_timestamp = data.get('last_timestamp')

    if not last_timestamp:
        await callback.answer('Ошибка. Вернитесь на главное меню')
        return

    last_timestamp = datetime.fromisoformat(last_timestamp)

    response = await get_log_async(db, last_timestamp)

    text = await parse_log(response, state)

    keyboard = nextKeyboard()

    if text:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

async def parse_log(response, state):
    last_timestamp = response.get('last_timestamp')
    if last_timestamp:
        last_timestamp = last_timestamp.isoformat()
    await state.update_data(last_timestamp=last_timestamp)

    logs = response.get('logs', [])
    if not logs:
        print("Нет новых логов.")

    return await get_log_text(logs)

async def get_log_text(logs):
    text = "<pre>"
    for log in logs:
        student = log.get('student').get()

        if student.to_dict() is None:
            student_name = "Неизвестный студент"

        else:
            student_data = student.to_dict()  # извлекаем словарь
            student_name = student_data.get('name')

        task_id = log.get('task_id')
        created_at = log.get('created_at')
        dt = datetime.fromisoformat(str(created_at))
        time = dt.strftime("%d %B %Y, %H:%M:%S")
        text += lexicon['ru']['curator']['log']['report'].format(time, student_name, task_id)
        text+='\n'
    text+="</pre>"
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

                    if (faculty == "маркетинг каз" or
                    faculty == "маркетинг рус онлайн" or
                    faculty == "маркетинг рус офлайн"):

                        faculty = 'Marketing'

                    if not faculty in ['Marketing', 'IT']:
                        error+=1
                        continue

                    if telegram.strip().startswith('@'):
                        telegram = telegram[1:]

                    row = fio + " " + faculty + " " + telegram + "\n"
                    students += row
                else:
                    error+=1
                    continue

        except Exception as e:
            await message.answer(f"⚠️ Ошибка при чтении файла:\n{e}")

        await message.answer(f"Строк с неправильным форматом обнаружено: {error}")
        print(students)
        await adding_students(message, students, db)

async def adding_students(message, students, db):
    success = await add_students_async(db, students)

    if success:
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
async def handle_document(message: Message, db):
    text = message.text
    success = await add_levels_async(db, text)

    if success:
        text = lexicon['ru']['curator']['add levels']

    else:
        text = lexicon['ru']['curator']['didnt add levels']

    await message.answer(text)


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
    error = 0
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

                else:
                    await message.answer(f"⚠️ Ошибка при чтении файла:\n")
                    return

        except Exception as e:
            await message.answer(f"⚠️ Ошибка при чтении файла:\n{e}")
            return

        await asyncio.gather(*tasks)
        text = lexicon['ru']['curator']['add tasks']
        await message.answer(text)


# Выход
@router.callback_query(F.data.startswith('exit'))
async def exit(callback: CallbackQuery, state:FSMContext, db):
    keyboard = createAdminPanel()

    data = await state.get_data()
    message_id = data.get('message_id', '')

    if message_id == '':
        print('Warning: module curator.py, line 105. Message id cannot be retrieved from Redis.')

    else:
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
