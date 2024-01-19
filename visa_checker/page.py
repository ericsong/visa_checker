import calendar
import logging
import datetime
import random
import time
import re
from typing import Optional

from date_utils import parse_month_year_str
from config import CITIES, VISA_APP_USER_EMAIL, VISA_APP_USER_PW, City

VISA_URL = "https://ais.usvisa-info.com/en-ca/niv/users/sign_in"
JSON_URL_REGEX = re.compile(r"appointment\/days\/(\d+)\.json")


class ServiceUnavailableError(Exception):
    pass


class NoResponseError(Exception):
    pass


class UnauthorizedError(Exception):
    pass


class TempBannedError(Exception):
    pass


class VisaPageWrapper:
    def __init__(self, page):
        self.page = page
        self.logged_in = False
        self.last_temp_banned_time = None

    def sign_in(self):
        logging.info("Signing in")
        self.page.goto(VISA_URL, timeout=60 * 1000)
        self.page.type("#user_email", VISA_APP_USER_EMAIL, delay=200)
        self.page.type("#user_password", VISA_APP_USER_PW, delay=200)
        self._random_delay()
        self.page.locator("#policy_confirmed").click(force=True)
        self._random_delay()
        self.page.click('input:text-is("Sign In")')
        self.logged_in = True
        logging.info("Sign in complete")

        logging.info("Navigating to scheduler page")
        self._random_delay()
        self.page.click('a:text-is("Continue")')
        self._random_delay()
        self.page.click('h5:text-is("Reschedule Appointment")')
        self._random_delay()
        self.page.click('a:text-is("Reschedule Appointment")')
        logging.info("Finished navigating to scheduler page")

    def wait_out_ban(self):
        """
        Sometimes our account can get temporarily banned for sending too many
        requests. As long as the number of requests wasn't too dramatic, the
        ban seems to be lifted after 1-3 hours.

        This function will regularly check our ban status and only exit if we're
        good to send more requests.

        Note, this function only runs if we know we've been banned before so it's
        possible that we're banned but we're not aware of it yet even if this
        successfully called. That is OK and part of the normal workflow. Once we
        discover that we're banned, the main worker loop will eventually circle
        back to this function call and start the waiting/checking loop.
        """

        while self.logged_in and self.last_temp_banned_time:
            if (
                datetime.datetime.now() - self.last_temp_banned_time
            ) > datetime.timedelta(hours=1):
                # More than an hour has passed. Check if we're still banned.
                logging.info(
                    "1 hour has passed since the last verified TEMP_BAN. Sending "
                    "a request to check."
                )

                try:
                    # Check any city to see if we get a valid request
                    self.get_available_dates_for_city(CITIES["92"])
                    logging.info(
                        "Received valid request. No longer TEMP_BAN. Setting "
                        "LAST_TEMP_BANNED_TIME to None."
                    )
                    self.last_temp_banned_time = None
                except UnauthorizedError:
                    logging.info("Received Unauthorized. Setting LOGGED_IN to False")
                    self.logged_in = False
                except ServiceUnavailableError:
                    logging.info("Waiting 30 minutes because service is unavailable.")
                    time.sleep(30 * 60)
            else:
                # Less than an hour has passed since the last known TEMP_BAN.
                # Sleep for a bit before trying again.
                logging.info(
                    "Less than 1 hour has passed since LAST_TEMP_BANNED_TIME "
                    f"{self.last_temp_banned_time}. Sleeping for 30 minutes."
                )
                time.sleep(30 * 60)

    def reschedule_appointment(self, month: int, day: int, year: int):
        logging.info(f"Rescheduling appointment to {month}/{day}/{year}")
        self._select_appointment(month=month, day=day, year=year)

        logging.info("Clicking Reschedule")
        self.page.click('input:text-is("Reschedule")')

        logging.info("Clicking Confirm")
        self.page.click('a:text-is("Confirm")')

        logging.info("Reschedule complete")

    def get_available_dates_for_city(self, city: City) -> Optional[set[str]]:
        """
        :return None - NotModified
                set[str] - Set of available dates for the city in the format of `%Y-%m-%d` eg. `2022-3-29`

        :raises UnauthorizedError - if the session is no longer authorized
        :raises NoResponseError - no matching JSON response found
        :raises ServiceUnavailableError - if 503 is returned
        :raises TempBannedError - Temp Banned
        """
        city_response = None

        def listen_response(response):
            match = JSON_URL_REGEX.search(response.url)

            if match is None:
                logging.info(f"No match for response url {response.url}")
                return

            response_city_id = match.group(1)
            assert response_city_id.isnumeric()
            response_city = CITIES[response_city_id]
            logging.info(
                f"Found dates JSON response for url {response.url}. Matching city_id"
                f" {response_city_id}. Matching city {response_city.name}."
            )

            if response_city is not city:
                logging.warning(
                    f"Requested {city.name} but found response for {response_city.name}"
                )
                return

            logging.info(f"Found response for {city.name}")
            nonlocal city_response
            city_response = response

        self.page.on("response", listen_response)

        # Select option to trigger
        self.page.select_option(
            "#appointments_consulate_appointment_facility_id", city.id
        )

        # wait for the response
        start_listen_time = datetime.datetime.now()
        while city_response is None:
            if datetime.datetime.now() - start_listen_time > datetime.timedelta(
                minutes=2
            ):
                logging.warning(
                    "No matching response in 2 minutes. Something probably went wrong. "
                    "Exiting response handler."
                )
                raise NoResponseError()

            self.page.evaluate(
                "async() => {await new Promise(r => setTimeout(r, 1000));}"
            )
            time.sleep(1)

        self.page.remove_listener("response", listen_response)

        # Handle response
        logging.info(f"Handling response for {city.name}")
        response = city_response
        if response.status == 401:
            # Unauthorized - Auth expired
            logging.info(
                f"{city.name} response - Received 401. Adding job back to work_queue "
                "and setting IS_LOGGED_IN to False to trigger new session."
            )
            raise UnauthorizedError()
        elif response.status == 503:
            logging.info("Received 503. Service temporarily unavailable.")
            raise ServiceUnavailableError()
        elif response.status >= 400:
            logging.info("Ran into network request error. Exiting.")
            logging.info(response)
            logging.info(response.status)
            logging.info(response.url)
            logging.info(response.text())
            exit(1)

        if response.status == 304:
            # Not modified
            logging.info(f"304 Not Modified for {city.name}")
            return None

        current_dates = {d["date"] for d in response.json()}

        if not current_dates and city.name in ["Calgary", "Vancouver", "Ottawa"]:
            # Most likely temp banned if we're getting empty results for any of these
            # cities since I know they likely have at least some availability.
            logging.info(
                f"Received empty result for {city.name}. Most likely temp banned. "
                "Setting TEMP_BANNED=True."
            )
            raise TempBannedError()

        return current_dates

    def _random_delay(self):
        time.sleep(random.uniform(0.5, 2))

    def _get_current_datepicker_months(self) -> tuple[int, int]:
        return [
            parse_month_year_str(s.replace("\xa0", " "))
            for s in self.page.locator(".ui-datepicker-title").all_text_contents()
        ]

    def _go_prev_month_datepicker(self):
        self.page.click('span:text-is("Prev")')

    def _go_next_month_datepicker(self):
        self.page.click('span:text-is("Next")')

    def _go_to_month_datepicker(self, target_month: int, target_year: int):
        target_month_year = (target_month, target_year)

        i = 0
        current_datepicker_months = self._get_current_datepicker_months()

        while target_month_year not in current_datepicker_months:
            left_side_month, left_side_year = current_datepicker_months[0]
            right_side_month, right_side_year = current_datepicker_months[1]

            if target_year < left_side_year or (
                target_year == left_side_year and target_month < left_side_month
            ):
                self._go_prev_month_datepicker()
            elif target_year > right_side_year or (
                target_year == right_side_year and target_month > right_side_month
            ):
                self._go_next_month_datepicker()
            else:
                raise RuntimeError(
                    f"Impossible condition met. Target Month/Year ({target_month_year})"
                    " not found and could not determine if it is before or after "
                    f"current dates {current_datepicker_months}."
                )

            i += 1

            if i == 50:
                raise RuntimeError(
                    f"Could not find target month/year ({target_month_year}) after 50"
                    " iterations."
                )

            current_datepicker_months = self._get_current_datepicker_months()

    def _select_day_datepicker(self, month: int, day: int):
        # Assumes datepicker is already open to correct month
        month_name = calendar.month_name[month]
        datepicker_month = self.page.locator(
            ".ui-datepicker-group",
            has=self.page.locator(f'span:text-is("{month_name}")'),
        )
        date_cell = datepicker_month.locator(f'td a:text-is("{day}")')

        if date_cell.count() == 0:
            logging.error(f"Selected day {month}/{day} is not available.")
            return False

        date_cell.click()
        return True

    def _get_time_option_values(self):
        while (
            self.page.locator("#appointments_consulate_appointment_time option").count()
            < 2
        ):
            count = self.page.locator(
                "#appointments_consulate_appointment_time option"
            ).count()
            logging.info(f"Option count is {count}")
            time.sleep(1)

        return [
            value
            for value in [
                option.evaluate("e => e.value")
                for option in self.page.query_selector_all(
                    "#appointments_consulate_appointment_time option"
                )
            ]
            if value
        ]

    def _open_datepicker(self):
        self.page.click("#appointments_consulate_appointment_date_input")

    def _select_appointment(self, month: int, day: int, year: int):
        logging.info(f"Selecting appointment date {month}/{day}/{year}")
        self._open_datepicker()
        self._go_to_month_datepicker(month, year)

        if self._select_day_datepicker(month, day):
            times = self._get_time_option_values()
            logging.info(f"Selecting appointment time {times[-1]}")
            self.page.select_option(
                "#appointments_consulate_appointment_time", times[-1]
            )
