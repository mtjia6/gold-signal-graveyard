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

import numpy as np
import pandas as pd

TRADING_DAYS = 252
TARGET_ANNUAL_VOL = 0.10  # Frozen. See DECISIONS.md.
VOL_LOOKBACK_DAYS = 60
VOL_FLOOR = 0.04  # annualized; prevents division blowups in dead-quiet regimes
MAX_LEVERAGE = 3.0


def realized_vol(returns: pd.Series, lookback: int = VOL_LOOKBACK_DAYS) -> pd.Series:
    """Trailing annualized vol, strictly causal (window ends at t-1).

    The `.shift(1)` is the whole point. A plain rolling std at index t includes
    day t's own return, but this number sizes a position decided at the close of
    t -- so including t is peeking at the bar being traded. Shifting by one makes
    the estimate at t depend only on returns through t-1.

    The tell that you got it wrong: strategy vol lands on the target almost
    exactly. A causal estimate always lags a changing vol regime, so it should
    land NEAR the target and miss.
    """
    return returns.rolling(lookback).std().shift(1) * np.sqrt(TRADING_DAYS)


def vol_target(
    raw_position: pd.Series,
    returns: pd.Series,
    *,
    target: float = TARGET_ANNUAL_VOL,
    max_leverage: float = MAX_LEVERAGE,
) -> pd.Series:
    """Scale raw_position so ex-ante portfolio vol ≈ target, capped at max_leverage.

    VOL_FLOOR is a lower bound on the vol ESTIMATE, not on the result. In a very
    quiet stretch the estimate collapses toward zero and target/estimate explodes,
    so the position would be enormous precisely because nothing had moved lately.
    Flooring the denominator bounds that before max_leverage has to.

    No dropna and no ffill here. The first `lookback` values are NaN because no
    estimate exists yet, and that is information the engine needs -- filling it
    would invent positions for days that had no vol estimate.
    """
    scale = target / realized_vol(returns).clip(lower=VOL_FLOOR)
    return (raw_position * scale).clip(-max_leverage, max_leverage)
