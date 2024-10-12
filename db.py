import logging
import time

import mysql.connector
from utils import load_confidentials_from_env, initialize_logging

DB_HOST = str(load_confidentials_from_env("MYSQL_DB_HOST"))
DB_LOGIN = str(load_confidentials_from_env("MYSQL_DB_USERNAME"))
DB_PASSWORD = str(load_confidentials_from_env("MYSQL_DB_PASSWORD"))
DB_NAME = 'myrplbetbot_db'

initialize_logging()


class Database:

    def __init__(self):
        self.name = DB_NAME
        self.conn = None
        self.cur = None
        self.attempt = 0  # to connect to db
        # self._init_db()

    def _try_connect(self) -> mysql.connector.connection.MySQLConnectionAbstract | None:
        max_retries = 3
        retry_delay = 2

        try:
            self.conn = mysql.connector.connect(host=DB_HOST,
                                                user=DB_LOGIN,
                                                password=DB_PASSWORD,
                                                database=self.name,
                                                connect_timeout=10)
            if self.attempt != 0:
                logging.info(f"Connection retry successful.")
            self.attempt = 0
            return self.conn
        except mysql.connector.errors.Error as e:
            logging.exception(f"Database error: {e.msg}")
            if self._error_retriable(e):
                if self.attempt < max_retries:
                    self.attempt += 1
                    logging.warning(f"Retrying connection (attempt {self.attempt}/{max_retries})...")
                    time.sleep(retry_delay)
                    self._try_connect()
                else:
                    logging.error(f"Exceeded maximum connect retry attempts. Unable to connect to database.")
            else:
                logging.error(f"Failed to connect to db. {e.errno}: {e.msg}")

        except Exception as e:
            logging.exception(f"An unexpected error occurred while connecting to db: {repr(e)}")

        self.conn = None
        return

    def _error_retriable(self, e: mysql.connector.errors.Error) -> bool:
        """Defines if a connection led to a error worth being retried"""
        # Considered err_codes:
        # 1045: Access denied for user 'user_name'@'host_name' (using password: YES) (wrong username or password)
        # 1049: Unknown database 'db_name' (wrong db name)
        # 2003: Can't connect to MySQL server on 'localhost:port' (MySQL server not responding e.g. not running)
        # 2005: Unknown MySQL server host 'host-name' (wrong hostname)

        non_retriable_err_codes = (2005, 1045, 1049)
        # I consider all other possible exceptions to be retriable by default
        return e.errno not in non_retriable_err_codes

    def __enter__(self):
        self.conn = self._try_connect()
        if self.conn:
            self.cur = self.conn.cursor()
        return self

    def __exit__(self, ext_type, exc_value, traceback):
        if not self.conn:
            return
        self.cur.close()
        if isinstance(exc_value, Exception):
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()

    def start(self):
        with self:
            pass
    # def _init_db(self):
    #     try:
    #         if not self._db_exists():
    #             logging.info(f"Database '{self.name}' not found.")
    #             self._create_db()
    #             self._create_tables()
    #             # self._populate_db()
    #     except mysql.connector.Error as e:
    #         logging.exception(f"Error during database initialization: {e}")
    #         raise


if __name__ == '__main__':
    db = Database()
    db.start()
