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
from .costs import apply_costs, turnover
from .sizing import vol_target

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
    """Run one signal through the full honest pipeline. No signal bypasses this.

    CAUSALITY WALKTHROUGH, which is the only thing that makes this function correct.

        gross_t = sized_t * ret_t

    Trace what each factor is allowed to know:

      * `sized_t` comes from `lagged_t`, which is `raw_{t-1}` after the shift. So the
        direction was decided at the close of t-1.
      * `sized_t` is also scaled by the volatility estimate at t, and `realized_vol`
        carries its own internal `.shift(1)`, so that estimate spans data through
        t-1 only.
      * `ret_t` is the move over day t.

    Therefore every day's P&L uses only information available at the close of t-1 to
    earn day t's return. Neither factor of the product can see day t before it is
    traded. If that chain holds, there is no lookahead in the engine.

    Note the two shifts are independent and both required. Removing the explicit one
    leaks the direction; removing the one inside `realized_vol` leaks the sizing.
    """
    ret = panel["close"].pct_change()

    raw = signal(panel)
    lagged = raw.shift(EXEC_LAG_BARS)
    sized = vol_target(lagged, ret, target=target_vol)

    gross = sized * ret
    net = apply_costs(gross, sized, cost_bps)

    return BacktestResult(
        name=name,
        positions=sized,
        gross_returns=gross,
        net_returns=net,
        turnover=turnover(sized),
        cost_bps=cost_bps,
    )


def split_is_oos(returns: pd.Series, split_frac: float = 0.60) -> tuple[pd.Series, pd.Series]:
    """First split_frac of the sample is IS; the remainder is OOS, touched once.

    Positional split on the dropna'd series, so the two halves hold comparable
    numbers of live observations rather than comparable spans of calendar time.
    The split point follows from the frozen sample window and is never re-chosen
    after seeing a result.
    """
    r = returns.dropna()
    cut = int(len(r) * split_frac)
    return r.iloc[:cut], r.iloc[cut:]


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
