from datetime import datetime

from telebot.types import Message

from db import Database
from bot import BetBot
from scheduler import BotScheduler
from stats_api import StatsAPIHandler
from users import User
from leagues import League
from seasons import Season


class Controller:
    def __init__(
            self,
            telegram_bot: BetBot,
            database: Database,
            scheduler: BotScheduler,
            stats_api_handler: StatsAPIHandler
    ):
        self.bot = telegram_bot
        self.db = database
        self.sah = stats_api_handler
        self.scheduler = scheduler

        self.users: list[User] | None = None
        self.bot.set_command_handler(self)
        self.bot.register_callback_query_handler(func=lambda query: query.data == "bon_appetit",
                                                 callback=self.handle_bon_appetit)
        self.bot.register_callback_query_handler(func=lambda query: query.data == "work_over",
                                                 callback=self.handle_work_over)

        self._get_registered_users()

    def handle_command(self, message: Message):
        command_map = {
            '/start': self._handle_start,
            '/help': self._handle_help,
            '/create_contest': self._handle_create_contest
        }

        command = message.text
        handler = command_map.get(command)

        if handler:
            handler(message)
        else:
            self.bot.reply_to(message=message, text="<b>Ой!</b>\n\n"
                                                    "Вы ввели неподдерживаемую команду.\n"
                                                    "Для вывода доступных команд введите /help.")

    def _handle_create_contest(self, message):
        """A handler func for the '/create_contest' telegram bot command."""
        self.bot.notify_admin(f"{message.text}\n"
                              f"CONTROLLER CREATING CONTEST...")

    def _handle_start(self, message: Message) -> None:
        """A handler func for the '/start' telegram bot command."""
        self._ensure_user_registration(message)
        self._get_registered_users()
        self.bot.reply_to(message, 'К сожалению, команда /start пока не поддерживается 😪')

    def _handle_help(self, message: Message) -> None:
        """A handler func for the '/help' telegram bot command."""
        comms_n_descs = [f"{c} - {d['desc']}" for c, d in self.bot.commands.items()]
        comms_n_descs = f'\n\n'.join(comms_n_descs)
        self.bot.reply_to(message, f"Список поддерживаемых ботом команд:\n\n"
                                   f"{comms_n_descs}")

    def handle_bon_appetit(self, callback_query):
        self.bot.send_message(callback_query.from_user.id, "Enjoy your meal!")
        self.bot.answer_callback_query(callback_query.id)

    def handle_work_over(self, callback_query):
        self.bot.send_message(callback_query.from_user.id, "Time to wrap up work!")
        self.bot.answer_callback_query(callback_query.id)

    def start(self):
        self.scheduler.start()
        self.bot.start()

    def _ensure_user_registration(self, message: Message) -> None:
        """
        Ensures that the user is registered in the database.
        Checks if a user is registered i.e., has already interacted with the bot at least once. If not,
        registers the user.
        :param message: The incoming message object from a user via telegram bot.
        """
        telegram_id = message.from_user.id
        new_user = self.db.user_registered(telegram_id)
        if not new_user:
            self.db.register_user(telegram_id)

    def _get_registered_users(self) -> None:
        """Fetches and updates the self.users field with a list of registered users from the database."""
        self.users = self.db.get_users()
