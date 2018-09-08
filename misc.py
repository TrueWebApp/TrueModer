import logging
import config
import sys
from aiogram.types import Chat, User

logger = logging.getLogger(f'TrueModer.{__name__}')


def setup_logger():
    logging.basicConfig(format='%(asctime)s | %(name)s:%(lineno)d | %(levelname)s | %(message)s',
                        level=config.LOGGING_LEVEL, stream=sys.stdout)

    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('chatbase').setLevel(logging.INFO)

    return logging.getLogger('TrueModer')


def log_repr(o):
    """
    Represents object to log view
    :param o:
    :type o: Chat or User
    :return:
    :rtype: str
    """
    if isinstance(o, Chat):
        return f'{o.full_name} ({o.id})'

    if isinstance(o, User):
        return f'{o.full_name} ({o.id})'

    return None
