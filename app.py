import logging
from datetime import datetime
from threading import Thread

from db import Database
from bot import BetBot
from scheduler import BotScheduler
import config


class App:
    def __init__(self, telegram_bot, database, scheduler):
        self.bot = telegram_bot
        self.db = database
        self.scheduler = scheduler
        self.start()

    def start(self):
        self.scheduler.start()
        self.bot.start()


if __name__ == '__main__':
    db = Database()
    bot = BetBot(db)
    bs = BotScheduler()
    bs.schedule_bon_appetit(job=bot.send_bon_appetit)
    bs.schedule_work_over(job=bot.send_work_over)

    app = App(bot, db, bs)
