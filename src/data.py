import datetime
from fredapi import Fred
from dotenv import load_dotenv
import os
import warnings

warnings.simplefilter(action="ignore", category=UserWarning)
import pandas as pd
import pyodbc
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
IS_WINDOWS = os.name == "nt"
SQL_SERVER_DRIVER = os.environ["SQL_SERVER_DRIVER"]
SQL_SERVER_INSTANCE = os.environ["SQL_SERVER_INSTANCE"]
API_KEY = os.environ["FRED_API_KEY"]
DATABASE_NAME = "vardata"
fred = Fred(api_key=API_KEY)


def get_series_info(ticker: str):
    return fred.get_series_info(ticker)


def get_series(
    field: str, start_date: datetime.datetime, end_date: datetime.datetime
) -> pd.DataFrame:
    return fred.get_series(field, start_date, end_date)


def query_series_from_sql(
    field: str, ticker: str, start_date: datetime.datetime, end_date: datetime.datetime
):
    # Establish a connection to the vardata database
    if IS_WINDOWS:
        connection_string = f"DRIVER={SQL_SERVER_DRIVER};SERVER={SQL_SERVER_INSTANCE};DATABASE={DATABASE_NAME};Trusted_Connection=yes;"
    else:
        connection_string = f"DRIVER={SQL_SERVER_DRIVER};SERVER={SQL_SERVER_INSTANCE};DATABASE={DATABASE_NAME};UID=SA;PWD=reallyStrongPwd123;TrustServerCertificate=yes"

    conn = pyodbc.connect(connection_string)
    query = f"""
        SELECT date, {field} FROM historical_data 
        WHERE ticker_id = (SELECT id FROM securities where price_index = '{ticker}' or yield_index = '{ticker}') 
        AND DATE BETWEEN '{start_date.isoformat()}' and '{end_date.isoformat()}'
        ORDER BY date;
    """
    result_df = pd.read_sql(query, conn)

    # Close the connection
    conn.close()
    return result_df


if __name__ == "__main__":
    END_DATE = datetime.date.today()
    START_DATE = END_DATE - datetime.timedelta(days=365 * 2)
    df = query_series_from_sql("price", "BAMLCC0A1AAATRIV", START_DATE, END_DATE)
    logger.info(df.head())
    logger.info(f"Found {len(df)} results")

    df = query_series_from_sql("yield", "BAMLCC0A1AAATRIV", START_DATE, END_DATE)
    logger.info(df.head())
    logger.info(f"Found {len(df)} results")
