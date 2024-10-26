import os
from dotenv import load_dotenv
import logging


def get_from_env(var_to_load: str) -> str:
    load_dotenv()
    return os.getenv(var_to_load)


def init_logging():
    logging.basicConfig(level=logging.INFO,
                        filename="MyRPLBetBot.log",
                        format="%(asctime)s [%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
                        datefmt="%d.%m.%Y %H:%M:%S",
                        encoding='UTF-8'
                        )
