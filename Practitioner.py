import re
import utils
TRANSLATION_TABLE = str.maketrans("éèêàïîô'", "eeeaiio-")

def arrays_have_common_elements(array1, array2):
    return len(list(filter(lambda x: x in array2, array1))) > 0


class Practitioner:
    def __init__(self, name, speciality, visiting_motive_keywords=[], visiting_motive_forbidden_keywords=[]):
        """
        initialises the Practitioner class (can also be an office). If user requests for visiting motive keywords, 
        the visiting motive that matches the most keywords will be taken. In case of equality, all the highest
        matching will be taken.
        :param name - String : name or practice name but without title
        :param [optional] visiting_motive_keywords - array[strings] : list of keywords to look for in visit motives
        """
        self.name = name
        self.speciality = speciality
        self.next_slots = {}
        self.agenda_ids = []
        self.practice_ids = []
        self.visit_motives = {}
        self.visiting_motive_keywords = visiting_motive_keywords
        self.visiting_motive_forbidden_keywords = visiting_motive_forbidden_keywords

    def fetch_data_from_name(self):
        """
        will fetch json data based on the Practitioner's name, and sets necessary data for the class
        """
        name_for_url = self.name.replace(" ", "-").lower().translate(TRANSLATION_TABLE)
        name_for_url = re.sub(r'-+', '-', name_for_url)
        url = f"https://www.doctolib.fr/online_booking/draft/new.json?id={name_for_url}"
        # data = utils.fetch_json_data_from_url(url)
        from pathlib import Path
        CURR_FOLDER = Path(__file__).parent.resolve()
        CONF_FILE = CURR_FOLDER/"url_requests"/"hospital.json"
        data = utils.get_json_data(CONF_FILE)
        if data:
            data = data.get("data", {})

            # fetch visit motives ids and their names. Only take the highest matching motives. If no visiting_motive_keywords was
            # given, we'll be storing all of them.
            motive_names = []
            num_keyword_match = []
            for visit_motive in data["visit_motives"]:
                if len([match for match in self.visiting_motive_forbidden_keywords if match.lower() in visit_motive["name"].lower()]) == 0:
                    motive_names.append(visit_motive["name"])
                    num_keyword_match.append(len([match for match in self.visiting_motive_keywords if match.lower() in visit_motive["name"].lower()]))
            if not num_keyword_match:
                return False
            max_match = max(num_keyword_match)
            for idx, item in enumerate(list(motive_names)):
                if num_keyword_match[idx] != max_match:
                    motive_names.remove(item)
            
            motive_ids = []
            motive_category_ids = []
            speciality_ids = []
            organization_ids = []
            for visit_motive in data["visit_motives"]:
                if visit_motive["name"] in motive_names:
                    if "id" in visit_motive.keys(): 
                        motive_ids.append(visit_motive["id"])
                        self.visit_motives[visit_motive["id"]] = visit_motive["name"]
                    if "speciality_id" in visit_motive.keys(): speciality_ids.append(visit_motive["speciality_id"])
                    if "organization_id" in visit_motive.keys(): organization_ids.append(visit_motive["organization_id"])
                    if "visit_motive_category_id" in visit_motive.keys(): motive_category_ids.append(visit_motive["visit_motive_category_id"])
            # remove duplicates
            motive_ids = list(dict.fromkeys(motive_ids))
            motive_category_ids = list(dict.fromkeys(motive_category_ids))
            speciality_ids = list(dict.fromkeys(speciality_ids))
            organization_ids = list(dict.fromkeys(organization_ids))
 

            # fetch agenda ids
            for agenda in data["agendas"]:
                if not agenda["booking_disabled"] and not agenda["booking_temporary_disabled"]:
                    if len(agenda['visit_motive_ids']) > 0 and arrays_have_common_elements(agenda['visit_motive_ids'], motive_ids)  or\
                        (agenda['organization_id'] and agenda['organization_id'] in organization_ids)                               or\
                        (agenda['speciality_id'] and agenda['speciality_id'] in speciality_ids)                                     or\
                        (agenda['visit_motive_ids'] and arrays_have_common_elements(agenda['visit_motive_ids'], motive_ids)):

                        self.agenda_ids.append(agenda["id"])
                        if "practice_id" in agenda.keys(): self.practice_ids.append(agenda["practice_id"])
                        # remove duplicates
            self.agenda_ids = list(dict.fromkeys(self.agenda_ids))
            self.practice_ids = list(dict.fromkeys(self.practice_ids))

            return True

    def get_next_available_appointments(self):
        """ """
        start_day = "2000-01-01"  # we take an old day to make sure no appointment will be available, so we can simply fetch the "next_slot" value
        for practice_id in self.practice_ids:
            for visit_motive_id in self.visit_motives.keys():
                for agenda_id in self.agenda_ids:
                    url_to_check = f"https://www.doctolib.fr/availabilities.json?" +\
                                   f"start_date={start_day}&"                      +\
                                   f"visit_motive_ids={visit_motive_id}&"          +\
                                   f"agenda_ids={agenda_id}&"                      +\
                                   f"practice_ids={practice_id}&limit=2"
                    data = utils.fetch_json_data_from_url(url_to_check)
                    if data:
                        if "next_slot" in data.keys():
                            self.next_slots[visit_motive_id] = data["next_slot"]

if __name__ == "__main__":
    p = Practitioner("name", "ORL", ["premiere", "consultation"], ["suivi"])
    a = p.fetch_data_from_name()
    print(a)