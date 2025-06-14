
from aiogram import Bot
from const import Const
from db.mongo_db import AsyncDatabase
from db.statuses import WatermarkStatus,DownloadStatus
from aiogram.types import FSInputFile, InputMediaPhoto
from aiogram import Bot
import asyncio
import logging
from processing.watermark import add_watermark
from processing.OCR import OCR
from processing.llm import LLM
from pathlib import Path
import os

class Observer:

    def __init__(self, bot: Bot, db: AsyncDatabase, OCR:OCR, LLM:LLM,  file_path_download: str, file_path_processed: str):
        self.bot = bot
        self.db = db
        self.OCR = OCR
        self.LLM = LLM

        self.file_path_download = file_path_download
        self.file_path_processed = file_path_processed

        self.download_queue = asyncio.Queue()
        self.process_queue = asyncio.Queue()
        self.send_queue = asyncio.Queue() 


        

    async def start(self):
        asyncio.create_task(self.send_image(asyncio.Semaphore(2)))
        asyncio.create_task(self.process_image())
        asyncio.create_task(self.download(asyncio.Semaphore(2)))

        asyncio.create_task(self.__upload_to_send())
        asyncio.create_task(self.__upload_to_process())
        asyncio.create_task(self.__upload_to_download())
        
        


    async def add_message_with_update(self,id:int,message:dict):
        result = await self.db.add_message(id,message)
        if result:
            await self.download_queue.put(result)
        
    async def __upload_to_download(self):
        current_items = {item["_id"] for item in self.download_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status(DownloadStatus.QUEUED,2)
            if item["user_id"] not in current_items  
        ]
        for item in new_items:
            await self.download_queue.put(item)

    async def __upload_to_process(self):
        current_items = {item["_id"] for item in self.process_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status(DownloadStatus.UPLOADED,1)
            if item["user_id"] not in current_items  
        ]
        for item in new_items:
            await self.process_queue.put(item)

    async def __upload_to_send(self):
        current_items = {item["_id"] for item in self.send_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status([WatermarkStatus.DONE,WatermarkStatus.ERROR_DONE],2)
            if item["user_id"] not in current_items  
        ]
        for item in new_items:
            await self.send_queue.put(item)
        

    async def download(self,semaphore=asyncio.Semaphore(1)):
        while True:
            try:
                async with semaphore:
                    data = await self.download_queue.get()
                    user_id = data["user_id"]
                    message = data["message"]
                    
                    for file in message["files"]:
                        path = str(Path(self.file_path_download) / f"{file['file_id']}.jpg")
                        await self.bot.download_file(file["file_path"], path)

                        file["file_path"] = f"{file['file_id']}.jpg"
                        await self.db.update_fields(user_id,
                                                    message["message_id"],
                                                    file["file_id"],
                                                    file)

                    message["status"] = DownloadStatus.UPLOADED.value
                    await self.db.update_status_message(user_id,
                                                        message["message_id"],
                                                        DownloadStatus.UPLOADED)
                    self.download_queue.task_done()
                    await self.process_queue.put({"user_id":user_id,
                                                  "message":message})

            except Exception as e:
                logging.error(f"Ошибка скачивания {e}")
            
            await asyncio.sleep(0)


    async def process_image(self,semaphore=asyncio.Semaphore(1)):
        while True:
            try:
                async with semaphore:
                    data = await self.process_queue.get()
                    user_id = data["user_id"]
                    message = data["message"]

                    config = (await self.db.get_configuration(user_id))["config"]

                    full_text = ""
                    caption = None
                    
                    for file in message["files"]:
                        path = str(Path(self.file_path_download) / f"{file['file_path']}")
                        
                        watermark_path = None

                        try:
                            text = await self.OCR.get_text_from_image(image_path=path)
                            if text:
                                full_text += text
                        except Exception as e:
                            logging.warning(f"OCR не удалось для файла {file['file_id']}: {e}")

                
                        try:
                            watermark_path = await asyncio.to_thread(
                                add_watermark,
                                path,
                                self.file_path_processed, 
                                config["text"],
                                config["line_spacing"],
                                config["font_size"],
                                config["angle"],
                                tuple(config["color"]),
                            )
                            if watermark_path:
                                relative_path = Path(watermark_path).relative_to(self.file_path_processed)
                                file["file_path"] = str(relative_path)
                            else:
                                raise ValueError("Функция вернула None")

                        except Exception as e:
                            logging.error(f"Ошибка при добавлении водяного знака для файла {file['file_id']}: {e}")
                        
                        
                        await self.db.update_fields(
                            user_id,
                            message["message_id"],
                            file["file_id"],
                            file
                        )
                    
                    try:
                        if full_text != "":
                            caption = await self.LLM.ask_llm(full_text)
                            message["caption"] = caption
                    except Exception as e:
                        logging.warning(f"LLM не удалось для файла {file['file_id']}: {e}")


                    status = WatermarkStatus.DONE if caption else WatermarkStatus.ERROR_DONE
                    message["status"] = status.value
                    await self.db.update_status_message(
                        user_id,
                        message["message_id"],
                        status,
                        fields = message
                    )

                    # Удаление download

                    self.process_queue.task_done()
                    await self.send_queue.put({"user_id":user_id,
                                                "message":message})

            except Exception as e:
                logging.error(f"Ошибка обработки сообщения: {e}")
            await asyncio.sleep(0)
        
    async def send_image(self,semaphore=asyncio.Semaphore(1)):
        while True:
            try:

                async with semaphore:
                    data = await self.send_queue.get()
                    user_id = data["user_id"]
                    message = data["message"]

                    media = []
                    
                    for idx, file in enumerate(message["files"]):
                        
                            path = str(Path(self.file_path_processed) / f"{file['file_path']}")
                            if not os.path.exists(path):
                                logging.warning(f"Файл не найден: {path}")
                                continue

                            if idx == 0:
                                media.append(InputMediaPhoto(media=FSInputFile(path), caption=message["caption"]))
                            else:
                                media.append(InputMediaPhoto(media=FSInputFile(path)))

                    await self.bot.send_media_group(chat_id=user_id, media=media)

                    self.send_queue.task_done()

            except Exception as e:
                logging.error(f"Ошибка при обработке отправки: {e}")

            await asyncio.sleep(0)
            