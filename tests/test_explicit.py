import pytest
import logging

from explicit import find_explicit
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TrueModerTest')
pytestmark = pytest.mark.asyncio


async def test_explicit(event_loop):
    """ huy test """
    test_data = (
        'Хуй', 'хуйло', 'бля', 'пиздец'
    )
    for word in test_data:
        txt = f'Какое-то предложение и {word} среди него'
        result = await find_explicit(txt)
        assert result is True


async def test_non_explicit(event_loop):
    """ huy test """
    test_data = (
        'сабля', 'Употреблять', 'рубля', 'злоупотреблять'
    )
    for word in test_data:
        txt = f'Какое-то предложение и {word} среди него'
        result = await find_explicit(txt)
        assert result is False
