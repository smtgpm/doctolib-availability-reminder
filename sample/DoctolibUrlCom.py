"""
This file is in between any requests made towards doctolib.fr. It'll track the amount made, can be used tu limit and control the 
number of requests made.
TODO: use it more appropriately, check the allowed number of requests of every call made to doctolib and tune this file in accordance to it
"""
import sys
import json
import requests

from enum import Enum
from pathlib import Path
from datetime import datetime

sys.path.insert(0, "sample")
import utils


CURR_FOLDER = Path(__file__).parent.resolve()
URL_COM_FILE = CURR_FOLDER.parent/"data"/"doctolib_url_com_data.json"


class UrlType(Enum):
    MAIN_DOCTOLIB_FR = 1
    AVALIABILITIES = 2
    ONLINE_BOOKING = 3
    UNKNOWN = 4
    NONE = 5


# how many seconds until a request is forgotten
REQUEST_TIME_LIMIT_S = {
    UrlType.MAIN_DOCTOLIB_FR: 24*60*60,  # 24 hours
    UrlType.AVALIABILITIES:   24*60*60,  # 24 hours
    UrlType.ONLINE_BOOKING:   24*60*60   # 24 hours
}
# numbner of requests allowed within the time limit
REQUEST_RATE_PER_TIME_LIMIT = {
    UrlType.MAIN_DOCTOLIB_FR: 5000,
    UrlType.AVALIABILITIES:   5000,
    UrlType.ONLINE_BOOKING:   5000
}

class Singleton(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            # don't want __init__ to be called every time
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class DoctolibUrlCom(metaclass=Singleton):
    """
    class that will communicate with doctolib.fr. Used mainly torequest and track amount
    of requests as to not become banned, so there should only be one instance of this class
    """
    def __init__(self):
        url_com_data = utils.get_file_json_data(URL_COM_FILE)
        self.logger =  utils.logger
        if url_com_data and {'MAIN_DOCTOLIB_FR', 'AVALIABILITIES', 'ONLINE_BOOKING'}.issubset(url_com_data.keys()):
            self._requests_dates = {
                UrlType.MAIN_DOCTOLIB_FR: url_com_data['MAIN_DOCTOLIB_FR'],
                UrlType.AVALIABILITIES: url_com_data['AVALIABILITIES'],
                UrlType.ONLINE_BOOKING: url_com_data['ONLINE_BOOKING']
            }
        else:
            self._requests_dates = {
                UrlType.MAIN_DOCTOLIB_FR: [],
                UrlType.AVALIABILITIES: [],
                UrlType.ONLINE_BOOKING: []
            }
        self._builtin_open = open  # to be able to call it during destruction 

    def __del__(self):
        self.dump_to_url_com_file()

    def dump_to_url_com_file(self):
        dump_data = {
            'MAIN_DOCTOLIB_FR': self._requests_dates[UrlType.MAIN_DOCTOLIB_FR],
            'AVALIABILITIES':self._requests_dates[UrlType.AVALIABILITIES],
            'ONLINE_BOOKING':self._requests_dates[UrlType.ONLINE_BOOKING]
        }
        with self._builtin_open(URL_COM_FILE, 'w') as f:
            json.dump(dump_data, f, indent=4, sort_keys=True, default=str)

    def request_from_json_url(self, url):
        """
        will extract the data from given url (needs to be in json format) if the rate is within allowed limits
        """
        # Parse the JSON content
        url_type = self.get_url_type(url)
        if self.is_request_allowed(url_type):
            try:
                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
                }
                response = requests.get(url, headers=headers)
                response.raise_for_status()  # Check for any request errors
                json_data = response.json()
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Error: Unable to fetch JSON data from the URL: {e}")
                return None
            self._requests_dates[url_type].append(datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"))
            self.dump_to_url_com_file()
            return utils.CustomJSON(json_data)
        else:
            return None
    
    def is_request_allowed(self, url_type):
        """
        cleans the too old requests from given type, and returns if we can request or not 
        """
        if type(url_type) != UrlType or url_type == UrlType.NONE:
            return False
        elif url_type == UrlType.UNKNOWN:
            return True
        
        curr_time = datetime.now()
        # first we clean the _requests_dates
        self._requests_dates[url_type] = [d for d in self._requests_dates[url_type] if (curr_time - datetime.strptime(d, '%Y-%m-%d %H:%M:%S.%f')).total_seconds() < REQUEST_TIME_LIMIT_S[url_type]]
        return len(self._requests_dates[url_type]) < REQUEST_RATE_PER_TIME_LIMIT[url_type]

    @staticmethod
    def get_url_type(url):
        """
        will check the url and returns the url_type
        :param url - String
        :return url_type - UrlType
        """
        if "https://www.doctolib.fr" in url:
            if "https://www.doctolib.fr/availabilities.json" in url:
                url_type = UrlType.AVALIABILITIES
            elif "https://www.doctolib.fr/online_booking/" in url:
                url_type = UrlType.ONLINE_BOOKING
            else:
                url_type = UrlType.MAIN_DOCTOLIB_FR
        elif "https://" in url:
            url_type = UrlType.UNKNOWN
        else:
            url_type = UrlType.NONE
        return url_type
