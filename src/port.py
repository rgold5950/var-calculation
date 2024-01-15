from dataclasses import dataclass
import typing as T
from src.data import query_series_from_sql, get_series
import datetime
import logging
import pandas as pd
from enum import Enum
import numpy as np
import scipy.stats as stats
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)
logger.setLevel(level="INFO")


class VarCalMethod(Enum):
    HISTORICAL = "HISTORICAL"
    MONTE_CARLO = "MONTE_CARLO"


@dataclass
class BondIndex:
    name: str
    yield_index: str
    price_index: str
    weight: float
    yield_data: T.Any = None
    price_data: T.Any = None


Port = T.List[BondIndex]


class Portfolio:
    def __init__(
        self,
        portfolio_name: str,
        portfolio: Port,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
        hydrate=True,
        use_sql=True,
    ):
        self.portfolio_name = portfolio_name
        self.portfolio = portfolio
        self._combined_df = None
        self.start_date = start_date
        self.end_date = end_date
        self.use_sql = use_sql
        self._hydrate()

    def _hydrate(self):
        self.fetch_price_data(start_date=self.start_date, end_date=self.end_date)
        self.fetch_yield_data(start_date=self.start_date, end_date=self.end_date)

    def fetch_yield_data(
        self, start_date: datetime.datetime, end_date: datetime.datetime
    ):
        for bond_index in self.portfolio:
            if bond_index.yield_data is None:
                try:
                    if self.use_sql:
                        data = query_series_from_sql(
                            "yield", bond_index.yield_index, start_date, end_date
                        )
                        bond_index.yield_data = data
                    else:
                        data = get_series(bond_index.yield_index, start_date, end_date)
                        bond_index.yield_data = pd.DataFrame(
                            {"date": data.index, "yield": data.values}
                        )

                    logger.info(
                        f"Successfully hydrated yield data for BondIndex {bond_index.yield_index}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to hydrate yield data for bond index {bond_index.yield_index} with exception {e}"
                    )

    def fetch_price_data(
        self, start_date: datetime.datetime, end_date: datetime.datetime
    ):
        for bond_index in self.portfolio:
            if bond_index.price_data is None:
                try:
                    if self.use_sql:
                        data = query_series_from_sql(
                            "price", bond_index.price_index, start_date, end_date
                        )
                        bond_index.price_data = data
                    else:
                        data = get_series(bond_index.price_index, start_date, end_date)
                        bond_index.price_data = pd.DataFrame(
                            {"date": data.index, "price": data.values}
                        )
                    logger.info(
                        f"Successfully hydrated price data for BondIndex {bond_index.price_index}"
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to hydrate price data for bond index {bond_index.price_index} with exception {e}"
                    )

    @property
    def combined_df(self) -> pd.DataFrame:
        if self._combined_df is None:
            comb = {}
            for bond_index in self.portfolio:
                ydf = bond_index.yield_data
                pdf = bond_index.price_data
                cdf = pd.merge(ydf, pdf, on="date", how="left")
                cdf["delta_yield"] = cdf["yield"].diff(periods=1)
                cdf["px_chg"] = cdf["price"].diff(periods=1)
                cdf["daily_return"] = cdf["price"].pct_change(fill_method=None)
                cdf["weight"] = bond_index.weight
                cdf["weighted_return"] = cdf["daily_return"] * cdf["weight"]
                cdf["weighted_px"] = cdf["price"] * cdf["weight"]
                cdf.set_index("date", inplace=True)
                comb[bond_index.name] = cdf
            self._combined_df = pd.concat(
                [data for data in comb.values()], keys=comb.keys(), axis=1
            )
            self._combined_df["total_weighted_return"] = self._combined_df.filter(
                like="weighted_return"
            ).sum(axis=1)
            self._combined_df["total_weighted_px"] = self._combined_df.filter(
                like="weighted_px"
            ).sum(axis=1)
        return self._combined_df

    def _hvar(self, cint: float):
        """Calculate Historical Var"""
        return np.percentile(
            self.combined_df["total_weighted_return"], 100 - cint, method="lower"
        )

    def _mcvar(self, cint: float) -> float:
        """Calculate Monte Carlo Var"""
        # fetch returns and last available price
        np.random.seed(1)
        tr, lst_px = (
            self.combined_df["total_weighted_return"],
            self.combined_df["total_weighted_px"].iloc[-1],
        )  # price is only necessary if we want to calculate the actual drawdown
        mean = np.mean(tr)
        std = np.std(tr)
        n_runs = 1_000_000
        sims = np.random.normal(mean, std, n_runs)
        return np.percentile(sims, 100 - cint)

    def calc_portfolio_var(
        self, cint: float, method: T.Optional[VarCalMethod] = VarCalMethod.HISTORICAL
    ) -> float:
        if not 0 <= cint <= 100:
            raise Exception("Confidence interval must be between 0 and 100")
        if method == VarCalMethod.HISTORICAL:
            return self._hvar(cint)
        elif method == VarCalMethod.MONTE_CARLO:
            return self._mcvar(cint)
        else:
            raise Exception(f"unsupported method passed to portfolio var {method}")

    def calc_portfolio_dv01(self):
        """Calculate Portfolio DV01 by linearly interpolating the change in price / change in yield for each date and add it to the combined_df object"""
        names = [bond.name for bond in self.portfolio]
        for lvl in [lvl for lvl in self._combined_df.columns.levels[0]][0:4]:
            if lvl in names:
                self._combined_df[(lvl, "dv01")] = (
                    0.01
                    * self._combined_df[(lvl, "px_chg")]
                    / self._combined_df[(lvl, "delta_yield")]
                )

    def plot_dv01(self):
        self.calc_portfolio_dv01()
        df = self._combined_df.dropna()
        dv01_columns = df.columns.get_level_values(1) == "dv01"
        df_dv01 = df.loc[:, dv01_columns]
        df_dv01 = df_dv01.droplevel(level=1, axis=1)
        df_dv01 = df_dv01.loc[
            (df_dv01 != 0).all(axis=1)
            & (df_dv01 != float("inf")).all(axis=1)
            & (df_dv01 != float("-inf")).all(axis=1)
        ]

        for parent_column in df_dv01.columns.get_level_values(0).unique():
            avg_dv01 = df_dv01[parent_column].dropna().mean()
            label = f"{parent_column} ({avg_dv01:.4f})"
            plt.plot(df_dv01[parent_column], label=label)

        plt.xlabel("Date")
        plt.ylabel("dv01")
        plt.title(f"Daily DV01 for {self.portfolio_name}")
        plt.legend(title="asset")
        plt.show()

    def plot_var(self):
        df = self._combined_df["total_weighted_return"]
        pvarh99 = round(self.calc_portfolio_var(99, method=VarCalMethod.HISTORICAL), 5)
        pvarmc99 = round(
            self.calc_portfolio_var(99, method=VarCalMethod.MONTE_CARLO), 5
        )
        pvarh95 = round(self.calc_portfolio_var(95, method=VarCalMethod.HISTORICAL), 5)
        pvarmc95 = round(
            self.calc_portfolio_var(95, method=VarCalMethod.MONTE_CARLO), 5
        )
        plt.hist(
            df, bins=10, color="grey", edgecolor="black", density=True, label="Returns"
        )
        plt.axvline(
            pvarh99,
            color="red",
            linestyle="-",
            linewidth=2,
            label=f"VaR Historical 99 ({pvarh99})",
        )
        plt.axvline(
            pvarmc99,
            color="orange",
            linestyle="-",
            linewidth=2,
            label=f"VaR Monte Carlo 99 ({pvarmc99})",
        )
        plt.axvline(
            pvarh95,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"VaR Historical 95 ({pvarh95})",
        )
        plt.axvline(
            pvarmc95,
            color="orange",
            linestyle="--",
            linewidth=2,
            label=f"VaR Monte Carlo 95 ({pvarmc95})",
        )
        plt.xlabel("% Return")
        plt.ylabel("Days")
        plt.title(f"Distribution of Returns for {self.portfolio_name}")
        mean, std = df.mean(), df.std()
        xmin, xmax = df.min(), df.max()
        x = np.linspace(xmin, xmax, 100)
        p = stats.norm.pdf(x, mean, std)
        skew = stats.skew(df)
        kurtosis = stats.kurtosis(df)
        logger.info(f"Skew is {skew}\n")
        logger.info(f"Kurtosis is {kurtosis}")
        # Annotating the plot with Skew and Kurtosis values
        plt.annotate(
            f"Skew: {round(skew, 3)}",
            xy=(0.05, 0.9),
            xycoords="axes fraction",
            fontsize=10,
        )
        plt.annotate(
            f"Kurtosis: {round(kurtosis, 3)}",
            xy=(0.05, 0.85),
            xycoords="axes fraction",
            fontsize=10,
        )
        plt.plot(x, p, "k", linewidth=2, label="Normal Distribution")
        plt.legend(loc="lowerright")
        plt.show()
