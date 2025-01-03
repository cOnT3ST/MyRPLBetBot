from db import Database
from bot import BetBot
from scheduler import BotScheduler
from stats_api import StatsAPIHandler
from controller import Controller


class App:
    def __init__(self, controller: Controller):
        self.controller = controller
        self.controller.start()


if __name__ == '__main__':
    db = Database()
    bot = BetBot(db)
    stats_api_handler = StatsAPIHandler(db)
    scheduler = BotScheduler()
    scheduler.schedule_bon_appetit(job=bot.send_bon_appetit)
    scheduler.schedule_work_over(job=bot.send_work_over)
    controller = Controller(telegram_bot=bot, database=db, scheduler=scheduler, stats_api_handler=stats_api_handler)
    app = App(controller)
