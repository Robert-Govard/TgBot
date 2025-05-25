import asyncio
from email import message
from aiogram import Bot, Dispatcher, types
from loguru import logger
from redis.asyncio import Redis

# from keyboard import link_markup


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

        def isPhoto(message: types.Message):
            if message.photo:
                return "Photo"
            return message.text

        logger.info(
            f"Сообщение сохранено: {message.chat.id}:{message.message_id}, {isPhoto(message)}"
        )

    except Exception as error:
        logger.error(f"Ошибка при сохранении сообщения: {error}")


@dp.business_message()
async def handle_message(message: types.Message) -> None:
    """Обработчик для входящих сообщений."""
    await set_message(message)


@dp.edited_business_message()
async def edited_message(new_message: types.Message):
    """
    Обработка, запрись и отправка измененных сообщений

    new_message - полученное новое сообщение, после изменений
    old_message - старое сообщение, до изменений
    """

    try:
        model_dump = await redis.get(f"{new_message.chat.id}:{new_message.message_id}")
        await set_message(new_message)
        if not model_dump:
            return

        # старое сообщение(до изменений)
        old_message = types.Message.model_validate_json(model_dump)
        if not old_message.from_user:
            return

        # -----------изменить этот метод-------------#
        await bot.send_message(CHAT_ID, "help")
        #await old_message.send_copy(chat_id=CHAT_ID).as_(bot)

        # -------------------------------------------#

        #проверка является ли сообщение фотографией, если да, то возвращается лог что это фото
        def isPhoto(message: types.Message):
            if message.photo:
                return "Photo"
            return message.text

        logger.info(
            f"Сообщение было изменено: {new_message.chat.id}:{new_message.message_id}, {isPhoto(new_message)}"
        )

    except Exception as error:
        logger.error(f"Ошибка при сохранении измененного сообщения: {error}")


# сделать сохранение удалённых сообщений, сделать сохранение фотографий и кружков


# Run the bot
async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
