import datetime
import calendar


def is_between_dates(
    start: datetime.datetime, end: datetime.datetime, query: datetime.datetime
) -> bool:
    return query >= start and query <= end


def date_str_to_datetime(s: str) -> datetime.datetime:
    return datetime.datetime.strptime(s, "%Y-%m-%d")


_MONTH_TO_INT = {
    month: index for index, month in enumerate(calendar.month_name) if month
}


def parse_month_year_str(s: str) -> tuple[int, int]:
    """
    Input:
      s: str - month_year string like '3 2022'

    Return:
      tuple[int, int] - tuple with month and year as integers. eg. (3, 2022)
    """
    month_s, year_s = s.split()

    return _MONTH_TO_INT[month_s], int(year_s)


def get_weekday(s):
    return calendar.day_name[datetime.datetime.strptime(s, "%Y-%m-%d").weekday()]


def is_preferred_date(
    proposed_date: datetime.datetime, current_date: datetime.datetime
):
    """
    Return True if the given `date` is a preferred date over the `current_date`.

    This implementation of this function will differ depending on the needs of the
    user requesting a visa appointment. A more advanced version of this would expose
    a configuration format to define different rules for what would qualify as a
    preferred date eg. (anything sooner than X, anything between Y and Z, etc)
    but since I made this script just for myself, it was by far simpler to just
    define the logic I wanted as code.
    """

    if is_between_dates(
        start=datetime.datetime(year=2024, month=6, day=11),
        end=datetime.datetime(year=2023, month=7, day=5),
        query=proposed_date,
    ):
        return True

    return False
