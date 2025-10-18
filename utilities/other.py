from config import OFFSET

async def get_dict_with_offset(dict:dict, start:int):
    items = list(dict.items())
    return items[start*OFFSET:start*OFFSET+OFFSET]