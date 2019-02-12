import logging

import pytest

from explicit import find_explicit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('TrueModerTest')
pytestmark = pytest.mark.asyncio

GOOD_WORDS = 'сабля', 'Употреблять', 'рубля', 'злоупотреблять', 'не психуй'
BAD_WORDS = 'Хуй', 'хуйло', 'бля', 'пиздец'


@pytest.fixture(params=GOOD_WORDS)
def good_word(request):
    return request.param


@pytest.fixture(params=BAD_WORDS)
def bad_word(request):
    return request.param


async def test_non_explicit(good_word):
    """ huy test """
    txt = f'Какое-то предложение и {good_word} среди него'
    result = await find_explicit(txt)
    assert result is False


async def test_explicit(bad_word):
    """ huy test """
    txt = f'Какое-то предложение и {bad_word} среди него'
    result = await find_explicit(txt)
    assert result is True



