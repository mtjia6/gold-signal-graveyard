"""Signal 3 -- COT positioning (contrarian).

HYPOTHESIS
    When managed money is crowded long, the marginal buyer is exhausted and
    forward returns are poor. Contrarian on the net-position z-score.

CONSTRUCTION (frozen)
    z = (net_managed_money - rolling_mean_156w) / rolling_std_156w
    position = -clip(z, -2, 2) / 2

THE LOOKAHEAD LANDMINE
    COT measures positions as of Tuesday and publishes Friday 15:30 ET. Using
    the Tuesday value on Tuesday gives you three days of free foresight, and it
    will look like genuine alpha. The panel carries release_date for exactly
    this reason: condition on release_date, never report_date.
"""

from __future__ import annotations

import pandas as pd

from . import register

ZSCORE_WINDOW_WEEKS = 156  # Frozen.


@register("cot_contrarian", "Crowded specs mean-revert", ("cot_net_mm", "cot_release_date"))
def cot_contrarian(df: pd.DataFrame) -> pd.Series:
    raise NotImplementedError
