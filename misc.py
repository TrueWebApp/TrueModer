import logging
from aiogram import types

logger = logging.getLogger(f'TrueModer.{__name__}')


def set_logging_levels():
    logging.getLogger('aiohttp').setLevel(logging.WARNING)


def log_repr(o):
    """
    Represents object to log view
    :param o:
    :return:
    :rtype: str
    """
    if isinstance(o, types.Chat):
        return f'{o.full_name} ({o.id})'

    if isinstance(o, types.User):
        return f'{o.full_name} ({o.id})'

    return None
