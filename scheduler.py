from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.jobstores.memory import MemoryJobStore
import config


def job_test_print():
    print(f"{datetime.now().strftime(config.PREFERRED_TIME_FORMAT)}: Test print job running...")


def job_bon_appetit():
    print(f"Breakfast time! Bon appetit!")


def job_cron_job():
    print(f"{datetime.now().strftime(config.PREFERRED_TIME_FORMAT)}: cron job in action!")


class BotScheduler(BackgroundScheduler):
    def __init__(self):
        super().__init__(
            jobstores={'default': MemoryJobStore()},
            executors={'default': ThreadPoolExecutor()},
            timezone=config.PREFERRED_TIMEZONE
        )
        self.jobs = {job_test_print: IntervalTrigger(seconds=3),
                     job_bon_appetit: IntervalTrigger(seconds=6),
                     job_cron_job: CronTrigger(hour=13, minute=49)}
        for j, t in self.jobs.items():
            self.add_job(func=j, trigger=t)

    def schedule_job(self, job: callable, job_dt: datetime) -> None:
        cron_args = BotScheduler._datetime_to_cron_args(job_dt)
        self.add_job(func=job, trigger=CronTrigger(**cron_args))

    @staticmethod
    def _datetime_to_cron_args(dt: datetime) -> dict:
        return {
            'year': dt.year,
            'month': dt.month,
            'day': dt.day,
            'hour': dt.hour,
            'minute': dt.minute,
            'second': dt.second
        }

import time

if __name__ == '__main__':
    s = BotScheduler()
    try:
        print(f"{datetime.now().strftime(config.PREFERRED_TIME_FORMAT)}: SCHEDULER ONLINE")
        s.start()
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        s.shutdown()
        print(f"{datetime.now().strftime(config.PREFERRED_TIME_FORMAT)}: SCHEDULER SHUT DOWN")
