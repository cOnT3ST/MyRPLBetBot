from datetime import datetime

from db import Database
from bot import BetBot
from scheduler import BotScheduler
from stats_api import StatsAPIHandler
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

        self.bot.set_command_handler(self)
        self.bot.register_callback_query_handler(func=lambda query: query.data == "bon_appetit",
                                                 callback=self.handle_bon_appetit)
        self.bot.register_callback_query_handler(func=lambda query: query.data == "work_over",
                                                 callback=self.handle_work_over)

    def handle_create_contest(self, message):
        self.bot.notify_admin(f"{message.text}\n"
                              f"CONTROLLER CREATING CONTEST...")

    def handle_command(self, message):
        # Map commands to methods
        command_map = {'/create_contest': self.handle_create_contest}

        command = message.text
        handler = command_map.get(command)

        if handler:
            handler(message)
        else:
            self.bot.send_message(
                message.chat.id, f"Unknown command: {command}. Type /help for a list of commands."
            )

    def handle_bon_appetit(self, callback_query):
        self.bot.send_message(callback_query.from_user.id, "Enjoy your meal!")
        self.bot.answer_callback_query(callback_query.id)

    def handle_work_over(self, callback_query):
        self.bot.send_message(callback_query.from_user.id, "Time to wrap up work!")
        self.bot.answer_callback_query(callback_query.id)

    def start(self):
        self.scheduler.start()
        self.bot.start()
