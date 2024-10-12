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
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self.name = DB_NAME
        self.conn = None
        self.cur = None
        # self._init_db()

    def _try_connect(self):
        try:
            self.conn = mysql.connector.connect(host=DB_HOST,
                                                user=DB_LOGIN,
                                                password=DB_PASSWORD,
                                                database='111',
                                                connect_timeout=10)
        except mysql.connector.errors.DatabaseError as e:
            return e
        return self.conn

    def __enter__(self):
        attempt = 0
        while attempt < Database.MAX_RETRIES:
            try:
                self.conn = mysql.connector.connect(host=DB_HOST,
                                                    user=DB_LOGIN,
                                                    password=DB_PASSWORD,
                                                    database=self.name,
                                                    connect_timeout=10)
                break

            except mysql.connector.errors.DatabaseError as e:
                print(f'Database error {e.errno}: {e.msg}')
                logging.exception(f'Database error {e.errno}: {e.msg}')
                if e.errno in (1045, 1049):
                    # 1045: Access denied for user 'user'@'host'
                    # 1049: Unknown database 'database'
                    return None
                if e.errno in (2005, 2003):
                    # 2005: Unknown MySQL server host 'hostname' (wrong host name)
                    # 2003: Can't connect to MySQL server on 'server' (MySQL server not responding e.g. not running)
                    attempt += 1
                    print(f"Retrying connection (attempt {attempt}/{Database.MAX_RETRIES})...")
                    logging.warning(f"Retrying connection (attempt {attempt}/{Database.MAX_RETRIES})...")
                    time.sleep(Database.RETRY_DELAY)
                else:
                    logging.error(f"An unexpected occurred while connecting to db: {e.msg}")
                    return None
            self.conn = None  # to avoid potential issues with partially initialized connection
        if not self.conn:
            print(f"Exceeded maximum connect retry attempts. Unable to connect to database.")
            logging.error(f"Exceeded maximum connect retry attempts. Unable to connect to database.")
            return
        else:
            print(f"Connection to db established!")
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
