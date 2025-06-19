import asyncio
from aiogram import Bot, F
from db.statuses import DownloadStatus, WatermarkStatus
from db.mongo_db import AsyncDatabase
from observers.observer import Observer
from aiogram.types import Message, CallbackQuery
from aiogram import Dispatcher, Router, Bot
from aiogram.filters import Command
from aiogram_media_group import media_group_handler
from tg.stategroup import ConfigEdit, config_inline_keyboard
from aiogram.fsm.context import FSMContext  
from aiogram.types import BotCommand
from aiogram.enums import ParseMode
import logging

logger = logging.getLogger(__name__)

async def set_default_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="Запустить бота"),
        BotCommand(command="config", description="Настроить водяной знак"),
        BotCommand(command="help", description="Справка"),
    ]
    await bot.set_my_commands(commands)

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

            await message.answer("👋 <b>Привет!</b> Ты был успешно зарегистрирован.\n\n"
                                 "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
                "📥 Просто отправь изображения, и бот обработает их: распознает текст (OCR), добавит водяной знак и сформирует подпись с помощью ИИ.\n\n"
                "⚙️ <b>Настройка водяного знака:</b>\n"
                "Используй команду /config, чтобы изменить:\n"
                "• <b>text</b> — текст водяного знака\n"
                "• <b>color</b> — цвет (в формате RGBA, например: 255,255,255,128)\n"
                "• <b>font_size</b> — размер шрифта\n"
                "• <b>line_spacing</b> — межстрочный интервал\n"
                "• <b>angle</b> — угол наклона текста\n\n",
                parse_mode=ParseMode.HTML
            )
            logger.info(f"Пользователь {message.from_user.id} начал работу.")
        except Exception as e:
            logger.error(f"Ошибка в start_handler для {message.from_user.id}: {e}")
            await message.answer("❌ Произошла ошибка при регистрации. Попробуй позже.")

    @router.message(Command("help"))
    async def help_handler(message: Message):
        try:
            await message.answer(
                "ℹ️ <b>Как пользоваться ботом:</b>\n\n"
                "📥 Просто отправь изображения, и бот обработает их: распознает текст (OCR), добавит водяной знак и сформирует подпись с помощью ИИ.\n\n"
                "⚙️ <b>Настройка водяного знака:</b>\n"
                "Используй команду /config, чтобы изменить:\n"
                "• <b>text</b> — текст водяного знака\n"
                "• <b>color</b> — цвет (в формате RGBA, например: 255,255,255,128)\n"
                "• <b>font_size</b> — размер шрифта\n"
                "• <b>line_spacing</b> — межстрочный интервал\n"
                "• <b>angle</b> — угол наклона текста",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Ошибка в help_handler для {message.from_user.id}: {e}")
            await message.answer("❌ Произошла ошибка. Попробуй позже.")


    @router.message(Command("config"))
    async def config_handler(message: Message, state: FSMContext):

        pop_list = [
            "font_family",
            "font_style",
            "text_weight"
        ]
        try:
            user_id = message.from_user.id
            config = (await db.get_configuration(user_id))["config"]

            for key in pop_list:
                config.pop(key)

            await message.answer("🛠 Настройки водяного знака:", 
                         reply_markup=config_inline_keyboard(config))
        except Exception as e:
            logger.error(f"Ошибка в config_handler: {e}")
            await message.answer("❌ Произошла ошибка при настройки конфигурации. Попробуйте позже.")

    @router.callback_query(F.data.startswith("edit_"))
    async def config_edit_callback(callback:CallbackQuery,state:FSMContext):
        key = callback.data.removeprefix("edit_")
        await state.update_data(key=key)
        await callback.message.answer(f"Введите новое значение для параметра `{key}`:")
        await state.set_state(ConfigEdit.waiting_for_value)
        await callback.answer()

    @router.message(ConfigEdit.waiting_for_value)
    async def config_edit_value(message: Message, state: FSMContext):
        user_id = message.from_user.id
        value_raw = message.text.strip()
        user_data = await state.get_data()
        key = user_data["key"]

        if key == "color":

            parts = value_raw.replace(', ', ' ').replace(',', ' ').split()

            if len(parts) != 4:
                raise ValueError("Ожидается 4 компонента: R, G, B, A (например: 255 255 255 128)")
            try:
                value = [int(x) for x in parts]
            except ValueError:
                raise ValueError("Все компоненты цвета должны быть целыми числами.")

        elif key in ["font_size", "line_spacing", "angle"]:
            try:
                value = int(value_raw)
            except ValueError:
                raise ValueError(f"Ожидалось целочисленное значение для параметра '{key}'.")
        else:
            value = value_raw
        try:
            success = await db.update_configuration(user_id, key, value)
            if success:
                await message.answer(f"✅ Параметр `{key}` обновлён.")
            else:
                await message.answer("❌ Не удалось сохранить настройку.")

            await state.clear()
        except Exception as e:
            await message.answer("❌ Не удалось сохранить настройку.")


    @router.message(
        F.media_group_id,
        F.photo | (F.document & F.document.mime_type.startswith("image/"))
    )
    @media_group_handler
    async def handle_album(messages: list[Message]):
        """Обрабатывает альбом из нескольких изображений"""
        try:
            await messages[0].answer(f"🔍 Получен альбом из {len(messages)} изображений...")
            
            success = 0
            user_id = messages[0].from_user.id
            message_id = messages[0].message_id
            files = []

            for msg in messages:
                
                if msg.photo:
                    file_id = msg.photo[-1].file_id
                else:
                    file_id = msg.document.file_id

                file = await msg.bot.get_file(file_id)
                
                files.append({
                                "file_id": file.file_id,
                                "file_path": file.file_path
                            })
                

                success += 1

                

            await observer.add_message_with_update(user_id,message=
                                                        {
                                                            "message_id": message_id,
                                                            "files": files
                                                        })
            
            await messages[0].answer(f"✅ Сохранено {success}/{len(messages)} изображений")

        except Exception as e:
                logger.error(f"ERROR: {e}")
                await messages[0].answer(f"❌ Не получилось обработать файлы")



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
            logger.error(f"ERROR: {e}")
            await message.answer(f"❌ Не получилось обработать файлы")




