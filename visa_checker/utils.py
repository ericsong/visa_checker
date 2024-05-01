import datetime
import logging
import time

from config import CITIES, City
from repo import (
    get_current_appointment_date,
    get_last_known_dates,
    record_new_dates,
    update_appointment_date,
)
from notify import send_notification
from date_utils import get_weekday, date_str_to_datetime, is_preferred_date
from page import (
    VisaPageWrapper,
    UnauthorizedError,
    TempBannedError,
    ServiceUnavailableError,
    NoResponseError,
)


class AvailabilityCheckError(Exception):
    pass


def process_availability_for_city(city_id: str, current_dates: set[str]):
    """
    Process current availability for a city by sending out notifications
    if new dates are detected and storing availability in the db.
    """

    city = CITIES[city_id]
    logging.info(f"Updating {city.name} with new dates.")

    new_dates = current_dates - get_last_known_dates(city)

    if new_dates:
        title = f"New Visa Appointment Dates ({city.name})"
        formatted_dates = [f"{d} ({get_weekday(d)})" for d in sorted(list(new_dates))]
        msg = "\n".join(formatted_dates)

        send_notification(title=title, msg=msg)
        send_notification(title=title, msg='test message')
        logging.info(f"Sent notification - {title} - {msg}")
        logging.info(title)
        logging.info(msg)
    else:
        logging.info(f"No new dates for {city.name}")

    record_new_dates(city, current_dates)


def check_availability_for_city(page_wrapper: VisaPageWrapper, city: City):
    """
    Fetch the current availability for a given city and execute any necessary
    follow ups with the new dates.
    """

    try:
        current_dates = page_wrapper.get_available_dates_for_city(city)
        print(f'{city} dates - {current_dates}')
    except (
        UnauthorizedError,
        TempBannedError,
        ServiceUnavailableError,
        NoResponseError,
    ) as e:
        if isinstance(e, UnauthorizedError):
            page_wrapper.logged_in = False
            logging.info("Received Unauthorized. Setting LOGGED_IN to False")
        elif isinstance(e, TempBannedError):
            page_wrapper.last_temp_banned_time = datetime.datetime.now()
            logging.info(
                f"Temp Banned. Setting TEMP_BAN to {page_wrapper.last_temp_banned_time}."
            )
        elif isinstance(e, ServiceUnavailableError):
            logging.info("Waiting 30 minutes because service is unavailable.")
            time.sleep(30 * 60)
        elif isinstance(e, NoResponseError):
            logging.info("No matching JSON response found. Adding job back to queue.")

        raise AvailabilityCheckError()

    if current_dates is None:
        logging.info(f"304 - No new dates for {city.name}")
        return

    process_availability_for_city(city.id, current_dates)

    # Check if any of the current_dates are preferred over our current
    # appointment slot. If so, reschedule to one of those dates.
    preferred_dates = sorted(
        [
            date
            for date in current_dates
            if is_preferred_date(
                date_str_to_datetime(date), get_current_appointment_date()
            )
        ]
    )

    if preferred_dates:
        logging.info(f"Found preferred dates - {', '.join(preferred_dates)}")

        new_date = date_str_to_datetime(preferred_dates[0])

        msg = f"Rescheduling to {new_date}"
        logging.info(msg)
        send_notification(
            title=f"Found preferrable appointment date - {city.name}", msg=msg
        )

        logging.info(f"Running rescheduler for preferred date - {new_date}")
        page_wrapper.reschedule_appointment(
            year=new_date.year,
            month=new_date.month,
            day=new_date.day,
        )
        update_appointment_date(
            datetime.datetime(
                month=new_date.month, day=new_date.day, year=new_date.year
            )
        )
