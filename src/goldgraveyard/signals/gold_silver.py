"""Signal 5 -- Gold/silver ratio mean reversion.

HYPOTHESIS
    The gold/silver ratio is range-bound over long horizons; extremes revert.

CONSTRUCTION (frozen)
    ratio = gold_close / silver_close, z-scored over 252 days.
    Long gold when z very negative, short gold when z very positive.

HONESTY NOTE
    The real trade is a SPREAD (long one leg, short the other). This project's
    engine trades a single gold exposure. Either implement it as gold-only and
    say so, or extend the engine to two-asset positions -- but do not describe a
    gold-only position as a ratio trade in the writeup.
"""

from __future__ import annotations

import pandas as pd

from . import register

ZSCORE_WINDOW_DAYS = 252  # Frozen.


@register("gold_silver_ratio", "Gold/silver ratio mean-reverts", ("close", "silver_close"))
def gold_silver_ratio(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
