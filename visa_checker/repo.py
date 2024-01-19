import datetime
import logging
from typing import Set

from db import create_db_connection
from date_utils import date_str_to_datetime
from config import City


def update_appointment_date(date: datetime.datetime):
    """
    Commit the current appointment date to the db
    """

    logging.info(f"Updating database current_appointment_date to {date}")

    with create_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "update misc set value=%s where key='current_appointment_date'",
                (date.strftime("%Y-%m-%d"),),
            )


def get_current_appointment_date() -> datetime.datetime:
    """
    Retrieve the current appointment date from the db
    """

    with create_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select value from misc where key='current_appointment_date'",
            )

            result = cur.fetchone()

            return date_str_to_datetime(result[0])


def record_new_dates(city: City, dates: Set[str]):
    """
    Store the given `dates` for the given `city` into the db.
    """

    with create_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO available_dates (city_id, city_name, dates) VALUES (%s,"
                " %s, %s)",
                (city.id, city.name, ",".join(dates)),
            )


def get_last_known_dates(city: City) -> Set[str]:
    """
    Fetch the last known available dates for the given `city`
    """
    with create_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "select dates from available_dates where city_id=%s ORDER BY created_at"
                " desc LIMIT 1",
                (city.id,),
            )

            result = cur.fetchone()

            if result is None:
                return set()

            return set(result[0].split(","))
