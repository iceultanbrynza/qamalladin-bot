from .database import *
from .caching import write_to_redis, read_from_redis
from .cloud import upload_many_async

import asyncio

async def query_students_async(db: Client):
    """
    Firstly, it tries retain student dict from Redis asynchronously,
    but if Redis is empty, it runs a Firestore student query asynchronously
    by delegating the blocking synchronous query to a background thread.
    After all, it saves it in Redis in terms of hash.
    """
    students: dict = await read_from_redis("students")

    if not students:
        students:dict = await asyncio.to_thread(query_students, db)
        await write_to_redis("students", students)

    return students

async def rewrite_cached_students(db:Client):
    students:dict = await asyncio.to_thread(query_students, db)
    await write_to_redis("students", students)

async def query_students_tags_async(db: Client):
    """
    Firstly, it tries retain student list from Redis asynchronously,
    but if Redis is empty, it runs a Firestore student query asynchronously
    by delegating the blocking synchronous query to a background thread.
    After all, it saves it in Redis in terms of list.
    """
    students: list = await read_from_redis("students_tags")

    if not students:
        students:list = await asyncio.to_thread(query_students_tags, db)
        await write_to_redis("students_tags", students)

    return students

async def query_curators_tags_async(db: Client):
    curators: list = await read_from_redis("curator_tags")

    if not curators:
        curators:list = await asyncio.to_thread(query_curators_tags, db)
        await write_to_redis("curator_tags", curators)

    return curators

async def query_card_async(db: Client, id: str=None, telegram:str=None):
    card:dict = await asyncio.to_thread(query_card, db, id, telegram)
    return card

async def write_qcoins_async(qcoins:int, db: Client, mode='id', student_id=None, name = None, surname = None):
    state, msg = await asyncio.to_thread(write_qcoins, qcoins, db, mode, student_id, name , surname)
    return state, msg

async def send_task_async(db: Client, username, task_id, file, student_id, file_type):
    response = await asyncio.to_thread(send_task, db, username, task_id, file, student_id, file_type)
    return response

async def write_log_async(db, student_id, task_id):
    await asyncio.to_thread(write_log, db, student_id, task_id)

async def retrieve_tasks_async(db:Client, level:str, faculty:str, completed_tasks)->dict:
    tasks:dict = await asyncio.to_thread(retrieve_task, db, level, faculty, completed_tasks)
    return tasks

async def retrieve_report_async(db: Client, student_id:str):
    reports:dict = await asyncio.to_thread(retrieve_report, db, student_id)
    return reports

async def get_student_id_name_async(db:Client, username):
    student_id, name = await asyncio.to_thread(get_student_id_name, db, username)
    return student_id, name

async def mark_as_checked_async(db: Client, student_id:str, task_id:str):
    is_marked = await asyncio.to_thread(mark_as_chekched, db, student_id, task_id)
    return is_marked

async def get_log_async(db: Client, student_id=None, last_timestamp:str=None)->dict:
    response = await asyncio.to_thread(get_log, db, student_id, last_timestamp)
    return response

async def add_student_async(db: Client, year:int, student:str):
    await asyncio.to_thread(add_student, db, year, student)

async def add_students_async(db: Client, message_text:str):
    year = datetime.now().year
    lines = message_text.strip().split('\n')

    tasks = []
    for line in lines:
        student = line.strip().split(' ')
        if len(student) == 4:
            tasks.append(add_student_async(db, year, student))
        else:
            return False

    await asyncio.gather(*tasks)
    return True

async def add_fine_async(db, mode='id', student_id=None, name=None, surname=None):
    await asyncio.to_thread(add_fine, db, mode, student_id, name, surname)

async def is_balance_per_level_enough(db:Client, student_id:str)->tuple[ProgressResult, str|None]:
    is_enough = await asyncio.to_thread(query_level_goal, db, student_id)
    if is_enough:
        state, msg = await asyncio.to_thread(move_to_next_level, db, student_id)
        return state, msg

    return ProgressResult.STANDSTILL, None

async def add_level_async(db:Client, level):
    await asyncio.to_thread(add_level, db, level)

async def add_levels_async(db:Client, levels:str):
    lines = levels.strip().split('\n')

    tasks = []
    for line in lines:
        level = line.strip().split(' ')
        if len(level) == 4:
            tasks.append(add_level_async(db, level))
        else:
            for t in tasks:
                t.close()
            return False

    await asyncio.gather(*tasks)
    return True

async def add_task_async(db, faculty, level, block, number, content):
    await asyncio.to_thread(add_task, db, faculty, level, block, number, content)

async def record_chat_id_async(db,username, role, chat_id):
    await asyncio.to_thread(record_chat_id, db, username, role, chat_id)

async def retrieve_completed_tasks_by_student_async(db, student_id):
    task_ids = await asyncio.to_thread(retrieve_completed_tasks_by_student, db, student_id)
    return task_ids

async def get_student_chat_id(db:Client, student_id):
    student = await query_students_async(db)
    data:dict = student.get(student_id)
    if data:
        chat_id = data.get("chat_id")
        return chat_id if chat_id else None
    return None

async def get_student_id_for_curator_async(db:Client, name, surname):
    student_id = await asyncio.to_thread(get_student_id_for_curator, db, name, surname)
    return student_id

async def delete_task_async(db, student_id, task_id):
    await asyncio.to_thread(delete_task, db, student_id, task_id)

async def write_accrual_to_log_async(db, qcoins, student_id, task_id=None):
    response = await asyncio.to_thread(write_accrual_to_log, db, qcoins, student_id, task_id)
    return response

async def query_goods_async(db: Client):
    goods: dict = await read_from_redis("shop")

    if not goods:
        goods:dict = await asyncio.to_thread(query_goods, db)
        await write_to_redis("shop", goods)

    return goods

async def qyery_good(db: Client, position:int)->tuple:
    goods = await query_goods_async(db)
    if goods:
        sorted_data = sorted(goods.items(), key=lambda item: item[1]['name'])

        try:
            good = sorted_data[position]

        except IndexError:
            return {}

        return good

    else:
        return {}

async def upload_goods_async(db, data, photo, public_id):
    response = await asyncio.to_thread(upload_goods, db, data, photo, public_id)
    return response

async def rewrite_cached_goods(db:Client):
    goods:dict = await asyncio.to_thread(query_goods, db)
    await write_to_redis("shop", goods)

async def purchase_async(db: Client, student_id:str, good_id:str):
    response, msg = await asyncio.to_thread(purchase, db, student_id, good_id)
    return response, msg

async def get_good_desc_async(name, good_id, time):
    msg = await asyncio.to_thread(get_good_desc, name, good_id, time)
    return msg

async def rewrite_cached_shop(db:Client):
    goods:dict = await asyncio.to_thread(query_goods, db)
    await write_to_redis("shop", goods)