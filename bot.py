import asyncio
import logging
import help

from aiogram import types
from aiogram.utils.executor import start_polling
from languages import underscore as _
from engine import dp

# logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TrueModer')
loop = asyncio.get_event_loop()
moder = None


async def register_handlers():
    # bot join chat handlers
    dp.register_message_handler(help.welcome, custom_filters=[types.ChatType.is_super_group],
                                content_types=types.ContentType.NEW_CHAT_MEMBERS)

    dp.register_message_handler(help.welcome_group, custom_filters=[types.ChatType.is_group],
                                content_types=types.ContentType.NEW_CHAT_MEMBERS)

    dp.register_message_handler(help.group_migrates_to_supergroup,
                                content_types=types.ContentType.MIGRATE_FROM_CHAT_ID)

    # moderator commands
    dp.register_message_handler(moder.ban, regexp=r'^!.*бан.*', content_types=types.ContentType.TEXT)
    dp.register_message_handler(moder.mute, regexp=r'^!.*мол[ч,к].*', content_types=types.ContentType.TEXT)

    # explicit filter
    dp.register_message_handler(moder.check_explicit, content_types=types.ContentType.TEXT)


@dp.message_handler(types.ChatType.is_private, commands=['start'])
async def start_private(message: types.Message):
    text = _('Привет, я бот-модератор! \n'
             'Добавь меня в чат, чтобы навести там порядок')
    await message.reply(text)


async def on_startup(_):
    from moderator import Moderator
    global moder
    moder = await Moderator.get_instance()
    await register_handlers()


async def on_shutdown(_):
    pass


if __name__ == '__main__':
    start_polling(dp, loop=loop, skip_updates=True, on_startup=on_startup, on_shutdown=on_shutdown)
