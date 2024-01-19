import requests

from visa_checker.config import NTFY_TOPIC


def send_notification(title: str, msg: str):
    requests.post(
        f"https://ntfy.sh/{NTFY_TOPIC}",
        data=msg,
        headers={
            "Title": title,
        },
    )
