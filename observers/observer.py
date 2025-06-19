
from aiogram import Bot
from const import Const
from db.mongo_db import AsyncDatabase
from db.statuses import WatermarkStatus,DownloadStatus,DoneStatus
from aiogram.types import FSInputFile, InputMediaPhoto
import asyncio
from observers.retryable_queue import RetryableQueue
from processing.watermark import add_watermark
from processing.OCR import OCR
from processing.llm import LLM
from pathlib import Path
import os
import logging
import threading

logger = logging.getLogger(__name__)

class Observer:

    def __init__(self, bot: Bot, 
                 db: AsyncDatabase, 
                 OCR:OCR, 
                 LLM:LLM,  
                 file_path_download: str, 
                 file_path_processed: str,
                 MAX_RETRIERS = 3):
        self.bot = bot
        self.db = db
        self.OCR = OCR
        self.LLM = LLM

        self.MAX_RETRIERS = MAX_RETRIERS

        self.file_path_download = file_path_download
        self.file_path_processed = file_path_processed

        self.download_queue = RetryableQueue()
        self.process_queue = RetryableQueue()
        self.send_queue = RetryableQueue() 


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
        new_items = await self.db.get_users_with_files_by_status(DownloadStatus.QUEUED,2)
        for item in new_items:
            await self.download_queue.put(item)

    async def __upload_to_process(self):
        new_items = await self.db.get_users_with_files_by_status(DownloadStatus.UPLOADED,1)
        for item in new_items:
            await self.process_queue.put(item)

    async def __upload_to_send(self):
        new_items =  await self.db.get_users_with_files_by_status([WatermarkStatus.CAPTION,WatermarkStatus.NOT_CAPTION],2)
        for item in new_items:
            await self.send_queue.put(item)
        

    async def download(self,semaphore=asyncio.Semaphore(1)):

        data = None 

        async with semaphore:
            while True:  
                try:         
                    data = await self.download_queue.get()
                    user_id = data["user_id"]
                    message = data["message"]

                    message["retries"] = message.get("retries", 0)
                    

                    for file in message["files"]:
                        path = str(Path(self.file_path_download) / f"{file['file_id']}.jpg")
                        await self.bot.download_file(file["file_path"], path)

                        file["file_path"] = f"{file['file_id']}.jpg"
                        await self.db.update_fields(user_id,
                                                    message["message_id"],
                                                    file["file_id"],
                                                    file)

                    message["status"] = DownloadStatus.UPLOADED.value
                    message["retries"] = 0
                    await self.db.update_status_message(user_id,
                                                        message["message_id"],
                                                        DownloadStatus.UPLOADED)
                    await self.process_queue.put({"user_id":user_id,
                                                "message":message})
                        
                except Exception as e:
                    message["retries"] += 1
                    logger.error(f"Ошибка скачивания (попытка {message['retries']}): {e}")

                    if message["retries"] < self.MAX_RETRIERS:
                        await self.download_queue.put({
                        "user_id": user_id,
                        "message": message},
                        True)
                        
                    else:
                        await self.db.update_status_message(user_id,
                                                        message["message_id"],
                                                        DoneStatus.FAILED)


    async def process_image(self,semaphore=asyncio.Semaphore(1)):

        async with semaphore:
            while True:
                rm_path = []
                try:    
                    data = await self.process_queue.get()
                    user_id = data["user_id"]
                    message = data["message"]

                    message["retries"] = message.get("retries", 0)

                    config = (await self.db.get_configuration(user_id))["config"]

                    full_text = ""
                    caption = None
                    
                    for file in message["files"]:

                        path = str(Path(self.file_path_download) / f"{file['file_path']}")

                        if not os.path.exists(path):
                            logger.warning(f"Файл не найден: {path}")
                            continue                        
                        
                        watermark_path = None

                        try:
                            text = await self.OCR.get_text_from_image(image_path=path)
                            if text:
                                full_text += text
                        except Exception as e:
                            logger.warning(f"OCR окончательно не удалось для файла {file['file_id']}: {e}")



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

                        
                        await self.db.update_fields(
                            user_id,
                            message["message_id"],
                            file["file_id"],
                            file
                        )

                        rm_path.append(path)
                    
                    try:
                        if full_text != "":
                            caption = await self.LLM.ask_llm(full_text)
                            message["caption"] = caption
                    except Exception as e:
                        logger.warning(f"LLM не удалось для сообщения {message['caption']}: {e}")


                    status = WatermarkStatus.CAPTION if caption else WatermarkStatus.NOT_CAPTION
                    message["retries"] = 0
                    message["status"] = status.value
                    await self.db.update_status_message(
                        user_id,
                        message["message_id"],
                        status,
                        fields = message
                    )

                    await self.send_queue.put({"user_id":user_id,
                                                "message":message})
                    
                    await asyncio.to_thread(self.__remove_files,rm_path)

                except Exception as e:

                    logger.error(f"Ошибка обработки сообщения: (попытка {message['retries']}): {e}")

                    message["retries"] += 1

                    if message["retries"] < self.MAX_RETRIERS:
                        await self.process_queue.put({"user_id":user_id,
                                                    "message":message},True)
                        
                    else: 
                        await self.db.update_status_message(
                            user_id,
                            message["message_id"],
                            DoneStatus.FAILED
                        )

        
    async def send_image(self,semaphore=asyncio.Semaphore(1)):

        async with semaphore:
            while True:

                rm_path = []
        
                try: 
                    data = await self.send_queue.get()
                    user_id = data["user_id"]
                    message = data["message"]

                    message["retries"] = message.get("retries", 0)

                    media = []
                    
                    for idx, file in enumerate(message["files"]):
                        
                            path = str(Path(self.file_path_processed) / f"{file['file_path']}")

                            if not os.path.exists(path):
                                logger.warning(f"Файл не найден: {path}")
                                continue      

                            if idx == 0:
                                media.append(InputMediaPhoto(media=FSInputFile(path), caption=message["caption"]))
                            else:
                                media.append(InputMediaPhoto(media=FSInputFile(path)))

                            rm_path.append(path)

                    await self.bot.send_media_group(chat_id=user_id, media=media)

                    await self.db.update_status_message(user_id,
                                                    message["message_id"],
                                                    DoneStatus.DONE if message["caption"] else DoneStatus.ERROR_DONE)

                    await asyncio.to_thread(self.__remove_files,rm_path)

                except Exception as e:
                    logger.error(f"Ошибка при обработке отправки: (попытка {message['retries']}): {e}")
                    message["retries"] += 1

                    if message["retries"] < self.MAX_RETRIERS:
                        await self.send_queue.put({"user_id":user_id,
                                                "message":message},True)
                    else:
                        await self.db.update_status_message(
                            user_id,
                            message["message_id"],
                            DoneStatus.FAILED
                        )
                        

    def __remove_files(self,rm_path):
        thread_name = threading.current_thread().name
        logger.debug(f"[{thread_name}] Удаляю файлы: {rm_path}")
        for f in rm_path:
            try:
                Path(f).unlink()
            except FileNotFoundError:
                logger.error("Файл уже удалён")
            except PermissionError:
                logger.error("Нет прав на удаление файла")
            except Exception as e:
                logger.error(f"Ошибка при удалении файла: {e}")




                    
                    
