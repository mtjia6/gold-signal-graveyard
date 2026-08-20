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
    raise NotImplementedError
