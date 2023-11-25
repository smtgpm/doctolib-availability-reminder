"""
This class will regroup all the info per practitionner. can definetly be improved, the usage is too narrow still.
"""
import sys

sys.path.insert(0, "sample")
import utils as utils
from DoctolibUrlCom import DoctolibUrlCom

TRANSLATION_TABLE = str.maketrans("ëéèêàïîô'ç", "eeeeaiio-c")


def fetch_json_data_from_profile_url(profile_url):
    """
    This function takes the URL of a profile on doctolib and returns the json data from it.
    :param profile_url - url copy pasted from doctolib.fr's profile.
    :return (slug_name, json_data) : (str, dict)
    """
    p_url = profile_url
    if "doctolib.fr/" in p_url:
        p_url = p_url.split("doctolib.fr/")[1]  # remove first part of the name
    p_url = p_url.split("?")[0]                 # remove any aditional unecessary parameters at end of link
    splitted_link = p_url.split("/")
    if len(splitted_link) != 3:
        utils.logger.error(f"[ERROR] link {profile_url} does not have format 'type/city/name'.")
        return (None, None)
    slug_name = splitted_link[2]

    # fetch all necessary data to sort out and classify our profile(s)
    url = f"https://www.doctolib.fr/online_booking/draft/new.json?id={slug_name}"
    json_data = DoctolibUrlCom().request_from_json_url(url)
    if json_data is None:
        utils.logger.error(f"[ERROR] link {url} couldn't fetch the json data. Does {profile_url} have the format (...)doctolib.fr/type/city/name(...) ?")
        return (None, None)
    return (slug_name, json_data.get("data", {}))


