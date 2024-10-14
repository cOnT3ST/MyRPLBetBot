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
        self.exists = False
        self.conn = None
        self.cur = None
        self.conn_attempt = 0

        if not self._db_exists():
            logging.info(f"Database '{self.name}' not found.")
            self._create_db()
            self._create_tables()
        else:
            self.exists = True

    def _try_connect(self) -> mysql.connector.connection.MySQLConnectionAbstract | None:

        conn_args = {'host': DB_HOST, 'user': DB_LOGIN, 'password': DB_PASSWORD}
        if self.exists:
            conn_args['database'] = self.name

        try:
            self.conn = mysql.connector.connect(**conn_args, connection_timeout=10)
            if self.conn_attempt != 0:
                logging.info(f"Connection retry successful.")
            self.conn_attempt = 0
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
        # 2003: Can't connect to MySQL server on 'localhost:port' (MySQL server not responding e.g. not running)
        # 2005: Unknown MySQL server host 'host-name' (wrong hostname)

        non_retriable_err_codes = (2005, 1045)
        # I consider all other possible exceptions to be retriable by default
        return e.errno not in non_retriable_err_codes

    def _retry_connection(self):
        """Retries connection attempts to db"""
        if self.conn_attempt < Database.MAX_RETRIES:
            self.conn_attempt += 1
            logging.warning(f"Retrying connection (attempt {self.conn_attempt}/{Database.MAX_RETRIES})...")
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
        logging.info(f"Attempt to create db...")
        try:
            with self:
                self.cur.execute(f"CREATE DATABASE {self.name}")
                self.exists = True
                logging.info(f"Database '{self.name}' created.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while creating db: {repr(e)}")

    def _create_tables(self):
        """Creates tables in the db using queries from a MySQL script."""
        logging.info("Attempt to create tables...")
        try:
            self._execute_mysql_script('database/create_tables.sql')
            logging.info(f"Tables created.")
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


if __name__ == '__main__':
    db = Database()
