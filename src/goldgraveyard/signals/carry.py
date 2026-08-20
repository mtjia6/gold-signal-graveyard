"""Signal 2 -- Term-structure carry (roll yield).

HYPOTHESIS
    The slope of the gold futures curve predicts return. Gold is a
    cost-of-carry market: the curve is roughly spot * exp((r + storage - lease)
    * T). Deviations of the observed slope from that fair carry are information
    about lease rates and physical tightness.

CONSTRUCTION (frozen)
    roll_yield = log(F_near / F_deferred) / years_between
    Long when roll_yield > 0 (backwardation), short when steeply negative.

NOTE ON DATA
    yfinance gives you only the front month. Real carry needs at least two
    contract months -- this signal may be blocked until you have a second
    series. Say so honestly rather than faking the curve from an interest-rate
    proxy.
"""

from __future__ import annotations

import pandas as pd

from . import register


@register("carry", "Curve slope predicts return", ("f_near", "f_deferred"))
def carry(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
