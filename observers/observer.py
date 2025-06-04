from aiogram.types import InputFile
from aiogram import Bot
from const import Const
from db.mongo_db import AsyncDatabase
from db.statuses import WatermarkStatus,DownloadStatus
from aiogram.types import InputFile
from aiogram import Bot

async def send_photo_with_caption(bot:Bot ,user_id: int, photo_path: str, caption: str):
    """
    Отправляет фото с подписью пользователю в Telegram.

    :param bot: экземпляр Bot
    :param user_id: Telegram ID пользователя
    :param photo_path: путь к изображению (локальный файл)
    :param caption: подпись под фото
    """
    photo = InputFile(photo_path)
    await bot.send_photo(chat_id=user_id, photo=photo, caption=caption)

async def download(bot:Bot ,file_path,destination):
    await bot.download_file(
                file_path, 
                destination
            )

class Observer:

    def __init__(self,bot:Bot,db:AsyncDatabase,file_path_dowload:str,file_path_processed:str):

        self.bot = bot
        self.db = db

        self.file_path_dowload = file_path_dowload
        self.file_path_processed = file_path_processed

        self.current = None
        self.images_download = []
        self.images_watermark = []


    async def observer_download(self):
        user = await self.db.get_one_with_status(DownloadStatus.QUEUED)    
        if user is not None:
            for file in user["files_download"]:
                await self.bot.download_file(
                    file["file_path"], 
                    self.file_path_dowload + file["file_id"]+".jpg"
                )

                file["file_path"] = self.file_path_dowload + file["file_id"]
                file["status"] = DownloadStatus.UPLOADED.value
                
                await self.db.update_file_download_fields(user["_id"],file["file_id"],file)
                print()

    
    async def observer_receive(self):
        pass

    async def processing(self):
        pass