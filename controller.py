from pprint import pprint
import logging
from datetime import datetime

from telebot.types import Message

from db import Database
from bot import BetBot
from scheduler import BotScheduler
from stats_api import StatsAPIHandler
from users import User
from leagues import League
from seasons import Season
from bet_contests import BetContest
from utils import init_logging

init_logging()


class Controller:
    def __init__(
            self,
            telegram_bot: BetBot,
            database: Database,
            scheduler: BotScheduler,
            stats_api_handler: StatsAPIHandler
    ):
        self.bot = telegram_bot
        self.db = database
        self.sah = stats_api_handler
        self.scheduler = scheduler

        self.users: list[User] | None = None
        self.bot.set_command_handler(self)
        self.bot.register_callback_query_handler(func=lambda query: query.data == "bon_appetit",
                                                 callback=self.handle_bon_appetit)
        self.bot.register_callback_query_handler(func=lambda query: query.data == "work_over",
                                                 callback=self.handle_work_over)

        self._get_registered_users()

    def handle_command(self, message: Message):
        command_map = {
            '/start': self._handle_start,
            '/help': self._handle_help,
            '/create_contest': self._handle_create_contest
        }

        command = message.text
        handler = command_map.get(command)

        if handler:
            handler(message)
        else:
            self.bot.reply_to(message=message, text="<b>Ой!</b>\n\n"
                                                    "Вы ввели неподдерживаемую команду.\n"
                                                    "Для вывода доступных команд введите /help.")

    def _handle_create_contest(self, message):
        """A handler func for the '/create_contest' telegram bot command."""
        logging.info(f"Handling '/create_contest' command...")
        country, league_name = 'Russia', 'Premier League'
        admin = self.db.get_user(message.from_user.id)

        stored_league = self._get_league(country, league_name)
        if not stored_league:
            new_season = self._create_season(country, league_name)
            self._create_bet_contest(new_season, admin)
            return

        stored_season = self._get_season(stored_league.api_id)
        if not stored_season:
            new_season = self._create_season(country, league_name)
            self._create_bet_contest(new_season, admin)
            return

        stored_bet_contests = self._get_bet_contests(stored_season.id)
        if not stored_bet_contests:
            self._create_bet_contest(stored_season, admin)
            return
        else:
            # self._suggest_bet_contest()
            self.bot.reply_to(
                message,
                '<b>Ой!</b>\n\n'
                f'В базе данных уже хранится соревнование\n'
                f'<b>{stored_season.league.league_country_ru}, {stored_season.league.league_name_ru}, '
                f'сезон {stored_season.year}-{stored_season.end_year}</b>!\n\n'
                'Создание нового соревнования в таком случае еще <b>не реализовано</b>.'
            )
            logging.info(f"Bet contest creation aborted: '{stored_season.league.league_country}, "
                         f"{stored_season.league.league_name}, season {stored_season.year}-{stored_season.end_year}' "
                         f"already stored.")


    def _get_season(self, league_api_id: int) -> Season | None:
        stored_season = self.db.get_last_stored_season(league_api_id)
        if not stored_season.finished:
            return stored_season
        return

    def _get_bet_contests(self, season_id: int) -> list[BetContest] | None:
        stored_bet_contests = self.db.get_bet_contests(season_id)
        if stored_bet_contests:
            return stored_bet_contests
        return

    def _get_bet_contest(self, id: int) -> BetContest | None:
        stored_bet_contest = self.db.get_bet_contest_by_id(id)
        return stored_bet_contest

    def _insert_bet_contest(self, bc: BetContest) -> int:
        return self.db.insert_bet_contest(bc.to_db_dict())

    def _create_bet_contest(self, season: Season | None, admin: User) -> BetContest | None:
        self.bot.notify_admin("Создание соревнования по ставкам...")
        bc = BetContest(season, [admin])
        bc_id = self._insert_bet_contest(bc)
        bc = self._get_bet_contest(bc_id)
        logging.info(f'New contest created: '
                     f'{bc.season.league.league_country}, {bc.season.league.league_name}, '
                     f'season {bc.season.year}-{bc.season.end_year}.')
        self.bot.notify_admin(f"Соревнование создано!")
        return bc

    def _get_league(self, country: str, league: str) -> League | None:
        return self.db.get_league_by_country_and_name(country, league)

    def _fetch_season(self, country: str, league: str) -> Season | None:
        """
        Extracts data from the statistics service for the desired country and league.
        :param country: Country of desired league.
        :param league: Name of the league in desired country, e.g. 'Premier League'.
        :return: Season obj representing desired country's football league's season.
        """
        fetched_data = self.sah.get_this_season_data(country, league)
        if not fetched_data:
            return

        country_data = fetched_data['country']
        league_country = country_data['name']

        season_data = fetched_data['seasons'][0]
        season_start = season_data['start']
        season_end = season_data['end']
        season_is_active = {'true': True, 'false': False}.get(season_data['current'])

        league_data = fetched_data['league']
        league_api_id = league_data['id']
        league_name = league_data['name']
        league_logo_url = league_data['logo']

        league = League(
            api_id=league_api_id,
            league_country=league_country,
            league_name=league_name,
            logo_url=league_logo_url,
            league_country_ru='Россия' if league_country == 'Russia' else None,
            league_name_ru='Премьер-Лига' if league_name == 'Premier League' else None
        )

        season = Season(
            league=league,
            start_date=datetime.strptime(season_start, '%Y-%m-%d').date(),
            end_date=datetime.strptime(season_end, '%Y-%m-%d').date(),
            active=season_is_active

        )
        return season

    def _insert_league(self, league: League) -> None:
        stored_league = self.db.get_league_by_api_id(league.api_id)
        if stored_league:
            diff = stored_league.compare(league)
            if diff:
                self.db.update_league(id=league.api_id, diff=diff)
        else:
            self.db.insert_league(league.to_db_dict())

    def _insert_season(self, season: Season) -> None:
        stored_season = self.db.get_season_by_league_api_id_and_year(season.league.api_id, season.year)
        if stored_season:
            diff = season.compare(stored_season)
            if diff:
                self.db.update_season(id=season.id, diff=diff)
        else:
            self.db.insert_season(season.to_db_dict())

    def _create_season(self, country: str, league: str) -> Season | None:
        season = self._fetch_season(country, league)
        if not season:
            return
        self._insert_league(season.league)
        self._insert_season(season)
        season = self._get_season(season.league.api_id)
        return season

    def _league_stored(self, league_api_id: int) -> bool:
        stored_league = self.db.get_league_by_api_id(league_api_id)
        return stored_league is not None

    def _bet_contest_exists(self, season_id: int) -> bool:
        stored_bc = self.db.get_bet_contests(season_id)
        return stored_bc is not None

    def _handle_start(self, message: Message) -> None:
        """A handler func for the '/start' telegram bot command."""
        self._ensure_user_registration(message)
        self._get_registered_users()
        self.bot.reply_to(message, 'К сожалению, команда /start пока не поддерживается 😪')

    def _handle_help(self, message: Message) -> None:
        """A handler func for the '/help' telegram bot command."""
        comms_n_descs = [f"{c} - {d['desc']}" for c, d in self.bot.commands.items()]
        comms_n_descs = f'\n\n'.join(comms_n_descs)
        self.bot.reply_to(message, f"Список поддерживаемых ботом команд:\n\n"
                                   f"{comms_n_descs}")

    def handle_bon_appetit(self, callback_query):
        self.bot.send_message(callback_query.from_user.id, "Enjoy your meal!")
        self.bot.answer_callback_query(callback_query.id)

    def handle_work_over(self, callback_query):
        self.bot.send_message(callback_query.from_user.id, "Time to wrap up work!")
        self.bot.answer_callback_query(callback_query.id)

    def start(self):
        self.scheduler.start()
        self.bot.start()

    def _ensure_user_registration(self, message: Message) -> None:
        """
        Ensures that the user is registered in the database.
        Checks if a user is registered i.e., has already interacted with the bot at least once. If not,
        registers the user.
        :param message: The incoming message object from a user via telegram bot.
        """
        telegram_id = message.from_user.id
        new_user = self.db.user_registered(telegram_id)
        if not new_user:
            self.db.register_user(telegram_id)

    def _get_registered_users(self) -> None:
        """Fetches and updates the self.users field with a list of registered users from the database."""
        self.users = self.db.get_users()

    def _suggest_bet_contest(self):
        self.bot.notify_admin('Соревнование для текущего сезона уже есть в базе данных!')
        print("_suggest_bet_contest run. Method hasn't been implemented yet")
        pass