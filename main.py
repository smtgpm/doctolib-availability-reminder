"""
For now works only for single page
"""
import os
import json
import random
import requests
from datetime import datetime
from fake_useragent import UserAgent

# available titles to be removed from names_with_titles
AVAILABLE_TITLES = ["Dr", "M.", "Monsieur", "Mr", "Madame", "Mme", "Mlle", "Mademoiselle"]
TRANSLATION_TABLE = str.maketrans("éèêàïîô", "eeeaiio")
CURR_FOLDER = os.path.dirname(os.path.abspath(__file__))

class Practitionner:
    def __init__(self, name, visiting_motive_keywords=[""]):
        """
        initialises the practitionner class (can also be an office). If user requests for visiting motive keywords, 
        the visiting motive that matches the most keywords will be taken. In case of equality, all the highest
        matching will be taken.
        :param name - String : name or practice name but without title
        :param [optional] visiting_motive_keywords - array[strings] : list of keywords to look for in visit motives
        """
        self.name = name
        self.next_slots = {}
        self.agenda_ids = []
        self.practice_ids = []
        self.visit_motive_ids = {}
        self.visiting_motive_keywords = visiting_motive_keywords

    def fetch_data_from_name(self):
        """
        will fetch json data based on the practitionner's name, and sets necessary data for the class
        """
        name_for_url = self.name.replace(" ", "-").lower().translate(TRANSLATION_TABLE)
        url = f"https://www.doctolib.fr/online_booking/draft/new.json?id={name_for_url}"
        data = fetch_json_data(url)
        if data is not None:
            data = data.get("data", {})
            # fetch practice ids
            for place in data["places"]:
                for id in place["practice_ids"]:
                    self.practice_ids.append(id)

            # fetch visit motives ids and their names. Only take the highest matching motives. If no visiting_motive_keywords was
            # given, we'll be storing all of them.
            motive_ids = []
            motive_names = []
            num_keyword_match = []
            for visit_motive in data["visit_motives"]:
                motive_ids.append(visit_motive["id"])
                motive_names.append(visit_motive["name"])
                num_keyword_match.append(len([match for match in self.visiting_motive_keywords if match.lower() in visit_motive["name"].lower()]))
            max_match = max(num_keyword_match)
            for i in range(len(motive_ids)):
                if num_keyword_match[i] == max_match:
                    self.visit_motive_ids[motive_ids[i]] = motive_names[i]
                
            # fetch agenda ids
            for agenda in data["agendas"]:
                if not agenda["booking_disabled"] and not agenda["booking_temporary_disabled"]:
                    self.agenda_ids.append(agenda["id"])

    def get_next_available_appointments(self):
        """ """
        start_day = "2000-01-01"  # we take a very old day to make sure no appointment will be available, so we can simply fetch the "next_slot" value
        for practice_id in self.practice_ids:
            for visit_motive_id in self.visit_motive_ids.keys():
                for agenda_id in self.agenda_ids:
                    url_to_check = f"https://www.doctolib.fr/availabilities.json?" +\
                                   f"start_date={start_day}&"                      +\
                                   f"visit_motive_ids={visit_motive_id}&"          +\
                                   f"agenda_ids={agenda_id}&"                      +\
                                   f"practice_ids={practice_id}&limit=2"
                    data = fetch_json_data(url_to_check)
                    if data is not None:
                        if "next_slot" in data.keys():
                            self.next_slots[visit_motive_id] = data["next_slot"]
                        else:
                            self.next_slots[visit_motive_id] = "No available slot for now..."

                        print(f"for a \"{self.visit_motive_ids[visit_motive_id]}\", next available slot is : {self.next_slots[visit_motive_id]}")


def generate_doctolib_search_url(practitionner_type, city, street_name):
    """
    creates the doctolib json URL that will return all available practitionners
    around given address. street_name should not contain the number. regarding practitionner type, 
    please go on doctolib.fr, do a research of what type you would like, and extract the type
    from the URL. For example, when searching for 'ORL', it generates this link:
    https://www.doctolib.fr/orl-oto-rhino-laryngologie/toulouse, so the type is orl oto rhino laryngologie
    :param practitionner_type - String
    :param city - String
    :param street_name - String
    """
    # Base URL
    practitionner_type = practitionner_type.replace(" ", "-").lower()
    city = city.replace(" ", "-").lower()
    street_name = street_name.replace(" ", "-").lower()
    base_url = "https://www.doctolib.fr/"

    # Construct the URL
    url = f"{base_url}{practitionner_type}/{city}-{street_name}"
    return url


