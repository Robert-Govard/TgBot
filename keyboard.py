"""from enum import StrEnum
from aiogram.utils.keyboard import InlineKeyboardBuilder


class Callbacks(StrEnum):
    EMPTY = "empty"
    CLOSE = "close"


def link_markup(user_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="👤", url=f"tg://user?id={user_id}")
    return builder.adjust(3).as_markup()"""