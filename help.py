from aiogram import types
from languages import underscore as _
from engine import moder
import config
import logging

logger = logging.getLogger(f'TrueModer.{__name__}')


async def welcome(message: types.Message):
    """
    Welcomes self and say HELP
    Said welcome message if enabled

    """
    chat = message.chat
    new_users = message.new_chat_members

    # a little delay before welcome
    await types.ChatActions.typing(sleep=2)

    # say help when bot added to new chat
    if await moder.me in new_users:
        logger.info(f'TrueModer added to chat {chat.full_name} ({chat.id})')
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text=f'ℹ️ Описание', url=config.FAQ_LINK))
        text = _(f"<b>Привет! Я бот-модератор!</b> \n\n"
                 f"Чтобы я смог следить за этой группой, мне нужно дать следующие права администратора: \n"
                 f"- удалять сообщения; \n"
                 f"- блокировать пользователей; \n"
                 f"- закреплять сообщения. \n\n"
                 f"Подробности в описании:")
        await moder.say(chat.id, text, reply_markup=markup)


async def welcome_group(message: types.Message):
    """ Said that bot can works only in super groups """

    chat = message.chat
    new_users = message.new_chat_members

    # a little delay before welcome
    await types.ChatActions.typing(sleep=2)

    if await moder.me in new_users:
        logger.info(f'Bot added to group chat {chat.full_name} ({chat.id})')

        text = (f"<b>Привет! Я бот-модератор!</b> \n\n"
                f"Я умею работать только в <i>супергруппах</i> \n"
                f"Преобразовать эту группу в супергруппу можно в настройках группы.")
        await moder.say(chat.id, text)


async def group_migrates_to_supergroup(message: types.Message):
    chat = message.chat

    logger.info(f'Group {message.migrate_from_chat_id} migrated to supergroup {chat.id}')

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton(text=f'ℹ️ Инструкция', url=config.FAQ_LINK))
    text = _(f"<b>Отлично!</b> \n\n"
             f"Теперь для начала работы требуется дать мне следующие права администратора: \n"
             f"- удалять сообщения; \n"
             f"- блокировать пользователей \n"
             f"- закреплять сообщения. \n\n"
             f"Подробности в разделе Установка:")
    await moder.say(chat.id, text, reply_markup=markup)
