import logging
from datetime import datetime

import telebot
import utils
import config

TELEGRAM_TOKEN: str = utils.load_confidentials_from_env("TELEGRAM_TOKEN")
ADMIN_ID: str = utils.load_confidentials_from_env("ADMIN_ID")

utils.initialize_logging()


class BetBot(telebot.TeleBot):

    def __init__(self, db):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode='HTML')
        self.db = db
        self.register_message_handler(commands=['start'], callback=self._handle_start, func=self.message_filter)
        self.register_message_handler(callback=self.handle_message, func=self.message_filter)
        self.start()

    def start(self) -> None:
        self.notify_admin("<b>БОТ ЗАПУЩЕН</b>")
        try:
            self.polling(none_stop=True)
        except Exception as e:
            logging.exception(repr(e))
            self.notify_admin(f"<b>БОТ ОСТАНОВЛЕН</b>\n\nНеожиданная ошибка: {e}")
        else:
            self.notify_admin("<b>БОТ ОСТАНОВЛЕН</b>\n\nВозможная причина: принудительное завершение из IDE.")

    def send_message(self, *args, **kwargs):
        chat_id = kwargs.get('chat_id', args[0] if args else None)
        user_blocked_bot = self._check_bot_block(chat_id)
        try:
            if user_blocked_bot:
                print('Attempting to send a message to user who blocked the bot...')
            super().send_message(*args, **kwargs)
            if user_blocked_bot:
                print('Success! User has unblocked the bot!')
                self._mark_bot_unblock(chat_id)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 403:  # 'error_code': 403, 'description': 'Forbidden: bot was blocked by the user'
                print('Failed! Bot is blocked by user...')
                if not user_blocked_bot:
                    self._mark_bot_block(chat_id)
                logging.exception(repr(e))
                return
            else:
                logging.exception(repr(e))
                raise e  # Re-raise the exception if it is a different error

    def notify_admin(self, text: str) -> None:
        prefix = datetime.now().strftime(config.PREFERRED_DATETIME_FORMAT) + "\n"
        try:
            self.send_message(chat_id=ADMIN_ID, text=prefix + text, parse_mode='HTML')
        except Exception as e:
            logging.exception(repr(e))

    def handle_message(self, message: telebot.types.Message) -> None:
        """Handles all text messages received by auth users."""
        text = f"A message has been received\n" \
               f"Sender: {message.from_user.first_name} {message.from_user.last_name}\n" \
               f"Text: {message.text}\n" \
               f"Message type: {message.content_type}"
        self.reply_to(message, text)

    def message_filter(self, message: telebot.types.Message) -> bool:
        """
        Filter for all messages coming from users. Declines unauthorized users and all non-text messages.
        Sends replies describing the situation to message senders.

        :param message: The incoming message object from a user.
        :return: True if a message is allowed to be processed by the bot, False otherwise.
        """

        message_is_text = message.content_type == 'text'

        if not self._user_authorized(message.from_user.id):
            self.reply_to(message=message,
                          text=f"<b>Доступ запрещен!</b>\n\n"
                               f"К сожалению, это закрытое соревнование, и Вы не являетесь его участником. 😢")
            return False
        elif not message_is_text:
            self.reply_to(message=message, text=f"<b>Ой!</b>\nЭтот бот понимает только текстовые сообщения.")
            return False
        else:
            return True

    def _check_prev_usage(self, message: telebot.types.Message) -> None:
        telegram_id = message.from_user.id
        already_used_bot = self.db.check_prev_usage(telegram_id)
        if not already_used_bot:
            self.db.set_used_bot(telegram_id)

    def _handle_start(self, message) -> None:
        self._check_prev_usage(message)
        self.reply_to(message, 'You used /start command!')

    def _user_authorized(self, user_id: int) -> bool:
        return self.db.get_user(user_id) is not None

    def _user_registered(self, user_id: int) -> bool:
        return self.db.get_user(user_id).chat_id is not None

    def _register_user(self, telegram_id: int, chat_id: int) -> None:
        self.db.register_user(telegram_id, chat_id)

    def _check_bot_block(self, telegram_id: int) -> bool:
        return self.db.check_bot_block(telegram_id)

    def _mark_bot_block(self, telegram_id: int) -> None:
        self.db.mark_bot_block(telegram_id)

    def _mark_bot_unblock(self, telegram_id: int) -> None:
        self.db.mark_bot_unblock(telegram_id)


if __name__ == "__main__":
    from db import Database

    db = Database()
    bot = BetBot(db)
