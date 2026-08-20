"""Performance summary statistics.

Sharpe here is EXCESS of nothing -- these are futures, already funded, so the
raw return is an excess return. Do not subtract a cash rate twice.
"""

from __future__ import annotations

from dataclasses import dataclass

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
    raise NotImplementedError


def max_drawdown(returns: pd.Series) -> float:
    raise NotImplementedError
