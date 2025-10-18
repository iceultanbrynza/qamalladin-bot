from config import load_config, BotConfig
from handlers import curator, authorization, admin, student

import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

async def main():
    config:BotConfig = load_config()

    bot = Bot(token=config.token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    storage = config.storage
    dp = Dispatcher(storage=storage)

    db = config.database
    admins = config.admins

    dp.workflow_data.update({'db': db, 'admins': admins})

    dp.include_routers(authorization.router, curator.router, student.router, admin.router)

    await bot.delete_webhook(drop_pending_updates=True)

    await dp.start_polling(bot)

if __name__=="__main__":
    asyncio.run(main())