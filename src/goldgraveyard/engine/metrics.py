"""Performance summary statistics.

Sharpe here is EXCESS of nothing -- these are futures, already funded, so the
raw return is an excess return. Do not subtract a cash rate twice.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252


@dataclass(frozen=True)
class PerfSummary:
    ann_return: float
    ann_vol: float
    sharpe: float
    max_drawdown: float
    hit_rate: float
    n_obs: int


def summarize(returns: pd.Series) -> PerfSummary:
    raise NotImplementedError


def sharpe(returns: pd.Series, periods_per_year: int = TRADING_DAYS) -> float:
    """Annualized return per unit of volatility.

    No risk-free rate is subtracted. These are futures positions, which are
    already financed, so the return series is an excess return by construction.
    Subtracting a cash rate would double-count.
    """
    r = returns.dropna()
    if len(r) < 2:
        return float("nan")
    sd = r.std()
    if sd == 0:
        return float("nan")
    return float(r.mean() / sd * np.sqrt(periods_per_year))


def max_drawdown(returns: pd.Series) -> float:
    raise NotImplementedError
