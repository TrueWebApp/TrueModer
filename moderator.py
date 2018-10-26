import asyncio as aio
import logging
import random
import re
from datetime import datetime, timedelta

from aiogram import types, Bot
from aiogram.utils import markdown as md
from aiogram.utils.exceptions import *

from aiochatbase import Chatbase
from antiflood import rate_limit
from languages import underscore as _
from misc import log_repr

logger = logging.getLogger(f'TrueModer.{__name__}')

TEXT = 'text'
ANSWER = 'answer'
TIME = 'time'

jail = {}


class Moderator:
    def __init__(self, bot, cb):
        self._bot: Bot = bot
        self.cb: Chatbase = cb

    @property
    async def me(self):
        return await self._bot.me

    async def say(self, chat_id, text, reply_markup=None, disable_web_page_preview=None):
        """
        Overrides bot.send_message and catches exceptions

        :param chat_id:
        :param text:
        :param reply_markup:
        :param disable_web_page_preview:
        :return: message
        :rtype: Message or None
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

        minutes = re.search(r'^мин|мин[^ ]+', message.text)
        hours = re.search(r'^час|час[^ ]+', message.text)
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
                text = _('Я бы с удовольствием произвёл блокировку, но мне не хватает администраторских прав')
                await self.say(chat_id, text)

            elif 'an administrator of the chat' in str(error):
                logger.debug(f'Зачем-то пытается ограничить админа :)')
                text = _('Я не могу заблокировать админа')
                await self.say(chat_id, text)

            else:
                logger.exception(f'BadRequest: {error}', exc_info=True)
                text = _('Не шмогла :(')
                await self.say(chat_id, text)

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
                    text = _('Я бы с удовольствием произвёл блокировку, но мне не хватает администраторских прав')
                    await self.say(chat.id, text)

                elif 'an administrator of the chat' in str(error):
                    logger.debug(f'Зачем-то пытается ограничить админа :)')
                    text = _('Я не могу заблокировать админа')
                    await self.say(chat.id, text)

                else:
                    logger.exception(f'BadRequest: {error}', exc_info=True)
                    text = _('Я не могу заблокировать админа')
                    await self.say(chat.id, text)

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
                text = _('Не могу я создателя блочить!')
                await self.say(chat_id, text)

            elif "is an administrator of the chat" in str(e):
                logger.debug(f"Restriction: can't demote chat admin at {chat_id}")
                text = _('Не могу я админа блочить!')
                await self.say(chat_id, text)

            elif "Not enough rights to restrict/unrestrict chat member" in str(e):
                logger.warning(f"Not enough rights to restrict/unrestrict chat member at {chat_id}")
                text = _('Я бы с удовольствием произвёл блокировку, но мне не хватает администраторских прав')
                await self.say(chat_id, text)

            else:
                logger.exception(f'Error: \n{e}', exc_info=True)
                text = _('Не шмогла :(')
                await self.say(chat_id, text)

        except RetryAfter:
            logging.error(f'Message limit reached! {RetryAfter}')

        except Unauthorized as e:
            logger.exception(f'Error: \n{e}', exc_info=True)

        except TelegramAPIError as e:
            logger.error(f'Error: \n{e}')

        else:
            return True

    @staticmethod
    async def delete_message(message: types.Message):
        chat = message.chat

        try:
            await message.delete()

        except MessageError as e:
            logger.info(f"Can't delete message in {chat.full_name} ({chat.id}), cause: {e}")

        except TelegramAPIError as e:
            logger.error(f'TelegramAPIError: {e}')

        else:
            return True

    @rate_limit(0.5, 'text')
    async def check_text(self, message: types.Message):
        logger.debug(f'Checking received text: {message.text}')
        await self.check_explicit(message)
        await self.check_link(message)

    @rate_limit(0.5, 'text')
    async def check_explicit(self, message: types.Message):
        from explicit import find_explicit

        text = message.text
        chat = message.chat
        user = message.from_user

        # message without text skip
        if not text:
            return

        # is explicit found?
        result = await find_explicit(text)
        if not result:
            await self.cb.register_message(user_id=user.id, intent='normal message')
            return
        logger.info(f'Found explicit in message: {text}')
        await self.cb.register_message(user_id=user.id, intent='explicit message')

        # let's delete bad message
        await self.delete_message(message)

        # notify user
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

    @rate_limit(0.5, 'link')
    async def check_link(self, message: types.Message):
        """ Find links and @group mentions """

        entities = message.entities
        text = message.text
        chat = message.chat
        user = message.from_user
        bot = message.bot

        for entity in entities:
            logger.debug(f'Checking entity with {entity.type}')
            if entity.type == types.MessageEntityType.URL:
                logger.info('Url found. Deleting. Restricting.')
                await message.delete()
                await self.restrict_user(chat_id=chat.id, user_id=user.id, seconds=5)
                return

            if entity.type == types.MessageEntityType.MENTION:
                name = entity.get_text(text)
                logger.debug(f'Received mention: {name}. Checking...')

                try:
                    mentioned_chat = await bot.get_chat(name)

                except Unauthorized as e:
                    logger.info('@-mention of group found. Deleting. Restricting.')
                    await message.delete()
                    await self.restrict_user(chat_id=chat.id, user_id=user.id, seconds=5)
                    return

                except ChatNotFound:
                    logger.debug('@-mention is user. Nothing to do.')
                    return

                else:
                    logger.info('@-mention of group found. Deleting. Restricting.')
                    if types.ChatType.is_group_or_super_group(mentioned_chat):
                        await message.delete()
                        await self.restrict_user(chat_id=chat.id, user_id=user.id, seconds=5)
                        return
