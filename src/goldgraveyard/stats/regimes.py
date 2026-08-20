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


def by_regime(returns: pd.Series) -> pd.DataFrame:
    """Per-regime Sharpe, mean, t-stat, n. One row per regime."""
    raise NotImplementedError


def sign_stability(returns: pd.Series, min_positive_regimes: int = 2) -> bool:
    """True if the mean return sign holds in at least min_positive_regimes regimes."""
    raise NotImplementedError
