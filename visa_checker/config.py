from dataclasses import dataclass
import os

NTFY_TOPIC = os.environ["VISA_CHECKER_NTFY_TOPIC"]


@dataclass
class City:
    name: str
    id: str  # ID used by us-visainfo.com
    skip: bool


CITIES = {
    id: City(name=name, id=id, skip=skip)
    for name, id, skip in [
        ("Calgary", "89", False),
        ("Halifax", "90", False),
        ("Montreal", "91", False),
        ("Ottawa", "92", False),
        ("Quebec City", "93", False),
        ("Toronto", "94", False),
        ("Vancouver", "95", False),
    ]
}

VISA_APP_USER_EMAIL = os.environ["VISA_CHECKER_APP_USER_EMAIL"]
VISA_APP_USER_PW = os.environ["VISA_CHECKER_APP_USER_PW"]
DB_NAME = os.environ["VISA_CHECKER_DB_NAME"]
DB_HOST = os.environ["VISA_CHECKER_DB_HOST"]
DB_USER = os.environ["VISA_CHECKER_DB_USER"]
DB_PW = os.environ["VISA_CHECKER_DB_PW"]
