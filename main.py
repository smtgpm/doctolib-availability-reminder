"""
For now works only for single page
"""
from sample.DoctolibUrlCom import DoctolibUrlCom
from sample.AvailabilityReminder import AvailabilityReminder


def main(argc=None, argv=None):
    duc = DoctolibUrlCom()
    ar = AvailabilityReminder()
    ar.run()

if __name__ == "__main__":
    main()
