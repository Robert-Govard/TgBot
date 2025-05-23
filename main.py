import asyncio
import types
from venv import logger

from aiogram import F, Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from redis import Redis 
from loguru import logger

#токен бота + CHAT_ID для пересылки удалёных/измененных сообщений
bot = Bot(token="7952648091:AAHek5j-EREIfUiin6hHAZS59chG92jPED8")
CHAT_ID = 1247834167

dp = Dispatcher()

#Создаем локальную бд для записи сообщений
redis = Redis(
    host="localhost",
    port=6379,
    password=None
)
EX_TIME = 60 * 60 * 24 * 21  # 21 день



# Command handler
@dp.message(Command('start'))
async def command_start_handler(message: Message):
    await message.answer("Hello! I'm a bot created with aiogram.")

#Сохраняем все сообщения
async def set_message(message: types.Message):
    try:
        redis.set(
            f"{message.chat.id}:{message.message_id}",
            message.model_dump_json(),
            ex=EX_TIME,
        )
        logger.info(f"Сообщение было сохранено: {message.chat.id}:{message.message_id}, {message.text}")

    except Exception as error:
        logger.error(f"Ошибка сохранения сообщения: {error}")

#получаем все сообщения
@dp.business_message()
async def handle_message(message: types.Message):
    await set_message(message)





# Run the bot
async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
          