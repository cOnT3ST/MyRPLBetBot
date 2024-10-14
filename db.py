import logging
import time
from os import path

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
        self.attempt = 0  # to connect to db


        #self._create_db()
        if not self._db_exists():
            self._create_db()

    def _try_connect(self) -> mysql.connector.connection.MySQLConnectionAbstract | None:

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
            if Database._error_retriable(e):
                self._retry_connection()
            else:
                logging.error(f"Failed to connect to db. {e.errno}: {e.msg}")

        except Exception as e:
            logging.exception(f"An unexpected error occurred while connecting to db: {repr(e)}")

        self.conn = None
        return

    @staticmethod
    def _error_retriable(e: mysql.connector.errors.Error) -> bool:
        """Defines if a connection led to a error worth being retried"""
        # Considered err_codes:
        # 1045: Access denied for user 'user_name'@'host_name' (using password: YES) (wrong username or password)
        # 1049: Unknown database 'db_name' (wrong db name)
        # 2003: Can't connect to MySQL server on 'localhost:port' (MySQL server not responding e.g. not running)
        # 2005: Unknown MySQL server host 'host-name' (wrong hostname)

        non_retriable_err_codes = (2005, 1045, 1049)
        # I consider all other possible exceptions to be retriable by default
        return e.errno not in non_retriable_err_codes

    def _retry_connection(self):
        """Retries connection attempts to db"""
        if self.attempt < Database.MAX_RETRIES:
            self.attempt += 1
            logging.warning(f"Retrying connection (attempt {self.attempt}/{Database.MAX_RETRIES})...")
            time.sleep(Database.RETRY_DELAY)
            self._try_connect()
        else:
            logging.error(f"Exceeded maximum connect retry attempts. Unable to connect to database.")

    def __enter__(self):
        self.conn = self._try_connect()
        if self.conn:
            self.cur = self.conn.cursor(buffered=True)
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

    def _db_exists(self) -> bool:
        """Shows if a db is already stored on server"""
        query = f"SHOW DATABASES LIKE '{self.name}'"
        with self:
            self.cur.execute(query)
            res = self.cur.fetchall()
        return res != []

    def _create_db(self):
        """Creates a db on MySQL server using queries from a MySQL script"""
        try:
            self._execute_mysql_script('database/create_db.sql')
        except FileNotFoundError as e:
            logging.exception(f"Database error: {repr(e)}")

    def _execute_mysql_script(self, filepath: str) -> None:
        """
        Executes queries from a MySQL .sql file.
        :param filepath: A path to the .sql file with MySQL queries.
        """
        if not path.exists(filepath):
            raise FileNotFoundError('Failed to find MySQL script file')

        queries = Database._extract_mysql_queries(filepath)

        with self:
            for q in queries:
                self.cur.execute(q)

    @staticmethod
    def _extract_mysql_queries(filepath: str) -> list[str]:
        """
        Extracts MySQL queries from a .sql file.
        :param filepath: A path to the .sql file.
        :return: A list of strings representing MySQL queries.
        """
        with open(filepath) as f:
            raw_text = f.read().strip()
        queries = [_ for _ in raw_text.split(';') if _]  # if _ deletes '' lines
        queries = [q.replace('\n', '') for q in queries]
        return queries

    def start(self):
        pass


if __name__ == '__main__':
    db = Database()
