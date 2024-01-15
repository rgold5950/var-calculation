import datetime
from tkinter import END
from src.port import Portfolio, VarCalMethod
import logging
from config import PORT, START_DATE, END_DATE

logger = logging.getLogger(__name__)
logger.setLevel(level="INFO")


def portfolio_calculations_single(
    start_date: datetime.datetime, end_date: datetime.datetime
):
    p = Portfolio("Equal Weight", PORT, start_date, end_date, use_sql=False)
    # calculating var
    logger.info("Calculating Portfolio Var for 99% Confidence Interval")
    hvar = p.calc_portfolio_var(cint=99, method=VarCalMethod.HISTORICAL)
    mcvar = p.calc_portfolio_var(cint=99, method=VarCalMethod.MONTE_CARLO)
    logger.info(f"Historical Var is {hvar}| Monte Carlo Var is {mcvar}")

    logger.info("Recalculating Portfolio Var for 95% Confidence Interval")
    hvar = p.calc_portfolio_var(cint=95, method=VarCalMethod.HISTORICAL)
    mcvar = p.calc_portfolio_var(cint=95, method=VarCalMethod.MONTE_CARLO)
    logger.info(f"Historical Var is {hvar}| Monte Carlo Var is {mcvar}")

    logger.info("Plotting portfolio returns and var")
    # p.plot_var()

    # calculating dv01
    p.calc_portfolio_dv01()

    # p.plot_dv01()


def portfolio_calculations_multiple(
    start_date: datetime.datetime, end_date: datetime.datetime
):
    for weightings in [
        ("Equal Weight", [0.25, 0.25, 0.25, 0.25]),
        ("Overweight IG", [0.5, 0.25, 0.15, 0.10]),
        ("Overweight HY", [0.1, 0.15, 0.25, 0.5]),
        ("Overweight BBB, BB", [0.1, 0.4, 0.4, 0.1]),
    ]:
        for idx, bond in enumerate(PORT):
            bond.weight = weightings[1][idx]
        p = Portfolio(weightings[0], PORT, start_date, end_date, use_sql=False)
        # calculating var
        logger.info("Calculating Portfolio Var for 99% Confidence Interval")
        hvar = p.calc_portfolio_var(cint=99, method=VarCalMethod.HISTORICAL)
        mcvar = p.calc_portfolio_var(cint=99, method=VarCalMethod.MONTE_CARLO)
        logger.info(f"Historical Var is {hvar}| Monte Carlo Var is {mcvar}")

        logger.info("Recalculating Portfolio Var for 95% Confidence Interval")
        hvar = p.calc_portfolio_var(cint=95, method=VarCalMethod.HISTORICAL)
        mcvar = p.calc_portfolio_var(cint=95, method=VarCalMethod.MONTE_CARLO)
        logger.info(f"Historical Var is {hvar}| Monte Carlo Var is {mcvar}")

        logger.info("Plotting portfolio returns and var")
        p.plot_var()

        # calculating dv01
        p.calc_portfolio_dv01()

        p.plot_dv01()


if __name__ == "__main__":
    portfolio_calculations_single(START_DATE, END_DATE)
    # portfolio_calculations_multiple(START_DATE, END_DATE)
