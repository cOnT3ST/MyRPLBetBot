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
        print('REQUEST SUCCESSFULL')
        response_json = response.json()
        return response_json

    def _country_supported(self) -> bool:
        """Checks if Russia us supported by Stats API service."""
        logging.info(f'Checking if Russia supported by STATS API ...')
        response = self._make_request(endpoint='countries', params={'name': 'Russia'})
        result = response['results'] != 0
        logging.info('Russia supported.' if result else 'Russia NOT SUPPORTED!')
        return result

    def _get_season_data(self):
        """
        Returns Stats API considering current Russian Premier League season information.

        :return:
        """
        country = 'Russia'
        league = 'Premier League'
        response = self._make_request(endpoint='leagues',
                                      params={'name': league, 'current': 'true', 'country': country}
                                      )

        if response['results'] == 0:  # League hasn't started yet
            return None

        valuable_data = response['response'][0]
        league_dict = valuable_data['league']
        season_dict = valuable_data['seasons'][0]

        season_data = {'league': {'id': league_dict['id'],
                                  'logo_url': league_dict['logo']
                                  },
                       'season': {'year': season_dict['year'],
                                  'start_date': season_dict['start'],
                                  'end_date': season_dict['end']
                                  }
                       }
        return season_data


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
    season_data = s._get_season_data()
    print(season_data)

