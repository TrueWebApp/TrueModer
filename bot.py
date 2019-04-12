import asyncio

from aiogram import types
from aiogram.utils.executor import start_polling, start_webhook

import config
import help
from antiflood import ThrottlingMiddleware
from engine import dp, moder, bot, cb
from languages import underscore as _
from misc import setup_logger

logger = setup_logger()
loop = asyncio.get_event_loop()


@dp.errors_handler()
async def errors_handler(dispatcher, update, exception):
    """
    Exceptions handler. Catches all exceptions within task factory tasks.

    :param dispatcher:
    :param update:
    :param exception:
    :return: stdout logging
    """
    from aiogram.utils.exceptions import Unauthorized, InvalidQueryID, TelegramAPIError, \
        CantDemoteChatCreator, MessageNotModified, MessageToDeleteNotFound

    if isinstance(exception, CantDemoteChatCreator):
        logger.debug("Can't demote chat creator")
        return

    if isinstance(exception, MessageNotModified):
        logger.debug('Message is not modified')
        return

    if isinstance(exception, MessageToDeleteNotFound):
        logger.debug('Message to delete not found')
        return

    if isinstance(exception, Unauthorized):
        logger.info(f'Unauthorized: {exception}')
        return

    if isinstance(exception, InvalidQueryID):
        logger.exception(f'InvalidQueryID: {exception} \nUpdate: {update}')
        return

    if isinstance(exception, TelegramAPIError):
        logger.exception(f'TelegramAPIError: {exception} \nUpdate: {update}')
        return

    logger.exception(f'Update: {update} \n{exception}')


@dp.message_handler(types.ChatType.is_private, commands=['start', 'help'])
async def start_private(message: types.Message):
    """
    Handle start and help commands in private chat

    :param message:
    :return:
    """
    text = _('<b>Привет, я бот-модератор!</b> \n'
             'Добавь меня в чат, чтобы навести там порядок')

    markup = types.InlineKeyboardMarkup()
    add_group = f'https://telegram.me/{config.BOT_NAME[1:]}?startgroup=true'
    markup.add(types.InlineKeyboardButton(text=f'Добавить модератора в чат', url=add_group))
    await message.reply(text, reply_markup=markup, reply=False)


TYPES_TO_DELETE = types.ContentType.STICKER + types.ContentType.VIDEO_NOTE + types.ContentType.VIDEO + \
                  types.ContentType.DOCUMENT + types.ContentType.CONTACT + types.ContentType.PHOTO + \
                  types.ContentType.GAME + types.ContentType.ANIMATION


@dp.message_handler(types.ChatType.is_super_group, content_types=TYPES_TO_DELETE)
async def delete_media(message: types.Message):
    user = message.from_user
    chat = message.chat

    if user.id in config.super_admins:
        return

    await message.delete()
    logger.info(f'Deleted message from {user.full_name} ({user.id}) in {chat.full_name} ({chat.id})')


async def register_handlers():
    """
    Function-container with registering external (non-decorated) handlers
    Don't forget about order of registered handlers! It really matters!
    :return: None
    """
    # bot join chat handlers
    dp.register_message_handler(help.welcome, custom_filters=[types.ChatType.is_super_group],
                                content_types=types.ContentType.NEW_CHAT_MEMBERS)

    dp.register_message_handler(help.welcome_group, custom_filters=[types.ChatType.is_group],
                                content_types=types.ContentType.NEW_CHAT_MEMBERS)

    dp.register_message_handler(help.group_migrates_to_supergroup,
                                content_types=types.ContentType.MIGRATE_FROM_CHAT_ID)

    # moderator commands
    # dp.register_message_handler(moder.ban, regexp=r'^!.*бан.*', content_types=types.ContentType.TEXT)
    # dp.register_message_handler(moder.mute, regexp=r'^!.*мол[ч,к].*', content_types=types.ContentType.TEXT)

    # text filter
    dp.register_message_handler(moder.check_text, custom_filters=[types.ChatType.is_super_group],
                                content_types=types.ContentType.TEXT)


async def on_startup(dispatcher):
    """
    Auto exec function on startup of your app

    :param dispatcher: dispatcher
    :return: None
    """
    await register_handlers()
    dispatcher.middleware.setup(ThrottlingMiddleware(limit=0))

    if config.WEBHOOK:
        await bot.set_webhook(config.WEBHOOK_URL)


async def on_shutdown(_):
    """
    Auto exec function on shutdown of your app

    :param _: dispatcher
    :return: None
    """
    await bot.close()
    await cb.close()
    await asyncio.sleep(0.250)


if __name__ == '__main__':
    if config.WEBHOOK:
        start_webhook(dp, webhook_path=config.WEBHOOK_PATH, loop=loop, skip_updates=True, on_startup=on_startup,
                      on_shutdown=on_shutdown, host=config.WEBAPP_HOST, port=config.WEBAPP_PORT)
    else:
        start_polling(dp, loop=loop, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
