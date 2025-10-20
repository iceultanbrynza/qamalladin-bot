from config import OFFSET

from aiogram.types import Message

async def get_dict_with_offset(dict:dict, start:int):
    items = list(dict.items())
    return items[start*OFFSET:start*OFFSET+OFFSET]

async def get_file_type(message: Message):
    mime_type = message.document.mime_type
    if mime_type.startswith("image/"):
        file_type = "photo"
    elif mime_type.startswith("video/"):
        file_type = "video"
    elif mime_type == "application/pdf":
        file_type = "pdf"
    else:
        file_type = "other"
    return file_type