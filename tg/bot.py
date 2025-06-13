import asyncio
from aiogram import Bot, F
from db.statuses import DownloadStatus, WatermarkStatus
from db.mongo_db import AsyncDatabase
from observers.observer import Observer
from aiogram.types import Message
from aiogram import Dispatcher, Router, Bot
from aiogram.filters import Command
from aiogram_media_group import media_group_handler
import logging
from datetime import datetime


logging.basicConfig(level=logging.INFO,
                    format="tg: [%(asctime)s] %(levelname)s: %(message)s",
                    handlers=[logging.FileHandler("tg.log"),
                              logging.StreamHandler()]) 

def setup_handlers(router:Router,bot:Bot,db:AsyncDatabase,observer:Observer):

    @router.message(Command("start"))
    async def start_handler(message: Message):
        try:
            await db.add_user(
                id=message.from_user.id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name
            )

            await message.answer("👋 Привет! Ты был успешно зарегистрирован.")
            logging.info(f"Пользователь {message.from_user.id} начал работу.")
        except Exception as e:
            logging.error(f"Ошибка в start_handler для {message.from_user.id}: {e}")
            await message.answer("❌ Произошла ошибка при регистрации. Попробуй позже.")




    @router.message(
        F.media_group_id,
        F.photo | (F.document & F.document.mime_type.startswith("image/"))
    )
    @media_group_handler
    async def handle_album(messages: list[Message]):
        """Обрабатывает альбом из нескольких изображений"""
        await messages[0].answer(f"🔍 Получен альбом из {len(messages)} изображений...")
        
        success = 0
        for msg in messages:
            try:
                if msg.photo:
                    file_id = msg.photo[-1].file_id
                else:
                    file_id = msg.document.file_id

                file = await msg.bot.get_file(file_id)
                

                success += 1

            except Exception as e:
                logging.error(f"ERROR: {e}")
                await messages[0].answer(f"❌ Не получилось обработать файлы")
        
        await messages[0].answer(f"✅ Сохранено {success}/{len(messages)} изображений")



    @router.message(
        F.photo | (F.document & F.document.mime_type.startswith("image/"))
    )
    async def handle_single_image(message: Message):
        """Обрабатывает одно изображение"""
        await message.answer("🖼 Обрабатываю изображение...")
        
        try:
            if message.photo:
                file_id = message.photo[-1].file_id
            else:
                file_id = message.document.file_id

            file = (await message.bot.get_file(file_id))

            await observer.add_message_with_update(message.from_user.id,message=
                                                   {
                                                       "message_id": message.message_id,
                                                       "files": [
                                                           {
                                                               "file_id": file.file_id,
                                                               "file_path": file.file_path
                                                           }
                                                       ]
                                                   })

        except Exception as e:
            logging.error(f"ERROR: {e}")
            await message.answer(f"❌ Не получилось обработать файлы")




