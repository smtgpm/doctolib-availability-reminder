"""
"""
from pathlib import Path
from datetime import datetime, timedelta

import sample.utils as utils

from sample.EmailSender import EmailSender
from sample.Practitioner import Practitioner
from sample.DoctolibUrlCom import DoctolibUrlCom

CURR_FOLDER = Path(__file__).parent.resolve()

# available titles to be removed from names_with_titles
AVAILABLE_TITLES = ["Dr", "M.", "Monsieur", "Mr", "Madame", "Mme", "Mlle", "Mademoiselle"]
CONF_FILE = CURR_FOLDER.parent/"conf"/"config.json"
AVAILABILITY_REMINDER_DATA_FILE = CURR_FOLDER.parent/"data"/"availability_reminder_data.json"


class AvailabilityReminder():
    """
    this is the main class that will setup your doctolib parser and globally make sure to send email reminders
    """
    def __init__(self):
        self.practitioner_names = []  # only the names of potentiel practitioners to check
        self.dist_from_adress = {}    # dist_from_adress[name] = distance
        self.config_data = utils.get_json_data(CONF_FILE)
        self.practitioners = []  # this is the list that'll conain practitioners data in form of Practitioner types
        self.email_sender = EmailSender.from_env()
        self.email_message = ""

    def fetch_practitioner_names_around_address(self, practitioner_type=None, city=None, street_name=None, max_dist_km=None):
        """
        will fetch all practitioners around given address within wanted distance. Any input can be optional, and if
        None is given, it'll take it from the conf/config.json file.
        Notes:
         - street_name should not contain the number.
         - practitioner_type shoould be the "slug" of the type. To get this, please go on doctolib.fr, do a research 
            of what type you would like, and extract the slug from the generated URL. For example, when searching for 'ORL'
            in the city of Toulouse, it generates this link: https://www.doctolib.fr/orl-oto-rhino-laryngologie/toulouse, 
            so the slug for ORL is 'orl-oto-rhino-laryngologie'
        :param [optional] practitioner_type - String
        :param [optional] city - String
        :param [optional] street_name - String
        :param [optional] max_dist_km - float : max dist to look from givent street
        """
        if practitioner_type is None:
            practitioner_type = self.config_data["practitioner_type"]
        if city is None:
            city = self.config_data["city"]
        if street_name is None:
            street_name = self.config_data["street_name"]
        if max_dist_km is None:
            max_dist_km = 10000.0
            if self.config_data["max_dist_from_address_km"]:
                max_dist_km = float(self.config_data["max_dist_from_address_km"])

        # first we generate the search url that will be requested from doctolib.fr
        practitioner_type = practitioner_type.replace(" ", "-").lower()
        city = city.replace(" ", "-").lower()
        street_name = street_name.replace(" ", "-").lower()
        base_url = "https://www.doctolib.fr/"
        url = f"{base_url}{practitioner_type}/{city}-{street_name}.json"

        # and finally we go and parse the url, retrieve all practitioner names around given adress.
        # TODO: figure out a way to parse more than 1 page (ie more than 20 results)
        json_data = DoctolibUrlCom().request_from_json_url(url)
        if json_data:
            for doctor in json_data.get("data", {}).get("doctors", []):
                if float(doctor['distance']) < max_dist_km:
                    name_without_title = doctor['name_with_title']
                    if name_without_title.split()[0] in AVAILABLE_TITLES:
                        name_without_title = " ".join(name_without_title.split()[1:])
                    
                    self.add_practitioner_to_check_list(name_without_title)
                    self.dist_from_adress[name_without_title] = "{:.2f}".format(doctor['distance'])
                else: # max distance has been reached, we can stop
                    break
        else:
            return False
        return True

    def add_practitioner_to_check_list(self, name):
        """
        instead (or in addition) to looking for practitioners of a given type around an address, you can also
        just add specific practitioners to the checklist so that the availabilityReminder checks them for available slots
        Just go on doctolib, look for your practitioner, and give the name. It can also be a health center, hospital... etc
        Note:
            Sometimes the naming taken for url is not exactly the name of the practitiner / center / hospital.
            To make sure you have the proper name, when you are on the profiles url, look in the url for the name. 
            Usually, it's at the end of the url, and before any '?' commands. For example:
            https://www.doctolib.fr/rhumatologue/toulouse/marine-eischen?pid=practice-188510 - name is marine-eischen
            https://www.doctolib.fr/hopital-public/clamart/centre-de-medecine-du-sommeil-hopital-antoine-beclere-ap-hp - name is centre-de-medecine-du-sommeil-hopital-antoine-beclere-ap-hp
        :param name - string : practitioner / health center's name
        """
        self.practitioner_names.append(name)

    def get_practitioners_data(self):
        """
        """
        for i in range(len(self.practitioner_names)):
            name = self.practitioner_names[i]
            print(f"checking for {name}")
            p = Practitioner(name=name,
                             speciality=self.config_data["practitioner_type"],
                             visiting_motive_keywords=self.config_data["visiting_motive_keywords"],
                             visiting_motive_forbidden_keywords=self.config_data["visiting_motive_forbidden_keywords"],
                             distance=(None if name not in self.dist_from_adress.keys() else self.dist_from_adress[name]))
            if (p.fetch_data_from_name()):
                self.practitioners.append(p)

    def find_available_slots(self):
        """ TODO """
        available_slot = False
        max_date = datetime.today()
        if self.config_data["max_days_from_today_for_reminder"]:
            max_date = max_date + timedelta(days=int(self.config_data["max_days_from_today_for_reminder"]))
        max_date = max_date.strftime("%Y-%m-%d")
        if self.config_data["max_date_slot_for_reminder"]:
            if utils.compare_dates(self.config_data["max_date_slot_for_reminder"], max_date) == -1:
                max_date = self.config_data["max_date_slot_for_reminder"]
 
        for p in self.practitioners:
            p.get_next_available_appointments()
            free_slots = p.available_slot_before_date(max_date)
            if free_slots:
                available_slot = True
                self.add_practitioner_slots_to_email(p)
        return available_slot
        
    def add_practitioner_slots_to_email(self, practitioner):
        self.email_message += f"Practitioner : {practitioner.name}\nType : {practitioner.speciality}\n"
        if practitioner.distance is not None:
            self.email_message +=  f"Distance from address : {practitioner.distance} km\n"
        self.email_message += f"Next available slots :\n"
        for motive_id in practitioner.next_slots.keys():
            self.email_message += f"{practitioner.visit_motives[motive_id]} : {practitioner.next_slots[motive_id].split('T')[0]}\n"
        self.email_message += "\n\n"

    def run(self, check_around_address=True):
        """
        if you want the run to be done without the check around config's address, make sure you add 
        practitionners to the check_list using add_practitioner_to_check_list().
        :param [optional] check_around_address - bool : if true, it'll parse the main config file and look for all practitioners around the given adress
        """
        if check_around_address:
            self.fetch_practitioner_names_around_address()
        self.get_practitioners_data()
        available_slots = self.find_available_slots()

        if available_slots:
            self.email_sender.create_email_message(subject="Doctolib Availability Reminder : new slots available !",
                                                   message=self.email_message)  # assuming environment variable ES_RECEIPIENTS is set
            self.email_sender.send_email()