import asyncio

from aiogram import types
from aiogram.dispatcher import CancelHandler, DEFAULT_RATE_LIMIT, ctx
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.utils import context
from aiogram.utils.exceptions import Throttled
from languages import underscore as _


FLOOD_LOCK_MESSAGE = _('<b>Не надо флудить!</b>')
FLOOD_MUTE_TIME = 120  # seconds


def rate_limit(limit: float, key=None):
    """
    Decorator for configuring rate limit and key in different functions.

    :param limit:
    :param key:
    :return:
    """

    def decorator(func):
        setattr(func, 'throttling_rate_limit', limit)
        if key:
            setattr(func, 'throttling_key', key)
        return func

    return decorator


class ThrottlingMiddleware(BaseMiddleware):
    """
    Simple middleware
    """

    def __init__(self, limit=DEFAULT_RATE_LIMIT, key_prefix='antiflood_'):
        self.rate_limit = limit
        self.prefix = key_prefix
        super(ThrottlingMiddleware, self).__init__()

    async def on_process_message(self, message: types.Message):
        """
        This handler is called when dispatcher receives a message

        :param message:
        """
        # Get current handler
        handler = context.get_value('handler')

        # Get dispatcher from context
        dispatcher = ctx.get_dispatcher()

        # If handler was configured, get rate limit and key from handler
        if handler:
            limit = getattr(handler, 'throttling_rate_limit', self.rate_limit)
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            limit = self.rate_limit
            key = f"{self.prefix}_message"

        # Use Dispatcher.throttle method.
        try:
            await dispatcher.throttle(key, rate=limit)
        except Throttled as t:
            # Execute action
            await self.message_throttled(message, t)

            # Cancel current handler
            raise CancelHandler()

    async def message_throttled(self, message: types.Message, throttled: Throttled):
        """
        Notify user only on first exceed and notify about unlocking only on last exceed

        :param message:
        :param throttled:
        """
        from engine import moder

        chat = message.chat
        user = message.from_user
        handler = context.get_value('handler')
        dispatcher = ctx.get_dispatcher()

        if handler:
            key = getattr(handler, 'throttling_key', f"{self.prefix}_{handler.__name__}")
        else:
            key = f"{self.prefix}_message"

        # Calculate how many time is left till the block ends
        delta = throttled.rate - throttled.delta

        # Prevent flooding
        if throttled.exceeded_count <= 2:
            await moder.restrict_user(chat.id, user.id, FLOOD_MUTE_TIME)
            await message.reply(FLOOD_LOCK_MESSAGE)

        # Sleep.
        await asyncio.sleep(delta)

        # Check lock status
        thr = await dispatcher.check_key(key)

        # # If current message is not last with current key - do not send message
        # if thr.exceeded_count == throttled.exceeded_count:
        #     await message.reply('Unlocked.')
