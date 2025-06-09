from aiogram.types import InputFile
from aiogram import Bot
from const import Const
from db.mongo_db import AsyncDatabase
from db.statuses import WatermarkStatus,DownloadStatus
from aiogram.types import InputFile
from aiogram import Bot
import asyncio
import logging
from processing import OCR,watermark,llm


class Observer:

    def __init__(self, bot: Bot, db: AsyncDatabase, file_path_download: str, file_path_processed: str):
        self.bot = bot
        self.db = db
        self.semaphore = asyncio.Semaphore(5)

        self.file_path_download = file_path_download
        self.file_path_processed = file_path_processed

        self.download_queue = asyncio.Queue()
        self.process_queue = asyncio.Queue()
        self.send_queue = asyncio.Queue() 


        

    async def start(self):
        asyncio.create_task(self.update_to_download())
        asyncio.create_task(self.download())
        
    async def update_to_download(self):
        current_items = {item["_id"] for item in self.download_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status(DownloadStatus.QUEUED,2)
            if item["_id"] not in current_items  
        ]
        for item in new_items:
            await self.download_queue.put(item)

    async def update_to_process(self):
        current_items = {item["_id"] for item in self.process_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status(DownloadStatus.UPLOADED,1)
            if item["_id"] not in current_items  
        ]
        for item in new_items:
            await self.process_queue.put(item)

    async def update_to_send(self):
        current_items = {item["_id"] for item in self.send_queue._queue}  
        new_items = [
            item for item in await self.db.get_users_with_files_by_status([WatermarkStatus.DONE,WatermarkStatus.ERROR_DONE],2)
            if item["_id"] not in current_items  
        ]
        for item in new_items:
            await self.send_queue.put(item)
        
    async def download(self):
        
        while True:
            async with self.semaphore:
                user = await self.download_queue.get()
                
                for file in user["files"]:
                    path = f"{self.file_path_download}{file['file_id']}.jpg"
                    await self.bot.download_file(file["file_path"], path)

                    file["file_path"] = path
                    file["status"] = DownloadStatus.UPLOADED.value

                    await self.db.update_file_download_fields(user["_id"], file["file_id"], file)

            await asyncio.sleep(60)

    async def process_image(self):
        while True:
            async with self.semaphore:
                user = await self.process_queue.get()
                
                for file in user["files"]:
                    path = f"{self.file_path_download}{file['file_id']}.jpg"
                    
                    text = await OCR.get_text_from_image()
                    caption = await llm.ask_llm(text)
                    watermark.add_watermark()

                    file["file_path"] = path
                    file["status"] = DownloadStatus.UPLOADED.value

                    await self.db.update_file_download_fields(user["_id"], file["file_id"], file)

            await asyncio.sleep(60)
        

    async def send_image(self):
        # TODO
        await self.bot.send_photo()