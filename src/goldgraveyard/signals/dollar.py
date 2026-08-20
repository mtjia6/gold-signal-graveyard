"""Signal 8 -- Dollar trend.

HYPOTHESIS
    Gold is priced in dollars, so a weakening dollar mechanically lifts it.

CONSTRUCTION (frozen)
    +1 when DXY 60-day change < 0, else -1.

THE INTERESTING QUESTION FOR THE AUTOPSY
    A contemporaneous negative correlation between gold and DXY is not a
    signal -- it is an identity of quotation. The signal only exists if
    PAST dollar moves predict FUTURE gold moves. Keep that distinction sharp
    in the writeup; it is the difference between a hedge ratio and alpha.
"""

from __future__ import annotations

import pandas as pd

from . import register

LOOKBACK_DAYS = 60  # Frozen.


@register("dollar_trend", "Past USD trend predicts gold", ("dxy",))
def dollar_trend(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
