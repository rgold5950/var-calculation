# Fixed Income Portfolio Analytics Library

This library contains logic to calculate VaR (Value at Risk) and DV01 for a portfolio of fixed income instruments. The library queries the FRED API for data and stores it into an MS SQL Server instance.

## Getting your environment set up

1. **Install MS SQL Server Express:** If you already have access to an instance, you can skip steps 1, 2, and 3 and proceed to step 4. Otherwise, follow step 2 if you are on a Windows machine, and step 3 if you are on a Linux/MacOS machine.

   - For Windows users, the setup is simple. Simply install MS SQL Server Express by following the instructions on Microsoft’s [website](https://www.microsoft.com/en-us/sql-server/sql-server-downloads).
   - For MacOS users, you will need to download a Linux distribution and run it in a containerized environment such as Docker since SQL Server is not available for MacOS. Follow [these instructions](https://docs.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-ver15).

     - Note: Ensure that pyodbc detects your newly installed SQL Server Driver. You may need to point it to the path of your driver when constructing your connection string (the path is usually something like `/usr/local/lib/libmsodbcsql.18.dylib`).

2. **Get FRED API Key:** If you already have a FRED API key, you can skip this step. Otherwise, you can get one for free by creating an account on their [website](https://fred.stlouisfed.org/docs/api/fred/) and following the instructions to create your key. The process should take no more than 5 minutes as key generation is fairly instantaneous.

3. **Define environment variables:** There are three important environment variables you need to define. Preferably, define them in a separate .env file which will be read at runtime.

   - `FRED_API_KEY`: Your FRED API key (keep this safe!)
   - `SQL_SERVER_DRIVER`: The path to the driver of your SQL Server
   - `SQL_SERVER_INSTANCE`: The address of the SQL Server instance (localhost if running locally)

4. Run `db_setup.py` This will create the database and schema and seed it with the data for the portfolio of instruments defined in the config.py
5. Run `main.py` This is the entry script for the calculations.
   - Note: To run without the database connection or for debugging purposes, you can change `use_sql` to False when creating the portfolio instance to query the FRED API directly. Note that this might have performance impacts and should not be used in production without logic to limit the number of calls to the calculations tool or cache the results. 

## Customizing portfolio holdings, lookback period, weightings

- All customizations can be specified in `db.config.py`
- To change assets in the portfolio, define your assets via the `BondIndex` class. The `BondIndex` class is a dataclass consisting of price, yield, and weight. Note that you'll either need to have an instrument that is in your database or available via the FRED API.

- To change the lookback period, adjust the `START_DATE` and `END_DATE`.

- To change the weighting, adjust the `weight` parameter in your `BondIndex`, OR, if you are running multiple portfolios, define a list of weightings and add it to the existing weightings in the function `portfolio_calculations_multiple`.

Enjoy!

P.S. [Here](analysis.pdf) is a brief analysis of the calculations for a simple corporate debt portfolio:
