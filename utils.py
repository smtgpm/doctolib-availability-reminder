import json
from pathlib import Path
from datetime import datetime
from DoctolibUrlCom import DoctolibUrlCom

CURR_FOLDER = Path(__file__).parent.resolve()

def get_json_data(json_file_path):
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
    return json_data


def fetch_json_data_from_url(url, max_hours_before_reset=24.0):
    """
    This will fetch the json data from given URL. Since doctolib.fr is very limiting in the number
    of requests allowed, the data is stored in json files and if the json file associated to the URL
    exists, the data will be taken from that file instead of an URL request. 
    In case the json file was created more hours ago than max_hours_before_reset, we reset the json
    file by requesting from URL the data. 0.0 will always be resetting
    :param max_hours_before_reset - float
    """
    curr_time = datetime.now()
    # first we look into stored jsons if the requests has already been made
    json_data_file = ""
    url_requests_folder = CURR_FOLDER / "url_requests"
    for filename in url_requests_folder.iterdir():
        data = get_json_data(filename)
        if data and data["current_url"] == url:
            # this URL has already been stored
            json_dump_time = datetime.strptime(data["dump_time"], "%Y-%m-%d %H:%M:%S.%f")
            time_diff = curr_time - json_dump_time
            hour_difference = time_diff.total_seconds() / 3600.0
            if hour_difference <= max_hours_before_reset:
                return data["json_data"]
            json_data_file = filename
            break
    json_data = DoctolibUrlCom().request_from_json_url(url)
    if json_data:
        data = {}
        data["json_data"] = json_data
        data["current_url"] = url
        data["dump_time"] = curr_time
        if json_data_file == "":
            # create a new XX.json file
            json_data_file = str(len([f for f in url_requests_folder.iterdir() if f.is_file() and f.suffix == ".json"])) + ".json"
        with open(url_requests_folder / json_data_file, 'w') as f:
            json.dump(data, f, indent=4, sort_keys=True, default=str)
        return json_data
    else:
        return None