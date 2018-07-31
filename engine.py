import logging
import asyncio
import config
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import context
from aiochatbase import Chatbase
from moderator import Moderator

logger = logging.getLogger(f'TrueModer.{__name__}')
loop = asyncio.get_event_loop()
loop.set_task_factory(context.task_factory)


def get_proxy_data():
    if config.PROXY_URL and config.PROXY_LOGIN and config.PROXY_PASSWORD:
        proxy = config.PROXY_URL
        if proxy.startswith('socks5'):
            import aiosocksy
            logger.debug('Socks5 proxy enabled.')
            proxy_auth = aiosocksy.Socks5Auth(login=config.PROXY_LOGIN, password=config.PROXY_PASSWORD)
        else:
            import aiohttp
            logger.debug('HTTP proxy enabled.')
            proxy_auth = aiohttp.BasicAuth(login=config.PROXY_LOGIN, password=config.PROXY_PASSWORD)
    else:
        logger.debug('Proxy disabled.')
        proxy = None
        proxy_auth = None

    return proxy, proxy_auth


# vars and instances
url, auth = get_proxy_data()
bot = Bot(token=config.TELEGRAM_TOKEN, loop=loop, proxy=url, proxy_auth=auth, parse_mode=types.ParseMode.HTML)
dp = Dispatcher(bot, storage=MemoryStorage(), run_tasks_by_default=True)
cb = Chatbase(api_key=config.CHATBASE_KEY, loop=loop, platform='Telegram', task_mode=True)
moder = Moderator(bot)
