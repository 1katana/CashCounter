from aiogram import Dispatcher, Router, Bot
from const import Const
from db.mongo_db import AsyncDatabase
from observers.observer import Observer
from tg.bot import setup_handlers,set_default_commands
import asyncio
from processing.OCR import OCR
from processing.llm import LLM

bot_istance = Bot(Const.TELEGRAM_TOKEN)
dp = Dispatcher()
router_istance = Router()
dp.include_router(router_istance)

OCR_instance = OCR(Const.OCR_API_KEY,Const.OCR_URL)
LLM_instance = LLM(Const.MODEL,Const.LLM_URL,Const.LLM_API_KEY,Const.SYSTEM_PROMPT)

db_istance = AsyncDatabase()
observer_istance = Observer(bot_istance, 
                            db_istance,
                            OCR_instance,
                            LLM_instance, 
                            Const.FILE_PATH_DOWNLOAD, 
                            Const.FILE_PATH_PROCESSED)

async def main():
    await observer_istance.start()  

    await set_default_commands(bot_istance)

    setup_handlers(router_istance, bot_istance, db_istance, observer_istance)

    await dp.start_polling(bot_istance)

if __name__ == "__main__":
    asyncio.run(main())