def fetch_json_data(url, max_hours_before_reset=0.0):
    """
    This will fetch the json data from given URL. Since doctolib.fr is very limiting in the number
    of requests allowed, the data is stored in json files and if the json file associated to the URL
    exists, the data will be taken from that file instead of an URL request. 
    In case the json file was created more hours ago than max_hours_before_reset, we reset the json
    file by requesting from URL the data. 0 will always be resetting
    :param max_hours_before_reset - float
    """
    curr_time = datetime.now()
    # first we look into stored jsons if the requests has already been made
    json_data_file = ""
    url_requests_folder = os.path.join(CURR_FOLDER, "url_requests")
    for filename in os.listdir(url_requests_folder):
        if filename.endswith(".json"):
            with open(os.path.join(url_requests_folder, filename), 'r') as f:
                data = json.load(f)
            if data["current_url"] == url:
                # this URL has already been stored
                json_dump_time = datetime.strptime(data["dump_time"], "%Y-%m-%d %H:%M:%S.%f")
                time_diff = curr_time - json_dump_time
                hour_difference = time_diff.total_seconds() / 3600.0
                if hour_difference <= max_hours_before_reset:
                    return data["json_data"]
                json_data_file = filename
                break
    # Parse the JSON content
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()  # Check for any request errors
        json_data = response.json()
    except requests.exceptions.RequestException as e:
        print("Error: Unable to fetch JSON data from the URL.")
        print(str(e))
        return None

    data = {}
    data["json_data"] = json_data
    data["current_url"] = url
    data["dump_time"] = curr_time
    if json_data_file == "":
        json_data_file = str(len(os.listdir(url_requests_folder))) + ".json"
    with open(os.path.join(url_requests_folder, json_data_file), 'w') as f:
        json.dump(data, f, indent=4, sort_keys=True, default=str)
    return json_data


def fetch_practitionners(config):
    """
    will fetch all practitionners from given adress within wanted distance (cf config.json)
    :param config - dict : config.json data
    """
    # first we generate the search url that will be requested from doctolib.fr
    url = generate_doctolib_search_url(city=config["city"],
                                       street_name=config["street_name"],
                                       practitionner_type=config["practitionner_type"])
    max_dist_km = 10000.0
    if config["max_dist_from_address_km"]:
        max_dist_km = float(config["max_dist_from_address_km"])
    names = []
    distances = []
    pids = []
    file_refresh_rate = 0.0
    if config["prog_behavior"]["doctolib_request_rate_hrs"]:
        file_refresh_rate = float(config["prog_behavior"]["doctolib_request_rate_hrs"])
    json_data = fetch_json_data(f"{url}.json", file_refresh_rate)
    if json_data:
        for doctor in json_data.get("data", {}).get("doctors", []):
            if float(doctor['distance']) < max_dist_km:
                name_with_title = doctor['name_with_title'].split()
                if name_with_title[0] in AVAILABLE_TITLES:
                    name_with_title = name_with_title[1:]
                names.append(" ".join(name_with_title))
                distances.append(doctor['distance'])
                pids.append(doctor['id'])
    return names, distances, pids


def main():
    with open(os.path.join(CURR_FOLDER, "config.json"), 'r') as f:
        conf_data = json.load(f)
    all_practitionners, dist, pids = fetch_practitionners(conf_data)
    
    for i in range(len(all_practitionners)):
        print(f"{all_practitionners[i]} ({pids[i]}) à une distance de {round(dist[i], 2)}km de votre adresse")
        p = Practitionner(all_practitionners[i], conf_data["visiting_motive_keywords"])
        p.fetch_data_from_name()
        p.get_next_available_appointments()
    

if __name__ == "__main__":
    main()
    #https://www.doctolib.fr/availabilities.json?start_date=2024-03-12&visit_motive_ids=392647&agenda_ids=1364767&insurance_sector=public&practice_ids=157973&limit=6
