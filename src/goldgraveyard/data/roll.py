"""Back-adjustment of a stitched continuous futures series.

THE BUG THIS FILE EXISTS TO PREVENT
    A continuous futures series is several contracts glued end to end. At each
    roll the front contract is replaced by a deferred one trading at a
    different price. If you stitch raw prices, the gap between them shows up in
    your return series as a real return that no position could ever have
    earned. Gold is usually in contango, so those phantom gaps are
    systematically negative -- a fake, persistent, tradeable-looking drift.

    Back-adjusting removes the gap by shifting (Panama/difference method) or
    scaling (ratio method) all history before each roll.

    Ratio-adjusted is preferred here because percentage returns are then exact
    and the series never crosses zero. Difference-adjusted preserves dollar
    spreads. Say which you used and never mix them.
"""

from __future__ import annotations

import pandas as pd


def ratio_back_adjust(contracts: dict[str, pd.DataFrame], roll_dates: pd.Series) -> pd.DataFrame:
    """Splice per-contract OHLCV into one ratio-back-adjusted continuous series."""
    raise NotImplementedError


def verify_no_roll_artifacts(
    px: pd.Series, roll_dates: pd.Series, *, z_thresh: float = 8.0
) -> pd.DataFrame:
    """Sanity check: return any roll date whose 1-day return is a |z| > z_thresh outlier.

    A correct back-adjustment leaves nothing anomalous at the seams. Run this
    as a TEST, not as a print statement you glance at once.
    """
    raise NotImplementedError
