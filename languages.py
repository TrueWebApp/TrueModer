import logging

logger = logging.getLogger(f'TrueModer.{__name__}')


def underscore(text: str, **kwargs):
    return text.format(**kwargs)

# todo add multilingual support
