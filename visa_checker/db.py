import psycopg2
from psycopg2.extensions import connection

from visa_checker.config import DB_HOST, DB_NAME, DB_PW, DB_USER


def create_db_connection() -> connection:
    return psycopg2.connect(dbname=DB_NAME, host=DB_HOST, user=DB_USER, password=DB_PW)


def create_available_dates_table():
    with create_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS available_dates (
               id SERIAL PRIMARY KEY,
               city_id VARCHAR(6) NOT NULL,
               city_name VARCHAR(100) NOT NULL,
               dates TEXT NOT NULL,
               created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
            )


def create_misc_table():
    with create_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
            CREATE TABLE IF NOT EXISTS misc (
                key VARCHAR(100) UNIQUE,
                value TEXT NOT NULL
            );
            """
            )


def create_tables():
    """
    Create necessary DB tables for visa_checker.  No-ops if the tables already exist.
    Opted for manual db create/querying instead of using an ORM + db migration manager
    for simplicity. This is more or less a one time use script.
    """
    create_available_dates_table()
    create_misc_table()
