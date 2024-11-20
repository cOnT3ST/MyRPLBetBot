from db import Database
from bot import BetBot
from scheduler import BotScheduler
from stats_api import StatsAPIHandler
from controller import Controller


class App:
    def __init__(
            self,
            telegram_bot: BetBot,
            database: Database,
            scheduler: BotScheduler,
            stats_api_handler: StatsAPIHandler
    ):
        self.bot = telegram_bot
        self.db = database
        self.stats = stats_api_handler
        self.scheduler = scheduler

        self.start()

    def start(self):
        self.scheduler.start()
        self.bot.start()


if __name__ == '__main__':
    db = Database()
    bot = BetBot(db)
    stats = StatsAPIHandler(db)
    bs = BotScheduler()
    bs.schedule_bon_appetit(job=bot.send_bon_appetit)
    bs.schedule_work_over(job=bot.send_work_over)
    c = Controller(telegram_bot=bot, database=db, scheduler=bs, stats_api_handler=stats)

    app = App(telegram_bot=bot, database=db, stats_api_handler=stats, scheduler=bs)
