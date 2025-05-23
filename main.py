import asyncio
from dbm import dumb
from mailbox import Message
from pydoc import text
from aiogram import F, Bot, Dispatcher, types, exceptions
from loguru import logger
from redis.asyncio import Redis
from typing import Optional

#from keyboard import link_markup


# Инициализация бота и Redis
bot = Bot(token="7952648091:AAHek5j-EREIfUiin6hHAZS59chG92jPED8")
CHAT_ID = 1247834167
dp = Dispatcher()

redis = Redis(
    host="localhost",
    port=6379,
    password=None,
)
EX_TIME = 60 * 60 * 24 * 21  # 21 день



async def set_message(message: types.Message) -> None:
    """Сохраняет сообщение в Redis с истечением через EX_TIME."""

    try:
        await redis.set(
            f"{message.chat.id}:{message.message_id}",
            message.model_dump_json(),
            ex=EX_TIME,
        )
        logger.info(f"Сообщение сохранено: {message.chat.id}:{message.message_id}, {message.text}")

    except Exception as error:
        logger.error(f"Ошибка при сохранении сообщения: {error}")


@dp.business_message()
async def handle_message(message: types.Message) -> None:
    """Обработчик для входящих сообщений."""
    await set_message(message)


@dp.edited_business_message()
async def edited_message(message: types.Message):
    """Обработка, запрись и отправка измененных сообщений"""
    try:
        model_dump = await redis.get(f"{message.chat.id}:{message.message_id}")
        await set_message(message)

        if not model_dump:
            return
        
        original_message = types.Message.model_validate_json(model_dump)
        if not original_message.from_user:
            return
        

        #-----------изменить этот метод-------------#
        await original_message.send_copy( #сделать отправку старых и новых сообщений, подписывать какой пользователь изменил это сообщение
           chat_id=CHAT_ID,
        ).as_(bot)
        #-------------------------------------------#
        
        logger.info(f"Сообщение было изменено: {message.chat.id}:{message.message_id}, {message.text}")
    
    except Exception as error:
        logger.error(f"Ошибка при сохранении измененного сообщения: {error}")


async def copy_message(message: types.Message):
    await message.send_copy(
        chat_id=CHAT_ID,
    ).as_(bot)




# Run the bot
async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
          