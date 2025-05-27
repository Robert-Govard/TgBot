import asyncio
from aiogram import F, Bot, Dispatcher, types, exceptions
from aiogram.types import Message
from aiogram.filters import Command
from loguru import logger
from redis.asyncio import Redis

from settings import settings
from keyboard import Callbacks

# Инициализация бота и Redis
bot = Bot(token=settings.TOKEN.get_secret_value())
dp = Dispatcher()

redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=(
        settings.REDIS_PASSWORD.get_secret_value() if settings.REDIS_PASSWORD else None
    ),
)
EX_TIME = 60 * 60 * 24 * 21  # 21 день

@dp.message(Command("start"))
async def get_user_id(message: Message):
    try:
        await message.answer(f"your user id: {message.from_user.id if message.from_user else None}") 
        return message.from_user.id if message.from_user else None
    
    except Exception as error:
        logger.error(f"Ошибка в получении user id: {error}")

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
                return "Photo", (
                    message.from_user.first_name if message.from_user else None
                )
            return message.text, (
                message.from_user.first_name if message.from_user else None
            )

        logger.info(
            f"Сообщение сохранено: {message.chat.id}:{message.message_id}, {isPhoto(message)}"
        )

    except Exception as error:
        logger.error(f"Ошибка при сохранении сообщения: {error}")


@dp.business_message()
async def handle_message(message: types.Message) -> None:
    """Обработчик для входящих сообщений."""
    return await set_message(message)


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

        if new_message.photo:
            await bot.send_message(
                settings.USER_ID,
                f"Edited photo by {new_message.from_user.first_name if new_message.from_user else None}:",
            )
            await new_message.send_copy(settings.USER_ID).as_(bot)
        else:
            await bot.send_message(
                chat_id=settings.USER_ID,
                text=f'Сообщение было изменено\n\nold message:\n<blockquote>{old_message.text}</blockquote>new message: <blockquote>{new_message.text}</blockquote> \nuser: {new_message.from_user.first_name if new_message.from_user else None}',
                parse_mode='HTML'
            )

        logger.info(
            f"Сообщение было изменено: {new_message.chat.id}:{new_message.message_id}"
        )

    except Exception as error:
        logger.error(f"Ошибка при сохранении измененного сообщения: {error}")


@dp.deleted_business_messages()
async def deleted_message(business_messages: types.BusinessMessagesDeleted):
    pipe = redis.pipeline()
    for message_id in business_messages.message_ids:
        pipe.get(f"{business_messages.chat.id}:{message_id}")
    messages_data = await pipe.execute()

    keys_to_delete = []
    for message_id, model_dump in zip(business_messages.message_ids, messages_data):
        if not model_dump:
            continue

        old_message = types.Message.model_validate_json(model_dump)
        if not old_message.from_user:
            continue

        if old_message.photo:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted photo by {old_message.from_user.first_name}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.voice:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted voice message by {old_message.from_user.first_name}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.video_note:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted video note by {old_message.from_user.first_name}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.video:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted video by {old_message.from_user.first_name}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.text:
            await bot.send_message(
                settings.USER_ID,
                f"Удаленное сообщение: {old_message.text}\nuser: {old_message.from_user.first_name}",
            )

        try:
            logger.info(f"Сообщение было удалено: {old_message.text}")
        except exceptions.TelegramRetryAfter as exp:
            logger.warning(f"Retry after {exp.retry_after} seconds")
            logger.error(f"Сообщение было удалено, но возникла ошибка: {exp}")
            await asyncio.sleep(exp.retry_after + 0.1)
        finally:
            await asyncio.sleep(0.1)

        keys_to_delete.append(f"{business_messages.chat.id}:{message_id}")

    if keys_to_delete:
        await redis.delete(*keys_to_delete)


@dp.callback_query(F.data == Callbacks.EMPTY)
async def empty(query: types.CallbackQuery):
    await query.answer()


@dp.callback_query(F.data == Callbacks.CLOSE)
async def close(query: types.CallbackQuery):
    await query.answer()
    if isinstance(query.message, types.Message):
        await query.message.delete()

# Run the bot
async def main() -> None:
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
