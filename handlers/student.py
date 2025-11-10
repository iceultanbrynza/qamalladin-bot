from utilities.database_async import (
    query_card_async,
    send_task_async,
    retrieve_tasks_async,
    get_student_id_name_async,
    write_log_async,
    retrieve_completed_tasks_by_student_async,
    get_log_async,
    qyery_good,
    get_url,
    purchase_async,
    get_good_desc_async,
    query_goods_async
)

from utilities.authorizing import is_registered, UserRole
from utilities.keyboard import (
    createInlineTaskButton,
    levelsKeyboard,
    nextKeyboard,
    buyGoodKeyboard,
    exitKeyboard,
    createShopCardKeyboard
)
from utilities.other import get_file_type
from lexicon import lexicon
from config import ALLOWED_FILE_TYPES, CURATORS_CHAT_ID, LOCAL_TZ
from fsm import Form
from qutypes import PurchaseResult

from datetime import datetime
import asyncio
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import InputMediaPhoto

router = Router()

@router.message(F.text=="📊 Мой прогресс")
async def my_card(message: Message, state: FSMContext, db):
    username = message.from_user.username
    is_student = await is_registered(username, db, UserRole.STUDENT)
    if is_student:
        document = await query_card_async(db, telegram=username)

        if not document:
            await message.answer(text="Студент не найден")
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

        await message.answer(text=card)

@router.message(F.text == "📝 Отправить отчет")
async def send_report(message: Message, state: FSMContext, db):
    username = message.from_user.username
    is_student = await is_registered(username, db, UserRole.STUDENT)
    if is_student:
        await state.set_state(Form.send_report)

        document = await query_card_async(db, telegram=username)
        if not document:
            await message.answer(text="Студент не найден")
            return

        level = str(document.get('level', ''))
        faculty = str(document.get('faculty', ''))

        await send_task_list(message, db, username, level, faculty, level)

@router.callback_query(F.data.startswith("level:"), StateFilter(Form.send_report))
async def send_report_for_another_level(callback: CallbackQuery, state: FSMContext, db):
    level = str(callback.data.split(':')[1])
    username = callback.from_user.username
    document = await query_card_async(db, telegram=username)

    if not document:
        await callback.message.answer(text="Студент не найден")
        return

    true_level = str(document.get('level', ''))
    faculty = str(document.get('faculty', ''))
    await send_task_list(callback.message, db, username, level, faculty, true_level)

async def send_task_list(message: Message, db, username, level, faculty, true_level):
    student_id, _ = await get_student_id_name_async(db, username)
    completed_tasks = await retrieve_completed_tasks_by_student_async(db, student_id)

    tasks_dict_of_dicts = await retrieve_tasks_async(db, level, faculty, completed_tasks)

    if tasks_dict_of_dicts:
        for task_id, task_content in tasks_dict_of_dicts.items():
            keyboard = createInlineTaskButton(task_id)
            info = [
                task_content.get('id'),
                task_content.get('number'),
                task_content.get('block'),
                task_content.get('content')
            ]

            response = lexicon['ru']['student']['task'].format(*info)

            await message.answer(text=response, reply_markup=keyboard)

        levels = levelsKeyboard(int(true_level))
        await message.answer(text="Доступные уровни:", reply_markup=levels)

@router.callback_query(F.data.startswith("report:"), StateFilter(Form.send_report))
async def sends_report(callback: CallbackQuery, state: FSMContext, db):
    task_id = str(callback.data.split(':')[1])
    await state.update_data(task_id=task_id)

    await callback.message.answer('Вышлите Фото/Видео/PDF в виде файла(!)')

