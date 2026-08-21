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

import numpy as np
import pandas as pd

from . import register

LONG_MONTHS = (1, 9)  # Frozen a priori from folklore, NOT fitted.


@register("seasonality", "Sep and Jan are structurally strong", ())
def seasonality(df: pd.DataFrame) -> pd.Series:
    """+1 during LONG_MONTHS, 0 otherwise. Long-only, never short.

    Values are in {0, 1} rather than {-1, +1}. That is deliberate and within the
    [-1, +1] contract: the hypothesis is that certain months are strong, not that
    the others are weak, so shorting them would be testing a claim nobody made.

    No warmup NaN, because the calendar month is known on every date. This is the
    only signal in the project that needs no price history at all, which also
    makes it the only one immune to the futures roll problem.

    EXPECT LOW REALIZED VOLATILITY, and do not treat it as a bug. The signal is
    flat roughly five sixths of the year, so while its exposure is vol-targeted to
    10% during the months it trades, the full series averages far below that.
    Sharpe is invariant to leverage, so the grade is unaffected.
    """
    month = df.index.month
    return pd.Series(np.where(np.isin(month, LONG_MONTHS), 1.0, 0.0), index=df.index)
