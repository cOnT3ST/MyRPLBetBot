import logging
from datetime import datetime
import string

import telebot
import utils
import config
from users import User
from bet_input_sessions import BetInputSession

TELEGRAM_TOKEN: str = utils.load_confidentials_from_env("TELEGRAM_TOKEN")
ADMIN_ID: str = utils.load_confidentials_from_env("ADMIN_ID")

utils.initialize_logging()


class BetBot(telebot.TeleBot):

    def __init__(self, db):
        super().__init__(token=TELEGRAM_TOKEN, parse_mode='HTML')
        self.db = db
        self.users: list[User] | None = None
        self._active_sessions: dict[int: BetInputSession] | None = None

        self.register_message_handler(commands=['start'], callback=self._handle_start, func=self._message_filter)
        self.register_message_handler(callback=self._handle_bet_input, func=self._bet_filter)
        self.register_message_handler(callback=self._handle_message, func=self._message_filter)

        self._get_registered_users()
        self.start()

    def start(self) -> None:
        self.notify_admin("<b>БОТ ЗАПУЩЕН</b>")
        self._request_bets()
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
            super().send_message(*args, **kwargs)
            if user_blocked_bot:
                self._mark_bot_unblocked(chat_id)
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 403:  # 'error_code': 403, 'description': 'Forbidden: bot was blocked by the user'
                if not user_blocked_bot:
                    self._mark_bot_blocked(chat_id)
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

    def _handle_message(self, message: telebot.types.Message) -> None:
        """A handler func for all text messages received by auth users."""
        text = f"A message has been received\n" \
               f"Sender: {message.from_user.first_name} {message.from_user.last_name}\n" \
               f"Text: {message.text}\n" \
               f"Message type: {message.content_type}"
        self.reply_to(message, text)

    def _message_filter(self, message: telebot.types.Message) -> bool:
        """
        Filter for all messages coming from users. Declines unauthorized users and all non-text messages.
        Sends replies describing the situation to message senders.

        :param message: The incoming message object from a user.
        :return: True if a message is allowed to be processed by the bot, False otherwise.
        """

        message_is_text = message.content_type == 'text'

        if not self._user_allowed(message.from_user.id):
            self.reply_to(message=message,
                          text=f"<b>Доступ запрещен!</b>\n\n"
                               f"К сожалению, это закрытое соревнование, и Вы не являетесь его участником. 😢")
            return False
        elif not message_is_text:
            self.reply_to(message=message, text=f"<b>Ой!</b>\nЭтот бот понимает только текстовые сообщения.")
            return False
        else:
            return True

    def _bet_filter(self, message: telebot.types.Message) -> bool:
        """
        This filter defines if a message is a bet: i.e., was received during active bet session.
        :param message: The incoming message object from a user.
        :return: True if a message is a bet, False otherwise.
        """
        if not self._bet_session_active(message.from_user.id):
            return False
        return True

    def _ensure_user_registration(self, message: telebot.types.Message) -> None:
        """
        Ensures that the user is registered in the database.
        Checks if a user is registered i.e., has already interacted with the bot at least once. If not,
        registers the user.
        :param message: The incoming message object from a user.
        """
        telegram_id = message.from_user.id
        new_user = self.db.user_registered(telegram_id)
        if not new_user:
            self.db.register_user(telegram_id)

    def _handle_start(self, message) -> None:
        """A handler func for the '/start' command."""
        self._ensure_user_registration(message)
        self._get_registered_users()
        self.reply_to(message, 'You used /start command!')

    def _user_allowed(self, telegram_id: int) -> bool:
        """
        Determines if the user is allowed to participate in the competition.
        Checks if the user's telegram ID is stored in the db.
        :param telegram_id: User's telegram id.
        :return: True if the user is allowed, False otherwise.
        """
        return self.db.get_user(telegram_id) is not None

    def _check_bot_block(self, telegram_id: int) -> bool:
        """
        Ensures that the user is allowed to participate in the competition.
        Checks if a user is stored in the db.
        :param telegram_id: User's telegram id.
        """
        return self.db.check_bot_block(telegram_id)

    def _mark_bot_blocked(self, telegram_id: int) -> None:
        """Marks the user as having blocked the bot in the db.
        :param telegram_id: User's telegram id.
        """
        self.db.mark_bot_block(telegram_id)

    def _mark_bot_unblocked(self, telegram_id: int) -> None:
        """Marks the user as having unblocked the bot in the db.
        :param telegram_id: User's telegram id.
        """
        self.db.mark_bot_unblock(telegram_id)

    def _get_registered_users(self) -> None:
        """Fetches and updates the self.users field with a list of registered users from the database."""
        self.users = self.db.get_users()

    def _request_bets(self) -> None:
        """Sends a message to registered users with an inline button suggesting to input bets on upcoming round's
        matches."""
        text = '<b>Тур на подходе!</b>\nВремя делать ставки!'
        markup = telebot.types.InlineKeyboardMarkup(row_width=1)
        b = telebot.types.InlineKeyboardButton("Начать", callback_data="_start_bets_callback")
        markup.add(b)
        self.register_callback_query_handler(callback=self._start_bets_callback,
                                             func=lambda query: query.data == "_start_bets_callback")

        for u in self.users:
            self.send_message(chat_id=u.telegram_id, text=text, reply_markup=markup)

    def _start_bets_callback(self, query) -> None:
        """
        A callback func for the button to start bet input session.
        :param query: Callback query instance received after the user pressed the button to start inputting bets.
        :return:
        """
        # deleting inline button that caused this callback
        chat_id = query.json['message']['chat']['id']
        message_id = query.json['message']['message_id']
        self.edit_message_reply_markup(chat_id=chat_id, message_id=message_id)

        # this method must be called to end a query that caused this callback. Otherwise the inline button will be in
        # progress forever
        self.answer_callback_query(query.id)

        matches = ('Зенит - Спартак', 'Краснодар - Динамо', 'Локомотив - Крылья Советов')
        session = self._create_bet_input_session(chat_id, matches)

        self.send_message(chat_id=chat_id, text='Начинаем!')
        self._request_bet(session)

    def _create_bet_input_session(self, telegram_id: int, matches: tuple[str, ...]) -> BetInputSession:
        """
        Creates a bet input session for a user and adds it to bot's list of sessions.
        :param telegram_id: telegram_id of a user who started bet input session.
        :param matches: A list of this round's matches for user to place bets on.
        :return: Newly created BetInputSession instance.
        """
        session = BetInputSession(user_id=telegram_id, matches=matches)
        self._add_bet_input_session(telegram_id, session)
        return session

    def _request_bet(self, session: BetInputSession, repeated_bet: bool = False) -> None:
        """
        Sends a message to the user with match data and prompts them to input a bet.

        If this is the last match in the session, it will call self._finish_bet_session() to complete the session.
        The method can optionally resend the bet request if the previous bet was invalid (indicated by repeated_bet).

        :param session: A BetInputSession this match belongs to.
        :param repeated_bet: Set to True if the previous bet input was invalid, prompting the user to re-enter their
        bet for the current match.
        """
        user_id = session.user_id

        if not repeated_bet:
            match = session.next_match()
            if not match:
                self._finish_bet_session(user_id)
                return

        text = f"<b>{session.match}</b>\n\nВаша ставка?"
        self.send_message(user_id, text=text)

    def _finish_bet_session(self, telegram_id: int) -> None:
        """
        Finishes the bet input session for the user, deletes it from the bot's list of active sessions and sends a
        confirmation message to the user indicating that all bets have been placed.
        :param telegram_id: telegram_id the user whose session has been finished.
        """
        self._delete_bet_input_session(telegram_id)
        text = f'<b>Готово!</b>\n\nВы успешно поставили на все матчи тура!'
        self.send_message(telegram_id, text)

    def _handle_bet_input(self, message: telebot.types.Message) -> None:
        """
        A handler func for messages received by the user during a BetInputSession.

        Validates the message format according to the expected bet syntax.
        If the format is invalid, prompts the user to re-enter the bet. If valid, confirms the bet and requests the
        next bet for the following match.

        :param message: The incoming message object from a user.
        """
        user_id = message.from_user.id
        session = self._active_sessions[user_id]

        input_valid = BetBot._correct_bet(message.text)
        if not input_valid:
            text = f"<b>Ой!</b>\nНеправильный формат ставки\n\nСтавки необходимо присылать в формате 'число-число' " \
                   f"или 'число:число'. Например, 2-1 или 0:0. Попробуйте еще раз!"
            self.reply_to(message, text)
            self._request_bet(session=session, repeated_bet=True)
            return

        self.reply_to(message, f"Ставка принята!")
        session = self._active_sessions[message.from_user.id]
        self._request_bet(session)

    @staticmethod
    def _correct_bet(bet_text: str) -> bool:
        """
        Parses text that user sent as a bet and determines if it follows the right syntax:
        bet must be represented by two integers devided by a single allowed delimiter.
        Examples: 2-1, 0:0.
        :param bet_text: Text representing user's bet.
        :return: True if text is valid, False otherwise.
        """
        delimiters = ['-', ':']
        allowed = string.digits + ''.join(delimiters)
        bet_text = bet_text.strip()
        bet_text = bet_text.replace(' ', '')

        if len(bet_text) < 3:
            return False

        if any([char not in allowed for char in bet_text]):
            return False

        present_dels = [d for d in delimiters if d in bet_text]
        if len(present_dels) != 1:
            return False

        d = present_dels[0]
        if len(bet_text.split(d)) != 2:
            return False

        return True

    def _add_bet_input_session(self, telegram_id: int, session: BetInputSession) -> None:
        """
        Adds the new BetInputSession to the list of self._active_sessions.
        :param telegram_id: User's telegram id whose session is to be added.
        :param session: New BetInputSession instance.
        """
        if not self._active_sessions:
            self._active_sessions = {telegram_id: session}
        else:
            self._active_sessions.update({telegram_id: session})

    def _delete_bet_input_session(self, telegram_id: int) -> None:
        """
        Deletes BetInputSession from the list of self._active_sessions.
        :param telegram_id: User's telegram id whose session is to be deleted.
        """
        self._active_sessions.pop(telegram_id)

    def _bet_session_active(self, telegram_id: int) -> bool:
        """
        Determines if a user's bot is currently in a bet input session.
        :param telegram_id: User's telegram id whose session is to be checked.
        :return: True if bot session is on, False otherwise.
        """
        if not self._active_sessions:
            return False
        if not self._active_sessions.get(telegram_id, None):
            return False
        return True


if __name__ == "__main__":
    from db import Database

    db = Database()
    bot = BetBot(db)
