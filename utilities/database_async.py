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
    await asyncio.to_thread(write_qcoins, qcoins, db, mode, student_id, name , surname)

async def send_task_async(db: Client, username, task_id, file, student_id, file_type):
    await asyncio.to_thread(send_task, db, username, task_id, file, student_id, file_type)

async def write_log_async(db, student_id, task_id):
    await asyncio.to_thread(write_log, db, student_id, task_id)

async def retrieve_tasks_async(db:Client, level:str, faculty:str)->dict:
    tasks:dict = await asyncio.to_thread(retrieve_task, db, level, faculty)
    return tasks

async def retrieve_report_async(db: Client, student_id:str):
    reports:dict = await asyncio.to_thread(retrieve_report, db, student_id)
    return reports

async def get_student_id_async(db:Client, username):
    student_id = await asyncio.to_thread(get_student_id, db, username)
    return student_id

async def mark_as_checked_async(db: Client, student_id:str, task_id:str):
    is_marked = await asyncio.to_thread(mark_as_chekched, db, student_id, task_id)
    return is_marked

async def get_log_async(db: Client, last_timestamp:str=None)->dict:
    response = await asyncio.to_thread(get_log, db, last_timestamp)
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
            return False

    await asyncio.gather(*tasks)
    return True
