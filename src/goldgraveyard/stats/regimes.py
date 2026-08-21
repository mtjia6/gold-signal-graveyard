"""Subperiod stability.

Regimes are frozen in DECISIONS.md and chosen on GOLD MARKET history, not on
where any strategy happens to make money. Choosing breakpoints after seeing
results is just a slower kind of overfitting.
"""

from __future__ import annotations

import pandas as pd

REGIMES: dict[str, tuple[str, str]] = {
    "bull_run":     ("2006-01-01", "2011-09-05"),
    "bear_2013":    ("2011-09-06", "2015-12-31"),
    "range_recov":  ("2016-01-01", "2019-12-31"),
    "covid_spike":  ("2020-01-01", "2020-12-31"),
    "modern":       ("2021-01-01", "2026-06-30"),
}


TRADING_DAYS = 252
MIN_OBS = 60  # below this, a regime's mean is not worth reading as evidence


def by_regime(returns: pd.Series) -> pd.DataFrame:
    """One row per frozen regime: n, mean return, annualized mean, Sharpe, sign.

    `n` is reported deliberately and is not decoration. The COVID window is a
    single calendar year, so it carries roughly a fifth of the observations of
    the bull run. Reading a thin regime's mean as though it were as informative
    as a thick one is the obvious way to misuse this table, and the only defence
    is having the count in front of you. `thin` flags anything under MIN_OBS.

    Regimes come from the frozen REGIMES constant, which mirrors DECISIONS.md
    section 4. They are never inferred from the data: choosing breakpoints after
    seeing where a strategy performed well is a slower form of overfitting, and
    the whole point of this test is to be unable to do that.

    Pass the same dropna'd net return series given to the Deflated Sharpe, so
    every condition of the verdict rule is judged on identical numbers.
    """
    r = returns.dropna()
    rows = []
    for name, (start, end) in REGIMES.items():
        window = r.loc[pd.Timestamp(start) : pd.Timestamp(end)]
        n = len(window)
        mean = float(window.mean()) if n else float("nan")
        sd = float(window.std()) if n > 1 else float("nan")
        rows.append(
            {
                "regime": name,
                "start": start,
                "end": end,
                "n": n,
                "mean": mean,
                "ann_mean": mean * TRADING_DAYS if n else float("nan"),
                "sharpe": (
                    mean / sd * (TRADING_DAYS**0.5) if n > 1 and sd not in (0.0,) else float("nan")
                ),
                "positive": bool(mean > 0) if n else False,
                "thin": n < MIN_OBS,
            }
        )
    return pd.DataFrame(rows).set_index("regime")


def count_positive_regimes(returns: pd.Series) -> int:
    """How many frozen regimes have a positive mean return.

    This integer is what condition 3 of the verdict rule tests, and it is what
    the graveyard table's "Regimes OK" column reports.
    """
    return int(by_regime(returns)["positive"].sum())


def sign_stability(returns: pd.Series, min_positive_regimes: int = 2) -> bool:
    """True if the mean return sign holds in at least min_positive_regimes regimes.

    Condition 3 of the frozen verdict rule. A strategy that works in exactly one
    regime is describing that stretch of history rather than a durable
    relationship, and a threshold of 2 out of 5 is a deliberately weak filter:
    it is there to catch the single-regime case, not to certify robustness.
    """
    return count_positive_regimes(returns) >= min_positive_regimes