class Practitioner:
    def __init__(self, slug_name, json_data):
        """ 
        :param slug_name - str : this is the name visible in a profile's URL. Usually it's the first-and-lastname without any special characters
        :param json_data - dict: data retrieved from the response of https://www.doctolib.fr/online_booking/draft/new.json?id=<slug_name>
        """
        self.is_ok = False
        self.logger = utils.logger
        try:
            if not json_data["profile"]["speciality"] or \
               not json_data["visit_motives"]         or \
               not json_data["agendas"]                   :
                self.logger.debug(f"the json_data provided is missing mandatory data, here is a dump of the data for debug:\n{json_data}")
                raise Exception(f"the json_data provided is missing mandatory data")
            self.slug_name = slug_name
            self.next_slots = []
            
            # fetch all necessary data :
            self.glob_type = json_data["profile"]["speciality"]["slug"]
            self.speciality_id = json_data["profile"]["speciality"]["id"]
            self.practitioner_name = json_data["profile"]["name_with_title"]
            self.speciality_name = json_data["profile"]["speciality"]["name"]
            
            self.practice_address_by_id = {}
            for place in json_data["places"]:
                for practice_id in place["practice_ids"]:
                    self.practice_address_by_id[practice_id] = f"{place['address']}, {place['zipcode']} {place['city']}"

            self.visit_motives = {}
            for vm in list(json_data["visit_motives"]):
                if (vm["speciality_id"] != self.speciality_id):
                    continue
                self.visit_motives[vm["id"]] = vm["name"].lower().translate(TRANSLATION_TABLE)

            self.agendas = {}
            for ag in list(json_data["agendas"]):
                if ag["booking_disabled"] or ag["booking_temporary_disabled"] or ag["speciality_id"] != self.speciality_id:
                    continue
                self.agendas[ag["id"]] = ag["visit_motive_ids_by_practice_id"]  # ag["visit_motive_ids_by_practice_id"] is a dictionnary :  key = practice id, item = [motive ids]

            self.is_ok = True
            self.logger.info(f"Practitioner {self.practitioner_name}'s object was successfully created")
        except Exception as e:
            self.logger.error(f"Failed to create a Practitionner object:\n{e}")

    def narrow_search_based_on_keywords(self, keywords=[], forbidden_keywords=[]):
        """
        Some practitionners have way too many agendas and/or visit motives, and he/she might have an abailability on some visit motive
        that does not interest the user. So this function is to trim any agenda/visit_motive that is not required to be looked at
        """
        keywords = [k.lower().translate(TRANSLATION_TABLE) for k in keywords]
        forbidden_keywords = [k.lower().translate(TRANSLATION_TABLE) for k in forbidden_keywords]
        self.logger.debug(f"Removing any visit_motive or agenda to narrow the availability search.\nLooking for these keywords: {keywords}\nRefusing these keywords:{forbidden_keywords}")

        # first we trim the visit motives. We'll remove any motive that has a forbidden keyword, and keep the ones that have the
        # highest number of matches with keywords
        highest_num_of_keyword_matches = 0
        for _, motive in self.visit_motives.items():
            highest_num_of_keyword_matches = max(highest_num_of_keyword_matches, sum(k in motive for k in keywords))

        motive_ids_to_remove = []
        for id, motive in self.visit_motives.items():
            if any(word in motive for word in forbidden_keywords) or sum(word in motive for word in keywords) < highest_num_of_keyword_matches:
                motive_ids_to_remove.append(id)

        # Removing items from 'self.visit_motives' based on 'motive_ids_to_remove'
        for id in motive_ids_to_remove:
            self.visit_motives.pop(id, None)

        # no we can trim the agendas
        agenda_ids_to_remove = []
        visit_motive_ids = list(self.visit_motives.keys())
        for agenda_id, visit_motive_ids_by_practice_id in self.agendas.items():
            practice_ids_to_remove = []
            for practice_id, agenda_motive_ids in visit_motive_ids_by_practice_id.items():
                if not utils.arrays_have_common_elements(agenda_motive_ids, visit_motive_ids):
                    practice_ids_to_remove.append(practice_id)
            # Removing items from 'visit_motive_ids_by_practice_id' based on 'practice_ids_to_remove'
            for practice_id in practice_ids_to_remove:
                visit_motive_ids_by_practice_id.pop(practice_id, None)
            if len(visit_motive_ids_by_practice_id) == 0:
                agenda_ids_to_remove.append(agenda_id)
        # Removing items from 'self.agendas' based on 'agenda_ids_to_remove'
        for agenda_id in agenda_ids_to_remove:
            self.agendas.pop(agenda_id, None)

        if len(self.visit_motives) == 0 or len(self.agendas) == 0:
            self.logger.error("There are no more available agendas or visit_motives. Verify your 'forbidden_keywords' as they might be too restrictive")
            return None
        self.logger.debug(f"SUCCESS: {len(motive_ids_to_remove)} visit_motives have been removed and {len(agenda_ids_to_remove)} agendas.")

    def get_next_available_appointment(self):
        """ will parse all agendas and visit motives of current practitionner, and look at the next available slots """
        self.logger.info("Looking into the agendas and visit motives, and checking the next available slots...")
        found_slot = False
        start_day = "2000-01-01"  # we take an old day to make sure no appointment will be available, so we can simply fetch the "next_slot" value
        for motive_id, _ in self.visit_motives.items():
            for agenda_id, visit_motive_ids_by_practice_id in self.agendas.items():
                for practice_id, _ in visit_motive_ids_by_practice_id.items():
                    url_to_check = f"https://www.doctolib.fr/availabilities.json?" +\
                                    f"start_date={start_day}&"                     +\
                                    f"visit_motive_ids={motive_id}&"      +\
                                    f"agenda_ids={agenda_id}&"                  +\
                                    f"practice_ids={practice_id}&limit=2"
                    json_data = DoctolibUrlCom().request_from_json_url(url_to_check)
                    if json_data:
                        if "next_slot" in json_data.keys() and "Aucune" not in json_data["next_slot"]:
                            next_slot = {}
                            next_slot["date"] = json_data["next_slot"].split("T")[0]
                            next_slot["motive_id"] = motive_id
                            next_slot["agenda_id"] = agenda_id
                            next_slot["practice_id"] = int(practice_id)
                            next_slot["send_reminder"] = False
                            self.next_slots.append(next_slot)
                            found_slot = True
                            self.logger.info(f"Next available slot for {self.visit_motives[motive_id]} : {next_slot['date']}")
        if not found_slot:
            self.logger.info(f"This practitionner does not have any future available slots.")
        return found_slot

if __name__ == "__main__":
    my_pract = Practitioner.from_url("https://www.doctolib.fr/dentiste/paris/rita-halhal?pid=practice-3680")
    if my_pract and my_pract.is_ok:
        my_pract.narrow_search_based_on_keywords(keywords=["premiere", "consultation"], forbidden_keywords=["chirurgie"])
        found_slot = my_pract.get_next_available_appointment()
        if found_slot:
            print(f"At least one available slot has been found for {my_pract.practitioner_name}:")
            for slot in my_pract.next_slots:
                print(f"for \"{my_pract.visit_motives[slot['motive_id']]}\", next available slot will be : {slot['date']} at {my_pract.practice_address_by_id[slot['practice_id']]}")
            