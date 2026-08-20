"""Signal 7 -- Calendar seasonality.

HYPOTHESIS
    Certain months are systematically strong (Indian wedding/festival demand,
    Chinese New Year restocking) -- classically September and January.

CONSTRUCTION (frozen)
    Long only in September and January; flat otherwise. Months chosen from the
    STATED folklore, not from the data. Picking the best months in-sample and
    then testing them is circular, and this signal is the easiest place in the
    whole project to do that by accident.
"""

from __future__ import annotations

import pandas as pd

from . import register

LONG_MONTHS = (1, 9)  # Frozen a priori from folklore, NOT fitted.


@register("seasonality", "Sep and Jan are structurally strong", ())
def seasonality(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
