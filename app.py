from db import Database
from bot import BetBot


class App:
    def __init__(self, telegram_bot, database):
        self.bot = telegram_bot
        self.db = database


if __name__ == '__main__':
    db = Database()
    bot = BetBot(db)
    app = App(bot, db)
