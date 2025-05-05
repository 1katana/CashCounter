from services.OCR import main
from services.llm import ask_llm
import asyncio
import os
from aiogram import Bot, Dispatcher, types,F
import aiofiles
from aiogram.filters import Command
from const import Const


bot = Bot(token=Const.telegram_token)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    
    await message.answer(
        "📷 Отправьте мне фото для обработки. "
    )

@dp.message(F.photo)
async def image_handler(message: types.Message):
    await message.answer("Обработка фото...")    
    os.makedirs(os.path.dirname(Const.file_path_dowload), exist_ok=True)
    
    photo = message.photo[-1]
    
    file = await bot.get_file(photo.file_id)
    file_path = os.path.join(Const.file_path_dowload, photo.file_id + ".jpg")
    await bot.download_file(file.file_path, file_path)
    
@dp.message(F.media_group)
async def handle_album(message: types.Message, album: list[types.Message]):
    """Обработка альбома фото."""
    user_id = message.from_user.id
    processed_files = []
    
    for idx, msg in enumerate(album):
        if msg.photo:
            file_path = await download_photo(msg, user_id, idx)
            
async def download_photo(message: types.Message, user_id: int, index: int):
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = os.path.join(Const.file_path_dowload, file.file_id + ".jpg")
    await bot.download_file(file.file_path, file_path)
    return file_path
    

if __name__ == "__main__":
    dp.run_polling(bot)

# image_paths = [
#         "images/dowload/1595227146122330398.jpg",
#         "images/dowload/1655786266185834359.jpg",
#     ]

# async def Main():
    
#     checks = await main(image_paths)
#     print("Checks: ", checks)
    
#     ask_llm_result = await ask_llm("\n".join(check for check in checks if check))
#     print("LLM Result: ", ask_llm_result)
    
# asyncio.run(Main())