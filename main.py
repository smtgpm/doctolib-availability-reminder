"""
For now works only for single page
"""
import utils
from pathlib import Path
from datetime import datetime
from EmailSender import EmailSender
from Practitionner import Practitionner
from DoctolibUrlCom import DoctolibUrlCom

# available titles to be removed from names_with_titles
AVAILABLE_TITLES = ["Dr", "M.", "Monsieur", "Mr", "Madame", "Mme", "Mlle", "Mademoiselle"]
CURR_FOLDER = Path(__file__).parent.resolve()
CONF_FILE = CURR_FOLDER/"conf"/"config.json"


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


def fetch_practitionners(config):
    """
    will fetch all practitionners around given address within wanted distance (cf config.json)
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
    json_data = utils.fetch_json_data_from_url(f"{url}.json", file_refresh_rate)
    if json_data:
        for doctor in json_data.get("data", {}).get("doctors", []):
            if float(doctor['distance']) < max_dist_km:
                name_with_title = doctor['name_with_title'].split()
                if name_with_title[0] in AVAILABLE_TITLES:
                    name_with_title = name_with_title[1:]
                names.append(" ".join(name_with_title))
                distances.append("{:.2f}".format(doctor['distance']))
                pids.append(doctor['id'])
            else: # max distance has been reached, we can stop
                break
    return names, distances, pids


def main():
    doctolib_url_com = DoctolibUrlCom()
    conf_data = utils.get_json_data(CONF_FILE)
    if conf_data:
        all_practitionners, dist, pids = fetch_practitionners(conf_data)

        email_message = ""

        for i in range(len(all_practitionners)):
            print(f"{all_practitionners[i]} ({pids[i]}) à une distance de {dist[i]}km de votre adresse")
            p = Practitionner(all_practitionners[i], conf_data["visiting_motive_keywords"], conf_data["visiting_motive_forbidden_keywords"])
            useful_pract = p.fetch_data_from_name()
            if not useful_pract:
                continue
            p.get_next_available_appointments()
            if p.next_slots:
                email_message += f"Practitionner : {p.name}\n" +\
                                 f"Type : {p.speciality}\n"+\
                                 f"Distance from address : {dist[i]} km\n"+\
                                 f"Next available slots :\n"
                for motive_id in p.next_slots.keys():
                    email_message += f"{p.visit_motives[motive_id]} : {p.next_slots[motive_id].split('T')[0]}\n"
                email_message += "\n\n"
    es = EmailSender.from_file()
    es.create_email_message(subject="next slots on doctolib",
                            message=email_message,
                            recipients="test@gmail.com")
    es.send_email()

if __name__ == "__main__":
    main()
