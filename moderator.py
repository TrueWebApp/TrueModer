from aiogram.utils.exceptions import BadRequest, Unauthorized, RetryAfter, TelegramAPIError
from aiogram.utils import markdown as md
from aiogram import types, Bot
from datetime import datetime, timedelta
from misc import log_repr
from languages import underscore as _

import asyncio as aio
import logging
import random
import re

logger = logging.getLogger(f'TrueModer.{__name__}')

TEXT = 'text'
ANSWER = 'answer'
TIME = 'time'

jail = {}


class Moderator:
    from engine import bot as _bot
    instance = None

    def __init__(self, bot_user: types.User):
        self.user = bot_user

    @classmethod
    async def get_instance(cls):
        """
        :return: Moderator instance. New or cached.
        :rtype: Moderator
        """
        if isinstance(cls.instance, cls):
            logger.debug('Moderator instance is here!')
            return cls.instance

        if not isinstance(cls._bot, Bot):
            logger.error("There's not Bot here!")
            return

        logger.debug('Creating new moderator instance')
        bot_user = await cls._bot.me
        cls.instance = cls(bot_user)
        return cls.instance

    async def say(self, chat_id, text, reply_markup=None, disable_web_page_preview=None):
        """
        Overrides send message and catches exceptions

        :param chat_id:
        :param text:
        :param reply_markup:
        :param disable_web_page_preview:
        :return:
        """
        try:
            msg = await self._bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup,
                                               disable_web_page_preview=disable_web_page_preview)

        except BadRequest:
            pass

        except Unauthorized:
            pass

        else:
            return msg

    @staticmethod
    async def check_admin(user, chat):
        """
        Check user is admin of chat

        :param user: administrator's user object
        :type user: types.User

        :param chat: chat object
        :type chat: types.Chat

        :return: True if user is admin of chat, else False
        :rtype: bool
        """
        from config import super_admins

        if not isinstance(user, types.User):
            logger.error("There's no User to check rights")
            return False

        if user.id in super_admins:
            return True

        if not isinstance(chat, types.Chat):
            logger.error("There's no Chat to check rights")
            return False

        member = await chat.get_member(user.id)
        if not isinstance(member, types.ChatMember):
            return False

        if member.is_admin():
            return True

        return False

    @staticmethod
    async def get_time(message):
        """
        Parse time from message

        :param message:
        :type message: types.Message
        :return: dict with keys: 'time' and 'text'
        :rtype: dict
        """
        from datetime import timedelta

        result = {}
        time = re.search(r'(\d+)', message.text)  # в сообщении есть числа
        time = time.group() if time else None

        minutes = re.search(r'мин|мин[^ ]+', message.text)
        hours = re.search(r'час', message.text)
        days = re.search(r'дн[^ ]|день|сутки|суток', message.text)
        weeks = re.search(r'недел', message.text)

        if not time:
            if re.search(r'пару', message.text):
                time = 2
            elif re.search(r'несколько', message.text):
                time = random.randint(3, 9)
            else:
                time = 1

        half = re.search(r'\s?пол.*', message.text)
        time = int(time) / 2 if half else int(time)

        if time and minutes:
            result[TEXT] = f'{str(time)} {minutes.group()}'
        elif time and hours:
            result[TEXT] = f'{str(time)} {hours.group()}'
        elif time and days:
            result[TEXT] = f'{str(time)} {days.group()}'
        elif time and weeks:
            result[TEXT] = f'{str(time)} {weeks.group()}'
        else:
            result[TEXT] = f'{str(time)} час.'

        if minutes:
            result[TIME] = timedelta(minutes=float(time))
        elif hours:
            result[TIME] = timedelta(hours=float(time))
        elif days:
            result[TIME] = timedelta(days=float(time))
        elif weeks:
            result[TIME] = timedelta(weeks=float(time))
        else:
            result[TIME] = timedelta(hours=float(time))

        return result

    @staticmethod
    async def check_delete(message):
        """
        Parse delete command from message

        :param message:
        :type message: types.Message
        :return: True if delete command
        :rtype: bool
        """
        delete = re.search(r'[ ]-|-[ ]', message.text)
        return True if delete else False

    async def kick(self, chat_id, user_id, seconds):
        until = int((datetime.now() + timedelta(seconds=seconds)).timestamp())

        try:
            await self._bot.kick_chat_member(chat_id, user_id, until)

        except BadRequest as error:

            if 'not enough rights' in str(error):
                logger.debug('Не хватает прав на совершение действия')

            elif 'an administrator of the chat' in str(error):
                logger.debug(f'Зачем-то пытается ограничить админа :)')

            else:
                logger.exception(f'BadRequest: {error}', exc_info=True)

    async def ban(self, message):
        """
        Executing ban

        :param message:
        :type message: types.Message
        :return: None
        """
        if not isinstance(message, types.Message):
            logger.error("There's no Message with ban request ")
            return

        admin = message.from_user
        chat = message.chat

        logger.info(f'moderator.ban received from {log_repr(admin)} in {log_repr(chat)}')

        # check admin rights
        if not await self.check_admin(admin, chat):
            await message.delete()
            await self.restrict_user(chat_id=chat.id, user_id=admin.id, seconds=30 * 60)
            return

        # check reply to forward
        if not message.reply_to_message:
            await message.reply(f'Эту команду нужно использовать в ответ на чьё-то сообщение')
            return

        abuser = message.reply_to_message.from_user
        if chat and abuser:
            how_long = await self.get_time(message)
            ban_before = int((datetime.now() + how_long.get(TIME)).timestamp())
            need_delete = await self.check_delete(message)

            try:
                await self._bot.kick_chat_member(chat.id, abuser.id, ban_before)

            except BadRequest as error:

                if 'not enough rights' in str(error):
                    logger.debug('Не хватает прав на совершение действия')

                elif 'an administrator of the chat' in str(error):
                    logger.debug(f'Зачем-то пытается ограничить админа :)')

                else:
                    logger.exception(f'BadRequest: {error}', exc_info=True)

            else:
                await self._bot.send_message(chat.id, 'Готово! :)')
                logger.info(f"{admin.full_name} ({admin.id}) "
                            f"ban {abuser.full_name} ({abuser.id}) "
                            f"in {chat.full_name} ({chat.id}) for {how_long.get(TEXT)}")

            if need_delete:
                await self._bot.delete_message(chat.id, message.reply_to_message.message_id)

        else:
            logger.info(f"{admin.first_name} ({admin.id}) "
                        f"хотел кого-то забанить, но не получилось :(")

    async def mute(self, message):
        """
        Executing mute command

        :param message:
        :type message: types.Message
        :return: None
        """
        if not isinstance(message, types.Message):
            logger.error("There's no Message with mute request ")
            return

        admin = message.from_user
        chat = message.chat
        logger.info(f'moderator.mute received from {log_repr(admin)} in {log_repr(chat)}')

        # check admin rights
        if not await self.check_admin(admin, chat):
            await message.delete()
            await self.restrict_user(chat.id, admin.id, seconds=61)
            return

        # check reply to forward
        if not message.reply_to_message:
            return await message.reply(f'Эту команду нужно использовать в ответ на чьё-то сообщение')

        abuser = message.reply_to_message.from_user
        if chat and abuser:
            how_long = await self.get_time(message)
            restrict_before = int((datetime.now() + how_long.get(TIME)).timestamp())
            need_delete = await self.check_delete(message)

            try:
                await self._bot.restrict_chat_member(chat_id=chat.id,
                                                     user_id=abuser.id,
                                                     until_date=restrict_before,
                                                     can_send_messages=False)

            except BadRequest as error:
                if 'not enough rights' in str(error):
                    logger.debug(f'Не хватает прав на совершение действия: {error}')

                elif 'an administrator of the chat' in str(error):
                    logger.debug(f'Зачем-то пытается ограничить админа. {error}')

                else:
                    logger.exception(f'BadRequest: {error}', exc_info=True)

            else:
                await self._bot.send_message(chat.id, 'Готово! :)')
                logger.info(f"{admin.full_name} ({admin.id}) "
                            f"mute {abuser.full_name} ({abuser.id}) "
                            f"in {chat.title} ({chat.id}) at {how_long.get(TEXT)}")

            if need_delete:
                await self._bot.delete_message(chat.id, message.reply_to_message.message_id)

        else:
            logger.info(f"{admin.first_name} ({admin.id}) "
                        f"хотел кого-то заткнуть, но не получилось :(")

    async def restrict_user(self, chat_id, user_id, seconds=61):
        """
        Restriction method with try

        :param chat_id:
        :param user_id:
        :type user_id: int
        :param seconds: int
        :return:
        """
        until = int((datetime.now() + timedelta(seconds=seconds)).timestamp())

        try:
            await self._bot.restrict_chat_member(chat_id, user_id,
                                                 can_send_messages=False,
                                                 can_send_other_messages=False,
                                                 can_add_web_page_previews=False,
                                                 can_send_media_messages=False,
                                                 until_date=until)
        except BadRequest as e:
            if "Can't demote chat creator" in str(e) or "can't demote chat creator" in str(e):
                logger.debug(f"Restriction: can't demote chat creator at {chat_id}")

            elif "is an administrator of the chat" in str(e):
                logger.debug(f"Restriction: can't demote chat admin at {chat_id}")

            elif "Not enough rights to restrict/unrestrict chat member" in str(e):
                logger.debug(f"Not enough rights to restrict/unrestrict chat member at {chat_id}")

            else:
                logger.exception(f'Error: \n{e}', exc_info=True)

        except RetryAfter:
            logging.error(f'Message limit reached! {RetryAfter}')

        except Unauthorized as e:
            logger.exception(f'Error: \n{e}', exc_info=True)

        except TelegramAPIError as e:
            logger.error(f'Error: \n{e}')

    async def check_explicit(self, message: types.Message):
        from explicit import find_explicit

        text = message.text
        chat = message.chat
        user = message.from_user

        # message without text
        if not text:
            return

        # is explicit found?
        result = find_explicit(text)

        if not result:
            return

        try:
            jail[user.id] += 1
        except KeyError:
            jail[user.id] = 1

        user_link = md.hlink(user.full_name, f'tg://user?id={user.id}')

        if jail.get(user.id) <= 2:
            text = _('Ай-ай-ай, {user_link}!', user_link=user_link)
            await self.say(chat.id, text)
            return

        if 2 < jail.get(user.id) < 5:
            text = _('{user_link}, я же тебя предупреждал... Иди молчать.', user_link=user_link)
            await self.say(chat.id, text)
            await aio.sleep(1)
            await self.restrict_user(chat.id, user.id, 5 * 60 * jail.get(user.id))
            return

        if jail.get(user.id) >= 5:
            text = _('{user_link}, я же тебя предупреждал... Иди в бан.', user_link=user_link)
            await self.say(chat.id, text)
            await aio.sleep(1)
            await self.kick(chat.id, user.id, 24 * 60 * 60)
            jail[user.id] = 3
            return
