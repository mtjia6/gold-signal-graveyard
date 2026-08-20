"""Volatility targeting.

WHY: comparing a signal that runs at 25% vol against one at 6% vol tells you
who bet bigger, not who predicted better. Scaling both to the same target vol
makes Sharpe the only axis of comparison.

THE TRAP: the vol estimate must use only data available at the time it scales
the position. An estimate computed on the full sample, or on a window that
includes day t while sizing day t, is lookahead -- and it is a subtle one,
because it inflates Sharpe without ever touching the signal itself.
"""

from __future__ import annotations

import pandas as pd

TARGET_ANNUAL_VOL = 0.10  # Frozen. See DECISIONS.md.
VOL_LOOKBACK_DAYS = 60
VOL_FLOOR = 0.04  # annualized; prevents division blowups in dead-quiet regimes
MAX_LEVERAGE = 3.0


def realized_vol(returns: pd.Series, lookback: int = VOL_LOOKBACK_DAYS) -> pd.Series:
    """Trailing annualized vol, strictly causal (window ends at t-1)."""
    raise NotImplementedError


def vol_target(
    raw_position: pd.Series,
    returns: pd.Series,
    *,
    target: float = TARGET_ANNUAL_VOL,
    max_leverage: float = MAX_LEVERAGE,
) -> pd.Series:
    """Scale raw_position so ex-ante portfolio vol ≈ target, capped at max_leverage."""
    raise NotImplementedError
