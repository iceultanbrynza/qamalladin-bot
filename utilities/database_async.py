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

async def retrieve_tasks_async(db:Client, level:str, faculty:str)->dict:
    tasks:dict = await asyncio.to_thread(retrieve_task, db, level, faculty)
    return tasks

async def retrieve_report_async(db: Client, student_id:str):
    reports:dict = await asyncio.to_thread(retrieve_report, db, student_id)
    return reports

async def get_student_id_async(db:Client, username):
    student_id = await asyncio.to_thread(get_student_id, db, username)
    return student_id