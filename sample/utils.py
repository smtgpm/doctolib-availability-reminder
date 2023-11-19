import json
import yaml
import logging
import inspect
from pathlib import Path
from datetime import datetime

CURR_FOLDER = Path(__file__).parent.resolve()
CONF_YAML_FILE = CURR_FOLDER.parent / "config" / "config.yaml"

class CustomLogger:
    def __init__(self, name='my_logger', level=logging.INFO):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create a console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self._logger.addHandler(console_handler)
    
    def _get_calling_class_name(self):
        try:
            stack = inspect.stack()
            # Get the class name from the stack frame
            class_name = stack[2][0].f_locals.get('self', None).__class__.__name__
            return class_name
        except Exception as e:
            # In case of any exception, return 'UnknownClass'
            return 'UnknownClass'
    
    def info(self, message):
        self._logger.info(message)
    
    def warn(self, message):
        self._logger.warning(message)
    
    def error(self, message):
        self._logger.error(message)
    
    def critical(self, message):
        self._logger.critical(message)
    
    def debug(self, message):
        self._logger.debug(message)

logger = CustomLogger()


class CustomJSON(dict):
    """ Instead of throwing exceptions if key not present, it'll just return None """
    def __getitem__(self, key):
        try:
            return super().__getitem__(key)
        except KeyError:
            return None


def read_config_file():
    """ reads ths config.yaml and returns the conf_data in dict format """
    with open(CONF_YAML_FILE, 'r') as f_in:
        try:
            config_data = yaml.safe_load(f_in)
        except Exception as e:
            logger.error(f"Failed to load config file : {e}")
            exit(0)
    return config_data


def arrays_have_common_elements(array1, array2):
    return len(list(filter(lambda x: x in array2, array1))) > 0


def get_file_json_data(json_file_path):
    """
    extracts from json and turns into dict.
    :param json_file_path - pathlib.Path
    :return json_data - dict
    """
    if json_file_path.exists() and json_file_path.is_file() and json_file_path.suffix == ".json":
        try:
            with json_file_path.open() as json_file:
                json_data = json.load(json_file)
        except Exception as e:
            print(f"failed to load json data from {json_file_path} : {str(e)}")
            return None
    else:
        print(f"couldn't properly locate json file {json_file_path}")
        return None
    return CustomJSON(json_data)


def compare_dates(date1, date2):
    """
    compares string dates. Dates should have format YYYY-MM-DD. Returns 1 if date1>date2, 0 if equal, -1 if date1<date2
    """
    if int(date1.split("-")[0]) > int(date2.split("-")[0]):
        return 1
    elif int(date1.split("-")[0]) < int(date2.split("-")[0]):
        return -1
    else:
        if int(date1.split("-")[1]) > int(date2.split("-")[1]):
            return 1
        elif int(date1.split("-")[1]) < int(date2.split("-")[1]):
            return -1
        else:
            if int(date1.split("-")[2]) > int(date2.split("-")[2]):
                return 1
            elif int(date1.split("-")[2]) < int(date2.split("-")[2]):
                return -1
            else:
                return 0
            
        
# not used, only for testing to avoid making requests, this can store requested pages into jsons, and call these jsons later on instead of requesting from net
# def fetch_json_data_from_url(url, max_hours_before_reset=24.0):
#     """
#     This will fetch the json data from given URL. Since doctolib.fr is very limiting in the number
#     of requests allowed, the data is stored in json files and if the json file associated to the URL
#     exists, the data will be taken from that file instead of an URL request. 
#     In case the json file was created more hours ago than max_hours_before_reset, we reset the json
#     file by requesting from URL the data. 0.0 will always be resetting
#     :param max_hours_before_reset - float
#     """
#     curr_time = datetime.now()
#     # first we look into stored jsons if the requests has already been made
#     json_data_file = ""
#     url_requests_folder = CURR_FOLDER / "url_requests"
#     for filename in url_requests_folder.iterdir():
#         data = get_file_json_data(filename)
#         if data and data["current_url"] == url:
#             # this URL has already been stored
#             json_dump_time = datetime.strptime(data["dump_time"], "%Y-%m-%d %H:%M:%S.%f")
#             time_diff = curr_time - json_dump_time
#             hour_difference = time_diff.total_seconds() / 3600.0
#             if hour_difference <= max_hours_before_reset:
#                 return data["json_data"]
#             json_data_file = filename
#             break
#     json_data = DoctolibUrlCom().request_from_json_url(url)
#     if json_data:
#         data = {}
#         data["json_data"] = json_data
#         data["current_url"] = url
#         data["dump_time"] = curr_time
#         if json_data_file == "":
#             # create a new XX.json file
#             json_data_file = str(len([f for f in url_requests_folder.iterdir() if f.is_file() and f.suffix == ".json"])) + ".json"
#         with open(url_requests_folder / json_data_file, 'w') as f:
#             json.dump(data, f, indent=4, sort_keys=True, default=str)
#         return json_data
#     else:
#         return None
    