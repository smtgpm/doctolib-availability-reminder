import utils
TRANSLATION_TABLE = str.maketrans("éèêàïîô", "eeeaiio")


class Practitionner:
    def __init__(self, name, visiting_motive_keywords=[], visiting_motive_forbidden_keywords=[]):
        """
        initialises the practitionner class (can also be an office). If user requests for visiting motive keywords, 
        the visiting motive that matches the most keywords will be taken. In case of equality, all the highest
        matching will be taken.
        :param name - String : name or practice name but without title
        :param [optional] visiting_motive_keywords - array[strings] : list of keywords to look for in visit motives
        """
        self.name = name
        self.speciality = ""
        self.next_slots = {}
        self.agenda_ids = []
        self.practice_ids = []
        self.visit_motives = {}
        self.visiting_motive_keywords = visiting_motive_keywords
        self.visiting_motive_forbidden_keywords = visiting_motive_forbidden_keywords

    def fetch_data_from_name(self):
        """
        will fetch json data based on the practitionner's name, and sets necessary data for the class
        """
        name_for_url = self.name.replace(" ", "-").lower().translate(TRANSLATION_TABLE)
        url = f"https://www.doctolib.fr/online_booking/draft/new.json?id={name_for_url}"
        data = utils.fetch_json_data_from_url(url)
        if data:
            data = data.get("data", {})
            # fetch practice ids
            for place in data["places"]:
                for id in place["practice_ids"]:
                    self.practice_ids.append(id)
            
            self.speciality = data["profile"]["speciality"]["name"]

            # fetch visit motives ids and their names. Only take the highest matching motives. If no visiting_motive_keywords was
            # given, we'll be storing all of them.
            motive_ids = []
            motive_names = []
            num_keyword_match = []
            for visit_motive in data["visit_motives"]:
                if len([match for match in self.visiting_motive_forbidden_keywords if match.lower() in visit_motive["name"].lower()]) == 0:
                    motive_ids.append(visit_motive["id"])
                    motive_names.append(visit_motive["name"])
                    num_keyword_match.append(len([match for match in self.visiting_motive_keywords if match.lower() in visit_motive["name"].lower()]))
            if not num_keyword_match:
                return False
            max_match = max(num_keyword_match)
            for i in range(len(motive_ids)):
                if num_keyword_match[i] == max_match:
                    self.visit_motives[motive_ids[i]] = motive_names[i]
                
            # fetch agenda ids
            for agenda in data["agendas"]:
                if not agenda["booking_disabled"] and not agenda["booking_temporary_disabled"]:
                    self.agenda_ids.append(agenda["id"])
            return True

    def get_next_available_appointments(self):
        """ """
        start_day = "2000-01-01"  # we take a very old day to make sure no appointment will be available, so we can simply fetch the "next_slot" value
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