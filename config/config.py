import os
import base64
import json
from dataclasses import dataclass
from enum import Enum

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

import redis.asyncio as redis

import cloudinary

from aiogram.fsm.storage.redis import RedisStorage

# Import creadetials for DataBase
from dotenv import load_dotenv
load_dotenv()

OFFSET = 1
ALLOWED_FILE_TYPES = ['pdf', 'photo', 'video']

redis_client = redis.Redis(
        host=os.getenv('HOST'),
        port=os.getenv('PORT'),
        decode_responses=True,
        username="default",
        password=os.getenv('PASSWORD')
    )

cloudinary.config(
  cloud_name = os.getenv('CLOUD_NAME'),
  api_key = os.getenv('API_KEY'),
  api_secret = os.getenv('API_SECRET')
)

class UserRole(str, Enum):
    STUDENT = "student"
    CURATOR = "curator"
    GUEST = "guest"

@dataclass
class BotConfig:
    token:str
    database:str
    admins: list
    storage:RedisStorage

def load_config()->BotConfig:
    # assemble configuration info

    fb_decoded_key = base64.b64decode(os.getenv("FIREBASE_KEY")).decode('utf-8')
    fb_private_key = json.loads(fb_decoded_key)

    cred = credentials.Certificate(fb_private_key)

    app = firebase_admin.initialize_app(cred)

    db = firestore.client()

    config = BotConfig(
        token=os.getenv('BOT_TOKEN'),
        database=db,
        admins=[int(admin.strip()) for admin in os.getenv('ADMINS', '').split(',') if admin.strip().isdigit()],
        storage=RedisStorage(redis=redis_client)
    )

    return config