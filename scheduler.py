from datetime import datetime
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
import config
from utils import init_logging

init_logging()


class BotScheduler(BackgroundScheduler):
    def __init__(self):
        super().__init__(
            jobstores={'default': MemoryJobStore()},
            executors={'default': ThreadPoolExecutor()},
            timezone=config.PREFERRED_TIMEZONE
        )

    def schedule(self, job: callable, job_dt: datetime) -> None:
        self.add_job(func=job, trigger=DateTrigger(job_dt))

    def schedule_bon_appetit(self, job: callable) -> None:
        self.add_job(func=job, trigger=CronTrigger(day_of_week='1-5', hour=12))

    def schedule_work_over(self, job: callable) -> None:
        self.add_job(func=job, trigger=CronTrigger(day_of_week='1-5', hour=16, minute=30))


if __name__ == '__main__':
    s = BotScheduler()
