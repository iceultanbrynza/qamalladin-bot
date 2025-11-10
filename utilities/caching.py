from config import redis_client

import json

async def read_from_redis(group:str)->list|dict:
    data_type = await redis_client.type(group)
    if data_type == 'list':
        values = await redis_client.lrange(group, 0, -1)
        return [json.loads(value) for value in values]

    if data_type == 'hash':
        values = await redis_client.hgetall(group)
        return {a: json.loads(b) for a,b in values.items()}

async def write_to_redis(group:str, data:list | dict):
    if isinstance(data, list) and data:
        await redis_client.rpush(group, *[json.dumps(item, ensure_ascii=False) for item in data])
        await redis_client.expire(group, 86400)

    elif isinstance(data, dict) and data:
        await redis_client.hset(group, mapping={k: json.dumps(v, ensure_ascii=False, default=str) for k, v in data.items()})
        await redis_client.expire(group, 86400)

    elif len(data)==0:
        return

    else:
        raise TypeError(f"data must be either list or dict. You are tring to load to Redis the data of {type(data)} type")

async def delete_from_redis_by_group(group: str) -> bool:
    """
    Удаляет группу (ключ) из Redis, независимо от типа данных.
    Возвращает True, если ключ был удалён.
    """
    try:
        deleted_count = await redis_client.delete(group)
        return deleted_count > 0
    except Exception as e:
        return False


async def delete_from_redis(group, id):
    """
    Удаление конкретного товара из кэша с целью оставлять кэш актуальным после удаления
    """
    try:
        res = await redis_client.hdel(group, id)
        if res == 1:
            return True
        else:
            return False
    except:
        return False