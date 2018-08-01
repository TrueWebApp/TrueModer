import logging
from aiogram.types import Chat, User

logger = logging.getLogger(f'TrueModer.{__name__}')


def set_logging_levels():
    logging.getLogger('aiohttp').setLevel(logging.WARNING)
    logging.getLogger('chatbase').setLevel(logging.INFO)


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
