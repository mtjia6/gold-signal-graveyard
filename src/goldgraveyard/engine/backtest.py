"""The single code path every signal goes through.

If a signal looks good, it must be because of the signal, because literally
nothing else differed. That is what this module buys you.

PIPELINE (order matters; each step is a place a real backtest goes wrong)

    1. signal(df)          -> raw desired position at close of day t
    2. .shift(EXEC_LAG)    -> you cannot trade on information at the instant
                              you learn it. One bar, always, no exceptions.
    3. vol_target(...)     -> equalize risk using a strictly causal vol estimate
    4. * returns           -> gross P&L
    5. apply_costs(...)    -> net P&L, charged on turnover
    6. split IS / OOS      -> on a date frozen in advance, never re-chosen

Design choice: vectorized, not event-driven. An event loop buys you order
book realism you do not need for a daily-bar directional study, and costs you
the ability to see the whole pipeline in twenty lines.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from ..types import SignalFn

EXEC_LAG_BARS = 1  # Frozen. Signal at close t -> position held over t+1.


@dataclass(frozen=True)
class BacktestResult:
    """Everything downstream stats need, and nothing they don't."""

    name: str
    positions: pd.Series
    gross_returns: pd.Series
    net_returns: pd.Series
    turnover: float
    cost_bps: float


def run_backtest(
    signal: SignalFn,
    panel: pd.DataFrame,
    *,
    name: str,
    cost_bps: float,
    target_vol: float,
) -> BacktestResult:
    """Run one signal through the full honest pipeline. No signal bypasses this."""
    raise NotImplementedError


def split_is_oos(returns: pd.Series, split_frac: float = 0.60) -> tuple[pd.Series, pd.Series]:
    """First split_frac of the sample is IS; the remainder is OOS, touched once."""
    raise NotImplementedError


def walk_forward(
    signal: SignalFn,
    panel: pd.DataFrame,
    *,
    min_train_days: int,
    step_days: int,
    **kwargs,
) -> BacktestResult:
    """Expanding-window walk-forward: any fitted parameter is refit using only past data.

    Only needed for signals that ESTIMATE something (e.g. the real-yield
    regression beta). Parameter-free signals give identical results to
    run_backtest, and that equality is a good test.
    """
    raise NotImplementedError
