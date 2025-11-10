from config import load_config, BotConfig
from handlers import curator, authorization, admin, student

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import Update

from fastapi import FastAPI, Request

app = FastAPI()
config:BotConfig = load_config()

bot = Bot(token=config.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = config.storage
dp = Dispatcher(storage=storage)

db = config.database
admins = config.admins

dp.workflow_data.update({'db': db, 'admins': admins})

dp.include_routers(authorization.router, curator.router, student.router, admin.router)

WEBHOOK_URL = config.webhook_host + '/webhook'

@app.on_event("startup")
async def on_startup():
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)
    return {"ok": True}

@app.get("/")
async def home():
    return {"status": "running"}