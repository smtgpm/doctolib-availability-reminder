"""
"""
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, "sample")
import utils
from EmailSender import EmailSender
from Practitioner import Practitioner
from DoctolibUrlCom import DoctolibUrlCom

CURR_FOLDER = Path(__file__).parent.resolve()

# available titles to be removed from names_with_titles
AVAILABLE_TITLES = ["Dr", "M.", "Monsieur", "Mr", "Madame", "Mme", "Mlle", "Mademoiselle"]
AVAILABILITY_REMINDER_DATA_FILE = CURR_FOLDER.parent/"data"/"availability_reminder_data.json"


class AvailabilityReminder():
    """
    this is the main class that will setup your doctolib parser and globally make sure to send email reminders
    """
    def __init__(self):
        self.dist_from_adress = {}    # dist_from_adress[name] = distance
        self.logger = utils.logger
        self.config_data = utils.read_config_file()
        
        self.practitioners = []  # this is the list that'll conain practitioners data in form of Practitioner types
        self.email_sender = EmailSender.from_env()
        self.email_message = ""
    
    def fetch_practitioners_data(self):
        """ depending on the config's read_config_file boolean, it'll extract the practitioner datas and store them in self.practitioners """
        if self.config_data["search_around_address"]:
            self.fetch_practitioners_around_address()
        if self.config_data["profile_urls"]:
            self.fetch_practitioners_from_urls()

    def fetch_practitioners_from_urls(self):
        """
        will fetch all practitioners that have been added in config's 'fetch_practitioners_from_urls' list
        """
        if "profile_urls" not in self.config_data.keys():
            self.logger.warning("'profile_urls' is not part of the config file keys. You should leave it there "
                                "and set keep it to empty if you don't want any URLs to be added to parser")
            return False
        for url in self.config_data["profile_urls"]:
            pract = Practitioner.from_url(url)
            if pract.is_ok:
                self.practitioners.append(pract)
    
    def fetch_practitioners_around_address(self):
        """
        will fetch all practitioners around given address within wanted distance. Please refer to the config.yaml file for setup
        """
        if not self.config_data["practitioner_types"]:
            self.logger.error("while requesting to look around address in the config, no practitioner type has been given to look for...")
            return False            
            
        for practitioner_type in list(self.config_data["practitioner_types"]):
            city = self.config_data["city"]
            street_name = self.config_data["street_name"]
            max_dist_km = 10000.0
            if self.config_data["max_dist_from_address_km"]:
                max_dist_km = self.config_data["max_dist_from_address_km"]

            # first we generate the search url that will be requested from doctolib.fr that'll return all practitioners around address
            practitioner_type = practitioner_type.replace(" ", "-").lower()
            city = city.replace(" ", "-").lower()
            street_name = street_name.replace(" ", "-").lower()
            base_url = "https://www.doctolib.fr"
            url = f"{base_url}/{practitioner_type}/{city}-{street_name}.json"

            # and finally we go and parse the url, retrieve all practitioner names around given adress.
            # TODO: figure out a way to parse more than 1 page (ie more than 20 results)
            json_data = DoctolibUrlCom().request_from_json_url(url)
            if json_data:
                for doctor in json_data.get("data", {}).get("doctors", []):
                    if float(doctor['distance']) < max_dist_km:
                        link = doctor['link']
                        url = base_url + link
                        pract = Practitioner.from_url(url)
                        if pract.is_ok:
                            self.practitioners.append(pract)
                    else: # max distance has been reached, we can stop
                        break
            else:
                return False
            return True

    def find_available_slots(self):
        """
        will parse all of the practitioners calendars and extract the next available slot for each of the visit motives
        that might interest us. If the next available slot is within the maximum date set in the config, it'll add the info
        to any mail content and send an email reminder.
        """
        available_slot = False
        max_date = datetime.today()
        if self.config_data["max_days_from_today_for_reminder"]:
            max_date = max_date + timedelta(days=int(self.config_data["max_days_from_today_for_reminder"]))
        max_date = max_date.strftime("%Y-%m-%d")
        if self.config_data["max_date_slot_for_reminder"]:
            if utils.compare_dates(self.config_data["max_date_slot_for_reminder"], datetime.today()) == -1:
                # in case the date given is previous to today, we ignore the value.
                pass
            elif utils.compare_dates(self.config_data["max_date_slot_for_reminder"], max_date) == -1:
                max_date = self.config_data["max_date_slot_for_reminder"]
 
        for p in self.practitioners:
            self.logger.info(f"\nLooking for slots in {p.practitioner_name}'s calendar...")
            p.narrow_search_based_on_keywords(keywords=self.config_data["visiting_motive_keywords"], 
                                              forbidden_keywords=self.config_data["visiting_motive_forbidden_keywords"])
            found_slot = p.get_next_available_appointment()
            if found_slot:
                for slot in p.next_slots:
                    if utils.compare_dates(slot["date"], max_date) == -1:
                        slot["send_reminder"] = True
                        available_slot = True
                if any(slot.get("send_reminder") for slot in p.next_slots):                
                    self.add_practitioner_slot_to_email(p)
        return available_slot
        
    def add_practitioner_slot_to_email(self, practitioner):
        """ 
        if any of the practitionner's next_slots has a send_reminder set to true, it'll add all the reminders
        to the email bloc.
        """
        if practitioner.next_slots and not any(slot.get("send_reminder") for slot in practitioner.next_slots):
            return
        self.email_message += f"Practitioner : {practitioner.practitioner_name}\nType : {practitioner.speciality_name}\n"
        self.email_message += f"Next available slots :\n"
        for slot in practitioner.next_slots:
            if slot["send_reminder"]:
                self.email_message += f"{practitioner.visit_motives[slot['motive_id']]} : {slot['date']}\n"
        self.email_message += "\n\n"

    def run(self):
        """
        runs all the steps based on the configuration set in the config.yaml file. and sends an email reminder if necessary
        """
        self.fetch_practitioners_data()
        available_slots = self.find_available_slots()
        if available_slots:
            self.email_sender.create_email_message(subject="[Doctolib Availability Reminder] New slots available !",
                                                   message=self.email_message)  # assuming environment variable ES_RECEIPIENTS is set
            self.email_sender.send_email()
            
if __name__ == "__main__":
    ar = AvailabilityReminder()
    ar.run()