@router.message(F.document, StateFilter(Form.send_report))
async def handle_document(message: Message, state: FSMContext, db):
    file_type = await get_file_type(message)
    if file_type in ALLOWED_FILE_TYPES:
        task_id_dict = await state.get_data()
        task_id = task_id_dict.get('task_id')
        username = message.from_user.username
        student_id, name = await get_student_id_name_async(db, username)
        doc = message.document
        file_id = doc.file_id
        file = await message.bot.get_file(file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        file_bytes.seek(0)

        response = await send_task_async(db, username, task_id, file_bytes, student_id, file_type)
        if response:
            await write_log_async(db, student_id, task_id)
            await message.answer('✅ Спасибо! Отчёт передан куратору.\nОтслеживай статус задачи в Логах Действий.')

            text = lexicon['ru']['curator']['Curator obtained report V2'].format(name, task_id)
            for chat_id in CURATORS_CHAT_ID:
                await message.bot.send_message(chat_id=chat_id, text=text)
                await message.bot.forward_message(
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )

        else:
            await message.answer('Ваш репорт не удалось сохранить. Пожалуйста, обратитесь к куратору')

    else:
        await message.answer('Бот принимает только фото, видео или pdf в формате файла.')

@router.message(F.text == "💰 Лог действий")
async def get_log(message: Message, state: FSMContext, db):
    username = message.from_user.username
    is_student = await is_registered(username, db, UserRole.STUDENT)
    if is_student:
        await state.set_state(Form.get_student_log)

        student_id, _ = await get_student_id_name_async(db, username)
        response = await get_log_async(db, student_id=student_id)
        last_timestamp = response.get('last_timestamp')
        if last_timestamp:
            last_timestamp = last_timestamp.isoformat()
        await state.update_data(last_timestamp=last_timestamp)

        logs = response.get('logs')
        if logs:
            text = await get_log_text(logs)
            keyboard = nextKeyboard()
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")

@router.callback_query(F.data.startswith('next:logs'), StateFilter(Form.get_student_log))
async def get_next_log(callback:CallbackQuery, state:FSMContext, db):
    data = await state.get_data()
    username = callback.from_user.username
    last_timestamp = data.get('last_timestamp')

    if not last_timestamp:
        await callback.answer('Ошибка. Вернитесь на главное меню')
        return

    last_timestamp = datetime.fromisoformat(last_timestamp)
    student_id, _ = await get_student_id_name_async(db, username)
    response = await get_log_async(db, student_id=student_id, last_timestamp=last_timestamp)

    text = await parse_log(response, state)

    keyboard = nextKeyboard()

    if text is not None:
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")

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

@router.message(F.text == "🏪 Магазин")
async def shop(message: Message, state: FSMContext, db):
    message_id=message.message_id
    username = message.from_user.username
    is_student = await is_registered(username, db, UserRole.STUDENT)
    if is_student:
        await state.set_state(Form.shopping)
        await state.update_data(message_id=message_id)
        goods = await query_goods_async(db)
        if goods:
            sorted_data = list(sorted(goods.items(), key=lambda item: item[1]['name']))
            keyboard = createShopCardKeyboard(sorted_data)
            await message.answer("Каталог товаров магазина QU:", reply_markup=keyboard)

        else:
            keyboard = exitKeyboard()
            await message.answer("Магазин пустует...", reply_markup=keyboard)

@router.callback_query(F.data.startswith('good'), StateFilter(Form.shopping))
async def get_good_card(callback: CallbackQuery, state: FSMContext, db):
    message_id = callback.message.message_id
    good_id = str(callback.data.split(":")[1])
    goods = await query_goods_async(db)
    if not goods:
        await callback.answer("Товары не найдены.")
        return

    sorted_data = dict(sorted(goods.items(), key=lambda item: item[1].get('name', '')))
    for i, (id_, good_data) in enumerate(sorted_data.items()):
        if id_ == good_id:
            index = i
            good = (id_, good_data)
            break

    else:
        await callback.answer("Товар не найден.")
        return

    await state.update_data(message_id=message_id, pos=index)
    good_id, name, description, price, photo = await parse_good(good)
    keyboard = buyGoodKeyboard(good_id)
    caption = lexicon['ru']['student']['shop'].format(name, price, description)
    if photo:
        photo_url = get_url(photo)
        await callback.message.answer_photo(photo=photo_url[0], caption=caption, reply_markup=keyboard)
        return

@router.callback_query(F.data.startswith('shop:exit'), StateFilter(Form.shopping))
async def exit_good(callback: CallbackQuery, state: FSMContext, db):
    await callback.message.delete()

@router.callback_query(F.data.startswith('shop:next'), StateFilter(Form.shopping))
async def get_next_good(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    pos = data.get('pos', '')
    message_id = data.get('message_id', '')

    pos = int(pos)
    if pos == '' or message_id == '':
        await callback.message.answer('Вы не можете использовать эту функцию')
        return

    good = await qyery_good(db, pos+1)
    if good:
        await state.update_data(pos=pos+1)
        good_id, name, description, price, photo = await parse_good(good)
        keyboard = buyGoodKeyboard(good_id)
        caption = lexicon['ru']['student']['shop'].format(name, price, description)
        if photo:
            photo_url = get_url(photo)
            media = InputMediaPhoto(media=photo_url[0], caption=caption)
            await callback.message.edit_media(media=media, reply_markup=keyboard)
            return

    else:
        await callback.answer("Больше товаров нет")

@router.callback_query(F.data.startswith('shop:back'), StateFilter(Form.shopping))
async def get_prev_good(callback: CallbackQuery, state: FSMContext, db):
    data = await state.get_data()
    pos = (data.get('pos', ''))
    message_id = data.get('message_id', '')

    if pos == '' or message_id == '':
        await callback.message.answer('Вы не можете использовать эту функцию')
        return
    pos = int(pos)
    good = await qyery_good(db, pos-1)
    if good:
        await state.update_data(pos=pos-1)
        good_id, name, description, price, photo = await parse_good(good)
        keyboard = buyGoodKeyboard(good_id)
        caption = lexicon['ru']['student']['shop'].format(name, price, description)
        if photo:
            photo_url = get_url(photo)
            media = InputMediaPhoto(media=photo_url[0], caption=caption)
            await callback.message.edit_media(media=media, reply_markup=keyboard)
            return

    else:
        await callback.answer("Больше товаров нет")

@router.callback_query(F.data.startswith('buy:'), StateFilter(Form.shopping))
async def buy(callback: CallbackQuery, state: FSMContext, db):
    good_id = str(callback.data.split(":")[1])
    username = callback.from_user.username
    student_id, name = await get_student_id_name_async(db, username)
    response, msg = await purchase_async(db, student_id, good_id)
    await callback.message.answer(text=msg)

    if response == PurchaseResult.SUCCESS:
        for chat_id in CURATORS_CHAT_ID:
            text = lexicon['ru']['curator']['notify'].format(name)
            await callback.message.bot.send_message(chat_id=chat_id, text=text)

async def parse_good(good:tuple):
    data:dict = good[1]
    id = good[0]
    name = data.get("name", "Товар")
    description = data.get("description", None)
    price = data.get("price", 0)
    photo = data.get("photo", None)
    return id, name, description, price, photo
