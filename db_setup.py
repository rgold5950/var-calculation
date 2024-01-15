import pyodbc
import uuid
from datetime import date
from dotenv import load_dotenv
import os
import logging
from config import PORT, START_DATE, END_DATE
from src.data import get_series
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()
IS_WINDOWS = os.name == "nt"
SQL_SERVER_DRIVER = os.environ["SQL_SERVER_DRIVER"]
SQL_SERVER_INSTANCE = os.environ["SQL_SERVER_INSTANCE"]
SQL_DB_USER = os.environ["SQL_DB_USER"]
SQL_DB_PASSWORD = os.environ["SQL_DB_PASSWORD"]
DATABASE_NAME = "vardata"


def setup_db():
    # Establish a connection to the SQL Server master database
    # login using Windows login - may have to change this on mac
    if IS_WINDOWS:
        master_connection_string = f"DRIVER={SQL_SERVER_DRIVER};SERVER={SQL_SERVER_INSTANCE};DATABASE=master;Trusted_Connection=yes;"
    else:
        master_connection_string = f"DRIVER={SQL_SERVER_DRIVER};SERVER={SQL_SERVER_INSTANCE};DATABASE=master;UID={SQL_DB_USER};PWD={SQL_DB_PASSWORD};TrustServerCertificate=yes"
    master_conn = pyodbc.connect(master_connection_string, autocommit=True)
    master_cursor = master_conn.cursor()

    master_cursor.execute(
        f"SELECT database_id FROM sys.databases WHERE Name = '{DATABASE_NAME}'"
    )
    database_exists = master_cursor.fetchone()

    if database_exists:
        # If the database exists, drop it
        master_cursor.execute(f"USE master; DROP DATABASE {DATABASE_NAME}")

    # Create vardata database
    master_cursor.execute(f"CREATE DATABASE {DATABASE_NAME}")

    # Commit the changes and close the master connection
    master_conn.close()

    # Establish a connection to the vardata database
    if IS_WINDOWS:
        connection_string = f"DRIVER={SQL_SERVER_DRIVER};SERVER={SQL_SERVER_INSTANCE};DATABASE={DATABASE_NAME};Trusted_Connection=yes;"
    else:
        connection_string = f"DRIVER={SQL_SERVER_DRIVER};SERVER={SQL_SERVER_INSTANCE};DATABASE={DATABASE_NAME};UID={SQL_DB_USER};PWD={SQL_DB_PASSWORD};TrustServerCertificate=yes"

    conn = pyodbc.connect(connection_string)
    cursor = conn.cursor()

    logger.info("Finished creating database")

    # Create securities table
    cursor.execute(
        """
        CREATE TABLE securities (
            id UNIQUEIDENTIFIER PRIMARY KEY,
            price_index NVARCHAR(255),
            yield_index NVARCHAR(255),
        )
    """
    )

    # Create historical_data table with a foreign key reference to securities
    cursor.execute(
        """
        CREATE TABLE historical_data (
            id UNIQUEIDENTIFIER PRIMARY KEY,
            date DATE,
            ticker_id UNIQUEIDENTIFIER FOREIGN KEY REFERENCES securities (id),
            yield FLOAT NULL,
            price FLOAT NULL,
        )
    """
    )

    securities = []
    historical_data_df = pd.DataFrame()
    for bond in PORT:
        ticker_id = uuid.uuid4()
        price_index_name, yield_index_name = bond.price_index, bond.yield_index
        securities.append([ticker_id, price_index_name, yield_index_name])
        price_data = get_series(price_index_name, START_DATE, END_DATE)
        yield_data = get_series(yield_index_name, START_DATE, END_DATE)
        pdf = pd.DataFrame({"date": price_data.index, "price": price_data.values})
        ydf = pd.DataFrame({"date": yield_data.index, "yield": yield_data.values})
        df = pd.DataFrame()
        df = pd.merge(ydf, pdf, on="date", how="left")
        df["id"] = [uuid.uuid4() for _ in range(len(df))]
        df["ticker_id"] = ticker_id
        historical_data_df = pd.concat([historical_data_df, df], axis=0)

    col_order = ["id", "date", "ticker_id", "yield", "price"]
    historical_data_df["yield"] = pd.to_numeric(
        historical_data_df["yield"], errors="coerce"
    )
    historical_data_df["price"] = pd.to_numeric(
        historical_data_df["price"], errors="coerce"
    )
    historical_data_df = historical_data_df.astype(object).where(
        pd.notnull(historical_data_df), None
    )
    historical_data = historical_data_df[col_order].values.tolist()

    logger.info("Adding historical data to db")
    logger.info(historical_data_df.head())
    logger.info(historical_data_df.info())

    cursor.executemany("INSERT INTO securities VALUES (?, ?, ?)", securities)
    cursor.executemany(
        "INSERT INTO historical_data VALUES (?, ?, ?, ?, ?)", historical_data
    )

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    logger.info("Finished setting up and seeding the database")
    return


if __name__ == "__main__":
    logger.setLevel(level="INFO")
    setup_db()
