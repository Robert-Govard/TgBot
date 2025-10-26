import asyncio
from aiogram import F, Bot, Dispatcher, types, exceptions
from aiogram.filters import Command
from loguru import logger
from redis.asyncio import Redis

from settings import settings
from keyboard import Callbacks

# Инициализация бота и Redis
bot = Bot(token=settings.TOKEN.get_secret_value())
dp = Dispatcher()

USER_ID = None

admin_userid = 1247834167


redis = Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=(
        settings.REDIS_PASSWORD.get_secret_value() if settings.REDIS_PASSWORD else None
    ),
)
EX_TIME = 60 * 60 * 24 * 21  # 21 день


async def set_user_id(user_id: int, username: str | None) -> None:
    """
    Асинхронная функция, которая сохраняет сообщения после нажатия кнопки /start
    в таблицу redis

    Args:
    user_id (int): ID пользователя Telegram
    username (str): Имя пользователя Telegram
    """

    try:
        await redis.set(f"{user_id}:{username}", "active", ex=EX_TIME)
        logger.info(f"{user_id} сохранен в redis")
    except Exception as error:
        logger.error(f"При сохранении {user_id} возникла ошибка {error}")

        
@dp.message(Command("start"))
async def handle_start_command(message: types.Message) -> None:
    """
    Функция для получения user id от пользователя

    Args:
    message (types.Message): переменная для записи сообщений от пользователя
    """

    if not message.from_user:
        return
    user_id = message.from_user.id
    username = message.from_user.username

    global USER_ID

    USER_ID = user_id

    await set_user_id(user_id, username) 

    await message.answer(f"Привет {username}! \n"
                         "Что бы бот работал его необходимо добавить в список бизнес ботов твоего профиля! \n\n"
                         "Если бот начал отслежить изменения твоих сообщений, просто введи /start \n")
    logger.warning(f"User {username}:{user_id} started bot")




async def set_message(message: types.Message) -> None:
    """Сохраняет сообщения в Redis, кроме тех, которые были отправлены самими пользователем с истечением через EX_TIME."""
    
    if message.from_user and message.from_user.id == USER_ID:
        logger.info(f"Сообщение от {message.from_user.username}, пропускаем сохранение")
        return
    try:
        await redis.set(
            f"{message.chat.id}:{message.message_id}",
            message.model_dump_json(),
            ex=EX_TIME,
        )
        logger.info("Message Saved")

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
                f"Edited photo by {new_message.from_user.username if new_message.from_user else None}:",
            )
            await new_message.send_copy(settings.USER_ID).as_(bot)
        else:
            await bot.send_message(
                chat_id=settings.USER_ID,
                text=f'Сообщение было изменено\n\nold message:\n<blockquote>{old_message.text}</blockquote>new message: <blockquote>{new_message.text}</blockquote> \nuser: @{new_message.from_user.username if new_message.from_user else None}',
                parse_mode='HTML'
            )

    except Exception as error:
        logger.error(f"Ошибка при сохранении измененного сообщения: {error}")


@dp.deleted_business_messages()
async def deleted_message(business_messages: types.BusinessMessagesDeleted):
    """
    Обработчик удалённых сообщений. Проверяет тип отправленного сообщения, в случае удаления пересылает копию в чат с юзером
    На вход получает сообщение от пользователя - business_messages
    
    old_message - Сообщение которое было удалено

    """
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
            return

        if old_message.photo:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted photo by @{old_message.from_user.username}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.voice:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted voice message by @{old_message.from_user.username}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.video_note:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted video note by @{old_message.from_user.username}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.video:
            await bot.send_message(
                settings.USER_ID,
                f"Deleted video by @{old_message.from_user.username}:",
            )
            await old_message.send_copy(settings.USER_ID).as_(bot)
        if old_message.text:
            await bot.send_message(
                settings.USER_ID,
                f"Удаленное сообщение: <blockquote>{old_message.text}</blockquote>\nuser: @{old_message.from_user.username}",
                parse_mode='HTML'
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
