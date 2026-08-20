"""Signal 4 -- Real-yield deviation.

HYPOTHESIS
    Gold is a zero-coupon real asset, so its price should track the 10y TIPS
    real yield inversely. Deviations from that relationship mean-revert.

CONSTRUCTION (frozen)
    Rolling 500-day OLS of log(gold) on DFII10. Trade the residual:
    position = -clip(resid_z, -2, 2) / 2.

WHY THIS ONE NEEDS WALK-FORWARD
    Unlike the other seven, this signal ESTIMATES a parameter (beta). A
    full-sample beta is lookahead -- the regression has seen the whole history.
    It must be refit on an expanding or rolling window using only past data.
"""

from __future__ import annotations

import pandas as pd

from . import register

REG_WINDOW_DAYS = 500  # Frozen.


@register("real_yield_dev", "Gold reverts to its TIPS relationship", ("close", "dfii10"))
def real_yield_dev(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
