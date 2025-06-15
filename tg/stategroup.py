from aiogram.fsm.state import StatesGroup, State
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup



class ConfigEdit(StatesGroup):
    waiting_for_value = State()

def config_inline_keyboard(config:dict) -> InlineKeyboardButton:
    buttons = [
        [InlineKeyboardButton(text=f"📝 {key}: {value}",callback_data=f"edit_{key}")]
        for key, value in config.items()
    ]

    return InlineKeyboardMarkup(inline_keyboard=buttons)