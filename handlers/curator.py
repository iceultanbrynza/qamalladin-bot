from utilities.keyboard import (
    createCardKeyboard,
    createAdminPanel
)
from utilities.database_async import (
    query_students_async,
    query_card_async,
    write_qcoins_async,
    retrieve_report_async
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
import requests

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    InputMediaPhoto,
    InputMediaVideo,
    InputFile,
    InputMediaDocument
)
from aiogram.types.input_file import FSInputFile, URLInputFile

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
        students = await get_dict_with_offset(data, start)
        keyboard = createCardKeyboard(students)
        await message.answer('Список карточек студентов:', reply_markup=keyboard)

@router.callback_query(F.data.startswith('next:card'), StateFilter(Form.student_card,
                                                                   Form.student_choosing_for_accrual,
                                                                   Form.accrual,
                                                                   Form.student_choosing_for_fine,
                                                                   Form.fine,
                                                                   Form.get_report))
async def get_next_students(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    start = int(data.get('start', ''))
    message_id = data.get('message_id', '')

    data = await query_students_async(db)
    students = await get_dict_with_offset(data, start+1)
    keyboard = createCardKeyboard(students)

    if start == '' or message_id == '':
        callback.message.answer('Вы не можете использовать эту функцию')
        return
    else:
        chat_id = callback.message.chat.id
        await callback.message.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id+1, reply_markup=keyboard)
        await state.update_data(start=start+1)

    await callback.answer()

@router.callback_query(F.data.startswith('back:card'), StateFilter(Form.student_card,
                                                                   Form.student_choosing_for_accrual,
                                                                   Form.accrual,
                                                                   Form.student_choosing_for_fine,
                                                                   Form.fine,
                                                                   Form.get_report))
async def get_previous_students(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    start = int(data.get('start', ''))
    message_id = data.get('message_id', '')

    if start>=1:
        data = await query_students_async(db)
        students = await get_dict_with_offset(data, start-1)
        keyboard = createCardKeyboard(students)

        if start == '' or message_id == '':
            callback.message.answer('Вы не можете использовать эту функцию')
            return
        else:
            chat_id = callback.message.chat.id
            await callback.message.bot.edit_message_reply_markup(chat_id=chat_id, message_id=message_id+1, reply_markup=keyboard)
            await state.update_data(start=start-1)
    await callback.answer()

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.student_card))
async def get_card(callback:CallbackQuery, state: FSMContext, db):
    id = str(callback.data.split(':')[1])

    document:dict = await query_card_async(db, id=id)

    if not document:
        await callback.message.answer(text="Студент не найден")

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
        students = await get_dict_with_offset(data, start)
        keyboard = createCardKeyboard(students)
        await message.answer('Выберите студента, которому начислить Qcoins или наберите ФИО вручную по шаблону "Имя Фамилия Qcoins" (можно начислить сразу нескольким, написав через Enter)', reply_markup=keyboard)

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.student_choosing_for_accrual))
async def accrual(callback:CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])

    await state.update_data(student_id=student_id)

    await callback.message.answer("Введите количество баллов для этого студента:")
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
        students = await get_dict_with_offset(data, start)
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

        await message.answer(f"✅ Студент {name} {surname} оштрафован на {qcoins}")

@router.message(F.text, IsInteger(), StateFilter(Form.fine))
async def writing_fine(message: Message, state:FSMContext, db):
    data = await state.get_data()
    student_id = data['student_id']
    qcoins = re.search(r"\d+", message.text)

    if not qcoins:
        await message.answer(f"В сообщении нет числа")
    await write_qcoins_async(-int(qcoins.group()), db, student_id=student_id)
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
        students = await get_dict_with_offset(data, start)
        keyboard = createCardKeyboard(students)
        await message.answer(lexicon['ru']['curator']['Curator asks to get report'], reply_markup=keyboard)

@router.callback_query(F.data.startswith('card:'), StateFilter(Form.get_report,
                                                               Form.student_choosing_for_accrual))
async def fetch_report(callback: CallbackQuery, state:FSMContext, db):
    student_id = str(callback.data.split(':')[1])
    chat_id = callback.message.chat.id
    reports = await retrieve_report_async(db, student_id)
    for task_id, content in reports.items():
        answer = {}
        is_checked = content.pop('is_checked', None)
        info = [
            task_id,
            is_checked
        ]
        text = lexicon['ru']['curator']['Curator obtained report'].format(*info)

        answer['text'] = text

        # if not is_checked:
        #     keyboard =

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

# Куратор не находится в состоянии, но испоьзует кнопки
@router.callback_query(F.data.startswith('card:'), StateFilter(None))
async def callback_no_state(callback:CallbackQuery, state:FSMContext, db):
    await callback.answer('Выберите действие')

router.message.register()