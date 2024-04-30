import argparse
import datetime
import logging
import random
from time import sleep

from apscheduler.schedulers.background import BackgroundScheduler
from playwright.sync_api import sync_playwright

from visa_checker.db import create_tables
from visa_checker.utils import AvailabilityCheckError, check_availability_for_city
from visa_checker.config import CITIES, City
from visa_checker.page import VisaPageWrapper

work_queue: list[City] = []


def start_session(headed: bool):
    """
    Starts a browser session which logs in and starts processing jobs from the
    work_queue. Each job means querying a city for its available dates and performing
    any necessary follow ups like storing the dates, sending out notifications, and/or
    rescheduling.

    The session will last until the authentication token expires at which point this
    function will exit. Continuous processing that persists across multiple auth sessions
    can be performed by running this function in a loop.
    """
    global work_queue

    logging.info("Starting a new tracking browser session")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=not headed)

        page_wrapper = VisaPageWrapper(browser.new_page())
        page_wrapper.sign_in()

        while page_wrapper.logged_in:
            page_wrapper.wait_out_ban()

            if work_queue:
                city = work_queue.pop(0)
                logging.info(f"Checking dates for {city.name}")

                try:
                    check_availability_for_city(page_wrapper, city)
                except AvailabilityCheckError as e:
                    work_queue.append(city)
                    continue

            # Just a small delay to prevent the loop from being run too
            # frequently when the work_queue is empty
            sleep(random.uniform(5, 10))


def add_jobs():
    global work_queue

    logging.info("Adding cities to job queue...")

    for city in CITIES.values():
        if city.skip:
            continue

        logging.info(f"Adding job for {city.name}")
        work_queue.append(city)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--log", default='log.txt')
    parser.add_argument("--headed", default=False)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    create_tables()

    logging.basicConfig(
        format="%(asctime)s %(levelname)-1s: %(message)s",
        level=logging.INFO,
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.FileHandler(args.log), logging.StreamHandler()],
    )

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        add_jobs,
        "interval",
        seconds=60 * 60,
        next_run_time=datetime.datetime.now(),
    )
    scheduler.start()

    while True:
        start_session(args.headed)
