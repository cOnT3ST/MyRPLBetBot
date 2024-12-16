import datetime
import logging
import requests
from pytz import timezone
from urllib.parse import urljoin

from utils import get_from_env, init_logging
from config import PREFERRED_TIMEZONE
from db import Database
from leagues import League

STATS_API_BASE_URL = 'https://api-football-beta.p.rapidapi.com'
STATS_API_HOST = 'api-football-beta.p.rapidapi.com'
HEADERS = {"X-RapidAPI-Host": STATS_API_HOST, "X-RapidAPI-Key": get_from_env("STATS_API_KEY")}

init_logging()


class StatsAPIHandler:
    def __init__(self, db):
        self.db = db
        self.timezone = timezone(PREFERRED_TIMEZONE)

    def _make_request(self, endpoint: str, params: dict[str, str | int] = None) -> dict | None:
        """
        Makes request to a certain endpoint of the API stats server.

        :param endpoint: API endpoint as per STATS_API_BASE_URL docs.
        :param params: A set of parameters required for this particular request as per STATS_API_BASE_URL docs.
        :return:
        """

        request_url = urljoin(base=STATS_API_BASE_URL, url=endpoint)
        # request_url = "https://www.amazon.com/nothing_here"
        # request_url = 'https://dadsasdasdsd.com/'
        # request_url = 'https://api.github.com/'
        # try:
        # response = requests.get(request_url, headers=HEADERS, params=params)
        # try:
        #     response = requests.get('https://geeksforgeeks.org/naveen/')
        #     response.raise_for_status()
        # except requests.ConnectionError as e:
        #     print(e.args[0])
        # except requests.HTTPError as e:
        #     print(e.args[0])
        # except requests.TooManyRedirects as e:
        #     print(e.args[0])
        # except requests.ReadTimeout as e:
        #     print(e.args[0])
        # except requests.Timeout as e:
        #     print(e.args[0])
        # except requests.JSONDecodeError as e:
        #     print(e.args[0])

        # logging.info(f"Requesting {request_url} with params: {params}...")
        response = requests.get(request_url, headers=HEADERS, params=params)

        if not response.ok:
            logging.error('BAD RESPONSE.')
            return

        # logging.info(f"Request successful.")
        response_json = response.json()
        return response_json

    def _country_supported(self, country: str) -> bool:
        """Checks if country us supported by Stats API service."""
        logging.info(f'Checking if {country} supported by STATS API ...')
        response = self._make_request(endpoint='countries', params={'name': country})
        result = response['results'] != 0
        logging.info(f'{country} supported.' if result else f'{country} NOT SUPPORTED!')
        return result

    def get_this_season_data(self, country: str, league: str) -> dict | None:
        """Returns data for this year season in the given championship of the given country fetched from Stats API."""

        response = self._make_request(
            endpoint='leagues',
            params={
                'name': league,
                'country': country,
                'current': 'true'
            }
        )

        if response['results'] == 0:  # League hasn't started yet
            return None

        valuable_data = response['response'][0]
        return valuable_data

    def _get_league_teams(self, league_api_id: int, year: int) -> list:
        response = self._make_request(
            endpoint='teams',
            params={"league": league_api_id, "season": year}
        )
        print(f"{response=}")
        teams_list = response['response']
        result = []
        for t in teams_list:
            team_id = t['team']['id']
            name_eng = t['team']['name']
            city_eng = t['venue']['city']
            logo_url = t['team']['logo']
            result.append({'team_api_id': team_id, 'name_eng': name_eng, 'city_eng': city_eng, 'logo_url': logo_url})
        return result


if __name__ == '__main__':
    db = Database()
    s = StatsAPIHandler(db)
    season_data = s.get_this_season_data('Russia', 'Premier League')

    print(season_data)
