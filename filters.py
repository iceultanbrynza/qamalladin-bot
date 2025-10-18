from aiogram.filters import BaseFilter
from aiogram.types import Message

import re
from io import BytesIO
from aiogram import types

ALLOWED_TYPES = {
    'image/jpeg',
    'image/png',
    'video/mp4',
    'application/pdf'
}

class IsInteger(BaseFilter):
    async def __call__(self, message: Message)->bool:
        value = re.search(r"\d+", message.text)
        return True if value else False

class IsFioQcoins(BaseFilter):
    async def __call__(self, message: Message)->bool:
        return re.fullmatch(r'(?:[А-ЯЁA-Z][а-яёa-z]+ [А-ЯЁA-Z][а-яёa-z]+ \d+\n?)+', message.text)

class IsAdmin(BaseFilter):
    async def __call__(self, message: Message, admins)->bool:
        return message.chat.id in admins

async def validate_file(file: types.File) -> BytesIO | None:
    # Определяем MIME-тип
    mime = file.mime_type if hasattr(file, 'mime_type') else None

    # Проверяем допустимый тип
    if mime not in ALLOWED_TYPES:
        print(f"❌ Недопустимый MIME-тип: {mime}")
        return False

    return True