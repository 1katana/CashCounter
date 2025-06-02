from services.OCR import run_ocr
from services.llm import ask_llm
from services.watermark import add_watermark
import asyncio
from aiogram import Dispatcher, Router, Bot, F
from const import Const
from db.mongo_db import AsyncDatabase
from aiogram.types import Message
from aiogram.filters import Command
from aiogram_media_group import media_group_handler
import logging


bot = Bot(Const.telegram_token)
dp = Dispatcher()
router = Router()
dp.include_router(router)
db = AsyncDatabase()


logging.basicConfig(level=logging.INFO,
                    format="[%(asctime)s] %(levelname)s: %(message)s",
                    handlers=[logging.FileHandler("tg.log"),
                              logging.StreamHandler()]) 


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

        file = (await message.bot.get_file(file_id)).file_path
        await message.bot.download_file(
            file, 
            Const.file_path_dowload+f"{file_id}."
        )
        await message.answer("✅ Изображение сохранено!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")




# Обработчик для медиагрупп (альбомов)
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
                ext = "jpg"
            else:
                file_id = msg.document.file_id
                ext = msg.document.file_name.split(".")[-1] if "." in msg.document.file_name else "jpg"
            
            file = await msg.bot.get_file(file_id)
            await msg.bot.download_file(
                file.file_path, 
                f"downloads/{file_id}.{ext}"
            )
            success += 1
        except Exception as e:
            print(f"Ошибка: {e}")
    
    await messages[0].answer(f"✅ Сохранено {success}/{len(messages)} изображений")

# Обработчик для одиночных изображений
@router.message(
    F.photo | (F.document & F.document.mime_type.startswith("image/"))
)
async def handle_single_image(message: Message):
    """Обрабатывает одно изображение"""
    await message.answer("🖼 Обрабатываю изображение...")
    
    try:
        if message.photo:
            file_id = message.photo[-1].file_id
            ext = "jpg"
        else:
            file_id = message.document.file_id
            ext = message.document.file_name.split(".")[-1] if "." in message.document.file_name else "jpg"
        
        file = await message.bot.get_file(file_id)
        await message.bot.download_file(
            file.file_path, 
            Const.file_path_dowload+f"{file_id}.{ext}"
        )
        await message.answer("✅ Изображение сохранено!")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")


if __name__ == "__main__":
    dp.run_polling(bot)