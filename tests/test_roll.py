"""Roll adjustment -- the #1 futures backtest bug."""

from __future__ import annotations

import pandas as pd

from goldgraveyard.data.roll import verify_no_roll_artifacts


def test_unadjusted_stitch_is_detected():
    """A deliberately broken stitch must be caught, or the check is worthless."""
    idx = pd.bdate_range("2020-01-01", periods=100)
    px = pd.Series(1800.0, index=idx)
    px.iloc[50:] = 1830.0  # phantom contango gap
    roll_dates = pd.Series([idx[50]])
    flagged = verify_no_roll_artifacts(px, roll_dates)
    assert len(flagged) == 1
