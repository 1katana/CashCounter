
from aiogram import Bot
from const import Const
from db.mongo_db import AsyncDatabase
from db.statuses import WatermarkStatus,DownloadStatus
from aiogram.types import InputFile
from aiogram import Bot
import asyncio
import logging
from processing.watermark import add_watermark
from processing.OCR import OCR
from processing.llm import LLM

class Observer:

    def __init__(self, bot: Bot, db: AsyncDatabase, OCR:OCR, LLM:LLM,  file_path_download: str, file_path_processed: str):
        self.bot = bot
        self.db = db
        self.OCR = OCR
        self.LLM = LLM

        self.semaphore = asyncio.Semaphore(5)

        self.file_path_download = file_path_download
        self.file_path_processed = file_path_processed

        self.download_queue = asyncio.Queue()
        self.process_queue = asyncio.Queue()
        self.send_queue = asyncio.Queue() 


        

    async def start(self):
        asyncio.create_task(self.upload_to_download())
        asyncio.create_task(self.download())
        
    async def upload_to_download(self):
        current_items = {item["_id"] for item in self.download_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status(DownloadStatus.QUEUED,2)
            if item["user_id"] not in current_items  
        ]
        for item in new_items:
            await self.download_queue.put(item)

    async def upload_to_process(self):
        current_items = {item["_id"] for item in self.process_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status(DownloadStatus.UPLOADED,1)
            if item["user_id"] not in current_items  
        ]
        for item in new_items:
            await self.process_queue.put(item)

    async def upload_to_send(self):
        current_items = {item["_id"] for item in self.send_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status([WatermarkStatus.DONE,WatermarkStatus.ERROR_DONE],2)
            if item["user_id"] not in current_items  
        ]
        for item in new_items:
            await self.send_queue.put(item)
        

    async def download(self):
        while True:
            try:
                async with self.semaphore:
                    message = await self.download_queue.get()
                    
                    for file in message["files"]:
                        path = f"{self.file_path_download}{file['file_id']}.jpg"
                        await self.bot.download_file(file["file_path"], path)

                        file_updated = file.copy()
                        file_updated["file_path"] = path
                        await self.db.update_fields(message["user_id"],
                                                    message["message_id"],
                                                    file["file_id"],
                                                    file_updated)

                    message["status"] = DownloadStatus.UPLOADED.value
                    await self.db.update_status_message(message["user_id"],
                                                        message["message_id"],
                                                        DownloadStatus.UPLOADED)
                    self.download_queue.task_done()
                    await self.process_queue.put(message)

            except Exception as e:
                logging.error(f"Ошибка скачивания {e}")


    async def process_image(self):
        while True:
            try:
                async with self.semaphore:
                    message = await self.process_queue.get()

                    full_text = ""
                    caption = None
                    
                    for file in message["files"]:
                        path = f"{self.file_path_download}{file['file_id']}"

                        
                        watermark_path = None

                        try:
                            text = await OCR.get_text_from_image(image_path=path)
                            if text:
                                full_text += text
                        except Exception as e:
                            logging.warning(f"OCR не удалось для файла {file['file_id']}: {e}")

                
                        try:
                            watermark_path = await asyncio.to_thread(
                                add_watermark,
                                path,
                                self.file_path_processed, 
                            )
                            if watermark_path is None:
                                raise ValueError("Функция вернула None")

                            file["file_path"] = watermark_path
                        except Exception as e:
                            logging.error(f"Ошибка при добавлении водяного знака для файла {file['file_id']}: {e}")
                        
                        
                        await self.db.update_fields(
                            message["user_id"],
                            message["message_id"],
                            file["file_id"],
                            file
                        )
                    
                    try:
                        if full_text != "":
                            caption = await LLM.ask_llm(full_text)
                    except Exception as e:
                        logging.warning(f"LLM не удалось для файла {file['file_id']}: {e}")

                    status = WatermarkStatus.DONE.value if caption else WatermarkStatus.ERROR_DONE.value

                    await self.db.update_status_message(
                        message["user_id"],
                        message["message_id"],
                        status
                    )
                    self.process_queue.task_done()

            except Exception as e:
                logging.error(f"Ошибка обработки сообщения: {e}")
            await asyncio.sleep(0)
        

    async def send_image(self):
        # TODO
        await self.bot.send_photo()