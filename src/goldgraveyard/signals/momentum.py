"""Signal 1 -- Time-series momentum.

HYPOTHESIS (frozen before testing)
    The trailing 12-month return of gold predicts the sign of the next month's
    return. Economically: slow diffusion of macro information plus
    trend-following flows.

CONSTRUCTION (frozen)
    +1 if trailing 252-day return > 0, else -1. No neutral band, no smoothing.
"""

from __future__ import annotations

import pandas as pd

from . import register

LOOKBACK_DAYS = 252  # Frozen.


@register("ts_momentum", "Past 12m return predicts next month's sign", ("close",))
def ts_momentum(df: pd.DataFrame) -> pd.Series:
    """+1 if the trailing 252-day return is positive, else -1. NaN until it exists.

    Hard +/-1 with no neutral band, per the frozen spec. A dead zone around zero
    would be a parameter, and every parameter is a trial the Deflated Sharpe has
    to be told about.

    The first LOOKBACK_DAYS rows have no trailing return, so they stay NaN rather
    than being filled with a position. Same reasoning as ma_cross: filling them
    would have the strategy trading before its own signal is defined, and a
    constant fill reads as a deliberate year-long directional bet.
    """
    close = df["close"]
    trail = close / close.shift(LOOKBACK_DAYS) - 1
    position = (trail > 0).astype(float) * 2 - 1
    return position.where(trail.notna())
