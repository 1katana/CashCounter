from aiogram import Dispatcher, Router, Bot
from const import Const
from db.mongo_db import AsyncDatabase
from observers.observer import Observer
from tg.bot import setup_handlers  

bot_istance = Bot(Const.TELEGRAM_TOKEN)
dp = Dispatcher()
router_istance = Router()
dp.include_router(router_istance)

db_istance = AsyncDatabase()
observer_istance = Observer(bot_istance, db_istance, Const.FILE_PATH_DOWNLOAD, Const.FILE_PATH_PROCESSED)

def main():
    setup_handlers(router_istance, bot_istance, db_istance, observer_istance)
    dp.run_polling(bot_istance)

if __name__ == "__main__":
    main()