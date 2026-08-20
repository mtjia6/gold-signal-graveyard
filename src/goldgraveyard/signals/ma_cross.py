"""Signal 6 -- 50/200 moving average crossover.

HYPOTHESIS
    Price trend persists; the golden cross marks it.

CONSTRUCTION (frozen)
    +1 when SMA(50) > SMA(200), else -1.

WHY THIS IS THE FIRST ONE YOU BUILD
    It is trivially correct to compute, so any weirdness in the result is a
    bug in the ENGINE, not the signal. Use it to shake out the plumbing.
    It is also the signal the overfitting sidecar will data-mine, which makes
    the frozen 50/200 baseline the control it gets compared against.
"""

from __future__ import annotations

import pandas as pd

from . import register

FAST, SLOW = 50, 200  # Frozen.


@register("ma_cross", "50/200 trend persists", ("close",))
def ma_cross(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
