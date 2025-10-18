from config import redis_client, UserRole
from .database_async import query_students_tags_async, query_curators_tags_async

from google.cloud.firestore import Client

async def is_registered(username, db:Client, position: UserRole)->bool:
    role = await get_role(username, db)
    return True if role == position or role == UserRole.CURATOR else False

async def get_role(username, db:Client):
    students, curators = await authorize(db)
    if username in curators:
        return UserRole.CURATOR
    elif username in students:
        return UserRole.STUDENT
    else:
        return UserRole.GUEST

async def authorize(db:Client):
    curators:list = await query_curators_tags_async(db)

    students:list = await query_students_tags_async(db)

    return students, curators