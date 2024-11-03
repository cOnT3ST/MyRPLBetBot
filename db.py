import logging
import time
from os import path

import mysql.connector
from utils import get_from_env, init_logging
from users import User

DB_HOST = str(get_from_env("MYSQL_DB_HOST"))
DB_LOGIN = str(get_from_env("MYSQL_DB_USERNAME"))
DB_PASSWORD = str(get_from_env("MYSQL_DB_PASSWORD"))
DB_NAME = 'local_BetBotDB'

init_logging()


class Database:
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self._name = DB_NAME
        self._exists = False
        self._tables = {
            'users': {'create': 'create_users.sql', 'populate': self._populate_users},
            'api_requests': {'create': 'create_api_requests.sql', 'populate': self._populate_api_requests}
        }
        self.conn = None
        self.cur = None
        self._conn_attempt = 0

        self._ensure_db_exists()
        logging.info(f"Database initialized.")

    def _try_connect(self) -> mysql.connector.connection.MySQLConnectionAbstract | None:

        conn_args = {'host': DB_HOST, 'user': DB_LOGIN, 'password': DB_PASSWORD}
        if self._exists:
            conn_args['database'] = self._name

        try:
            self.conn = mysql.connector.connect(**conn_args, connection_timeout=10)
            if self._conn_attempt != 0:
                logging.info(f"Connection retry successful.")
            self._conn_attempt = 0
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
        """Defines if a connection led to an error worth being retried."""
        # Considered err_codes:
        # 1045: Access denied for user 'user_name'@'host_name' (using password: YES) (wrong username or password)
        # 2003: Can't connect to MySQL server on 'localhost:port' (MySQL server not responding e.g., not running)
        # 2005: Unknown MySQL server host 'host-name' (wrong hostname)

        retriable_err_codes = (2003,)
        # I consider all other possible exceptions to be retriable by default.
        return e.errno in retriable_err_codes

    def _retry_connection(self) -> None:
        """Retries connection attempts to db"""
        if self._conn_attempt < Database.MAX_RETRIES:
            self._conn_attempt += 1
            logging.warning(f"Retrying connection (attempt {self._conn_attempt}/{Database.MAX_RETRIES})...")
            time.sleep(Database.RETRY_DELAY)
            self._try_connect()
        else:
            logging.error(f"Exceeded maximum connect retry attempts. Unable to connect to database.")

    def __enter__(self):
        self.conn = self._try_connect()
        if self.conn:
            self.cur = self.conn.cursor(buffered=True, dictionary=True)
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
        query = f"SHOW DATABASES LIKE '{self._name}'"
        with self:
            self.cur.execute(query)
            res = self.cur.fetchall()
        return res != []

    def _create_db(self) -> None:
        logging.info(f"Creating DB '{self._name}'...")
        try:
            with self:
                self.cur.execute(f"CREATE DATABASE {self._name}")
                self._exists = True
                logging.info(f"Database '{self._name}' created.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while creating db: {repr(e)}")

    def _missing_tables(self) -> tuple[str, ...]:
        with self:
            self.cur.execute('SHOW TABLES;')
            stored_tables = self.cur.fetchall()
        missing_tables = tuple(set(self._tables) - set(stored_tables))
        return missing_tables

    def _create_tables(self):
        """Creates tables in the db using queries from MySQL scripts."""
        tables = self._missing_tables()
        if not tables:
            return

        logging.info("Creating tables...")
        for t in tables:
            self._create_table(t)

        logging.info("Tables creation finished.")

    def _create_table(self, table: str) -> None:
        """Creates a single table in the db using it's create query and populates it with initial data."""
        logging.info(f"Creating table '{table}'...")

        sql_script = self._tables[table]['create']
        sql_path = path.join('database', sql_script)

        try:
            self._execute_mysql_script(sql_path)
            logging.info(f"Table '{table}' created.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while creating table: {repr(e)}")

        try:
            self._populate_table(table)
        except Exception as e:
            logging.exception(f"An unexpected error occurred while populating table: {repr(e)}")

    def _populate_table(self, table: str) -> None:
        """Populates a table with data."""
        logging.info(f"Populating table '{table}'...")
        pop_method = self._tables[table]['populate']
        pop_method()
        logging.info(f"Table populated.")

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

    def _ensure_db_exists(self) -> None:
        """
        Checks if the DB already exists on MySQL server and creates it if not.
        This only concerns local DB because you have to create remote DB manually. In that case
        this script will find DB and only create tables.
        """
        if not self._db_exists():
            logging.info(f"Database '{self._name}' not found.")
            self._create_db()
            self._create_tables()
        else:
            logging.info(f"Database '{self._name}' found.")
            self._exists = True
            self._create_tables()

    def _table_exists(self, table: str) -> bool:
        """Shows if a table is already stored in the DB"""
        query = f"SHOW TABLES LIKE '{table}'"

        with self:
            self.cur.execute(query)
            res = self.cur.fetchall()
        return res != []

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

    @staticmethod
    def _write_insert_query(table: str, data: dict) -> str:
        cols = tuple(data.keys())
        pholders = ', '.join(["%s" for _ in cols])
        q = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({pholders});"
        return q

    def _populate_users(self):
        """Populates 'users' table with initial data."""
        admin_data = {
            'telegram_id': int(get_from_env('ADMIN_ID')),
            'is_admin': True
        }
        test_user_data = {
            'telegram_id': int(get_from_env('TEST_ACCOUNT_ID')),
            'first_name': 'test',
            'last_name': 'account'
        }

        admin_q = Database._write_insert_query('users', admin_data)
        test_q = Database._write_insert_query('users', test_user_data)

        with self:
            self.cur.execute(admin_q, tuple(admin_data.values()))
            self.cur.execute(test_q, tuple(test_user_data.values()))

    def _populate_api_requests(self):
        """Populates 'api_requests' table with initial data."""
        data = {'requests_today': 0, 'daily_quota': 100}
        query = Database._write_insert_query('api_requests', data)
        with self:
            self.cur.execute(query, tuple(data.values()))

    def get_users(self) -> list[User] | None:
        query = 'SELECT * FROM users WHERE used_bot = 1'
        with self:
            self.cur.execute(query)
            res = self.cur.fetchall()
        if res:
            res = [User.from_dict(d) for d in res]
        return res

    def get_user(self, telegram_id: int) -> User | None:
        query = f'SELECT * FROM users WHERE telegram_id = {telegram_id}'
        with self:
            self.cur.execute(query)
            res = self.cur.fetchone()
        if res:
            res = User.from_dict(res)
        return res

    def _get_admin(self) -> User | None:
        query = 'SELECT * FROM users WHERE is_admin = True'
        with self:
            self.cur.execute(query)
            res = self.cur.fetchone()
        if res:
            res = User.from_dict(res)
        return res

    def user_registered(self, telegram_id: int) -> bool:
        user = self.get_user(telegram_id)
        return bool(user.used_bot)

    def register_user(self, telegram_id: int) -> None:
        query = f"UPDATE users SET used_bot = 1 WHERE telegram_id = {telegram_id}"
        with self:
            self.cur.execute(query)

    def mark_bot_block(self, telegram_id: int) -> None:
        query = f"UPDATE users SET blocked_bot = 1 WHERE telegram_id = {telegram_id}"
        with self:
            self.cur.execute(query)

    def mark_bot_unblock(self, telegram_id: int) -> None:
        query = f"UPDATE users SET blocked_bot = 0 WHERE telegram_id = {telegram_id}"
        with self:
            self.cur.execute(query)

    def check_bot_block(self, telegram_id: int) -> bool:
        user = self.get_user(telegram_id)
        return bool(user.blocked_bot)


if __name__ == '__main__':
    db = Database()
