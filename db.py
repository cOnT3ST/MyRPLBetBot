import logging
import time
from os import path
from pprint import pprint

import mysql.connector
from utils import get_from_env, init_logging
from users import User
from leagues import League
from seasons import Season
from bet_contests import BetContest

DB_HOST = str(get_from_env("MYSQL_DB_HOST"))
DB_LOGIN = str(get_from_env("MYSQL_DB_USERNAME"))
DB_PASSWORD = str(get_from_env("MYSQL_DB_PASSWORD"))
ENV_TYPE = str(get_from_env("ENV_TYPE"))
DB_NAME = 'local_BetBotDB' if ENV_TYPE == 'development' else str(get_from_env("MYSQL_DB_NAME"))

init_logging()


class Database:
    MAX_RETRIES = 3
    RETRY_DELAY = 2

    def __init__(self):
        self._name = DB_NAME
        self._exists = False
        self._tables = {
            'api_requests': {'create': 'create_api_requests.sql', 'populate': self._populate_api_requests},
            'users': {'create': 'create_users.sql', 'populate': self._populate_users},
            'teams': {'create': 'create_teams.sql'},
            'leagues': {'create': 'create_leagues.sql'},
            'seasons': {'create': 'create_seasons.sql'},
            'bet_contests': {'create': 'create_bet_contests.sql'},
            'matches': {'create': 'create_matches.sql'},
            'bets': {'create': 'create_bets.sql'},
            'bet_contest_users': {'create': 'create_bet_contest_users.sql'}
        }
        self._creation_order = ('api_requests', 'users', 'teams', 'leagues', 'seasons', 'bet_contests', 'matches',
                                'bets')
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
        # TODO _mysql_connector.MySQLInterfaceError: Can't connect to MySQL server on 'localhost:3306' (10061)
        # TODO WHEN MYSQL80 isn't running

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
            fetched_data = self.cur.fetchall()  # returns a list of dicts

        stored_tables = [v for d in fetched_data for v in d.values()]
        missing_tables = tuple(set(self._tables) - set(stored_tables))
        return missing_tables

    def _create_tables(self):
        """Creates tables in the db using queries from MySQL scripts."""
        missing_tables = self._missing_tables()
        if not missing_tables:
            return

        logging.info("Creating tables...")

        ordered_tables = tuple(t for t in self._creation_order if t in missing_tables)
        for t in ordered_tables:
            self._create_table(t)

        logging.info("Tables creation finished.")

    def _create_table(self, table: str) -> None:
        """Creates a single table in the db using it's create query and populates it with initial data."""
        logging.info(f"Creating table '{table}'...")

        sql_script = self._tables[table]['create']
        sql_path = path.join('database', sql_script)
        pop_method = self._tables[table].get('populate', None)

        try:
            self._execute_mysql_script(sql_path)
            logging.info(f"Table '{table}' created.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while creating table: {repr(e)}")

        if not pop_method:
            return
        try:
            self._populate_table(table, pop_method)
        except Exception as e:
            logging.exception(f"An unexpected error occurred while populating table: {repr(e)}")

    def _populate_table(self, table: str, pop_method: callable) -> None:
        """Populates a table with data."""
        logging.info(f"Populating table '{table}'...")
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
    def _gen_insert_query(table: str, data: dict) -> str:
        cols = tuple(data.keys())
        cols_str = ', '.join(cols)
        pholders = ', '.join(["%s" for _ in cols])
        q = f"INSERT INTO {table} ({cols_str}) VALUES ({pholders});"
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

        admin_q = Database._gen_insert_query('users', admin_data)
        test_q = Database._gen_insert_query('users', test_user_data)

        with self:
            self.cur.execute(admin_q, tuple(admin_data.values()))
            #self.cur.execute(test_q, tuple(test_user_data.values()))

    def _populate_api_requests(self):
        """Populates 'api_requests' table with initial data."""
        data = {'requests_today': 0, 'daily_quota': 100}
        query = Database._gen_insert_query('api_requests', data)
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

    def get_admin(self) -> User | None:
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

    def insert_league(self, league_data: dict) -> None:
        query = Database._gen_insert_query('leagues', league_data)
        try:
            with self:
                self.cur.execute(query, tuple(league_data.values()))
            logging.info(f"New league inserted: {league_data}.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while inserting new league into table 'leagues':"
                              f" {repr(e)}")

    def get_league_by_api_id(self, api_id: int) -> League | None:
        q = f'SELECT * FROM leagues WHERE api_id = %s'
        with self:
            self.cur.execute(q, (api_id,))
            res = self.cur.fetchone()
        if res:
            res = League.from_db_dict(res)
        return res

    def get_league_by_country_and_name(self, country: str, name: str) -> League | None:
        q = f'SELECT * FROM leagues WHERE league_country = %s AND league_name = %s'
        with self:
            self.cur.execute(q, (country, name))
            res = self.cur.fetchone()
        if res:
            res = League.from_db_dict(res)
        return res

    def update_league(self, id: int, diff: dict) -> None:
        set_clause = ', '.join([f'{k} = %s' for k in diff.keys()])
        q = f"UPDATE leagues SET {set_clause} WHERE api_id = {id};"
        new_values = tuple(diff.values())

        try:
            with self:
                self.cur.execute(q, new_values)
            logging.info(f"Table 'leagues', id {id} updated: {diff}.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while updating table 'leagues': {repr(e)}")

    def insert_season(self, season_dict: dict) -> None:
        query = Database._gen_insert_query('seasons', season_dict)
        try:
            with self:
                self.cur.execute(query, tuple(season_dict.values()))
            logging.info(f"New season inserted: {season_dict}.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while inserting new season into table 'seasons':"
                              f" {repr(e)}")

    def get_season_by_id(self, id: int) -> Season | None:
        q = f'SELECT * FROM seasons WHERE id = %s'
        with self:
            self.cur.execute(q, (id,))
            res = self.cur.fetchone()
        if res:
            league = self.get_league_by_api_id(res['league_api_id'])
            res = Season.from_db_dict(league, res)
        return res

    def get_season_by_league_api_id_and_year(self, league_api_id: int, year: int) -> Season | None:
        q = f'SELECT * FROM seasons WHERE league_api_id = %s and year = %s'
        with self:
            self.cur.execute(q, (league_api_id, year))
            res = self.cur.fetchone()
        if res:
            league = self.get_league_by_api_id(league_api_id)
            res = Season.from_db_dict(league, res)
        return res

    def get_seasons_by_league_api_id(self, league_api_id: int) -> list[Season] | None:
        q = f'SELECT * FROM seasons WHERE league_api_id = %s'
        with self:
            self.cur.execute(q, (league_api_id,))
            res = self.cur.fetchall()
        if res:
            league = self.get_league_by_api_id(league_api_id)
            res = [Season.from_db_dict(league, s) for s in res]
        return res

    def get_last_stored_season(self, league_api_id: int) -> Season | None:
        q = f'SELECT * FROM seasons WHERE league_api_id = %s ORDER BY year DESC'
        with self:
            self.cur.execute(q, (league_api_id,))
            res = self.cur.fetchone()
        if res:
            league = self.get_league_by_api_id(league_api_id)
            res = Season.from_db_dict(league, res)
        return res

    def update_season(self, id: int, diff: dict) -> None:
        set_clause = ', '.join([f'{k} = %s' for k in diff.keys()])
        q = f"UPDATE seasons SET {set_clause} WHERE id = {id};"
        new_values = tuple(diff.values())
        try:
            with self:
                self.cur.execute(q, new_values)
            logging.info(f"Table 'seasons', id {id} updated: {diff}.")
        except Exception as e:
            logging.exception(f"An unexpected error occurred while updating table 'seasons': {repr(e)}")

    def insert_bet_contest(self, bet_contest_dict: dict) -> int | None:
        query = Database._gen_insert_query('bet_contests', bet_contest_dict)
        try:
            with self:
                self.cur.execute(query, tuple(bet_contest_dict.values()))
                bet_contest_id = self.cur.lastrowid
            logging.info(f"New bet contest inserted: {bet_contest_dict}.")
            return bet_contest_id
        except Exception as e:
            logging.exception(f"An unexpected error occurred while inserting new bet contest into table 'bet contests':"
                              f" {repr(e)}")

    def get_bet_contests(self, season_id: int) -> list[BetContest] | None:
        q = f'SELECT * FROM bet_contests WHERE season_id = %s'
        with self:
            self.cur.execute(q, (season_id,))
            res = self.cur.fetchall()
        if res:
            season = self.get_season_by_id(season_id)
            res = [BetContest.from_db_dict(season, s) for s in res]
        return res

    def get_bet_contest_by_id(self, id: int) -> BetContest | None:
        q = f'SELECT * FROM bet_contests WHERE id = %s'
        with self:
            self.cur.execute(q, (id,))
            res = self.cur.fetchone()
        if res:
            season = self.get_season_by_id(res['season_id'])
            res = BetContest.from_db_dict(season, res)
        return res


if __name__ == '__main__':
    db = Database()

