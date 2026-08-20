"""Transaction costs.

Cost is charged on TURNOVER, not on trade count: every unit of position change
pays half-spread plus commission. Frozen default and a 2x stress case are both
declared in DECISIONS.md; nothing here may be tuned after seeing results.
"""

from __future__ import annotations

import pandas as pd

TRADING_DAYS = 252
DEFAULT_COST_BPS = 2.0  # round-trip, GC front month. Frozen. See DECISIONS.md.
STRESS_COST_BPS = 4.0


def _position_changes(positions: pd.Series) -> pd.Series:
    """Absolute day-on-day change in position, treating NaN as flat.

    Filling NaN with 0 before differencing is deliberate: the first day a signal
    becomes defined, the position moves from nothing to something, and that move
    is a real trade that has to be paid for. Differencing the raw series would
    produce NaN there and hand the strategy a free entry.
    """
    return positions.fillna(0.0).diff().abs()


def apply_costs(gross_returns: pd.Series, positions: pd.Series, cost_bps: float) -> pd.Series:
    """Net returns = gross - (|change in position| * cost_bps / 2 / 10_000).

    `positions` must be the VOL-SIZED position, not the raw +1/-1 direction. Cost
    is paid on the quantity actually traded, so a signal holding 0.3 units pays
    less to flip than one holding 2.0 units.

    The /2 is because cost_bps is quoted round-trip (in and back out again) while
    a one-day position change of 1.0 is a single one-way trade.
    """
    cost = _position_changes(positions) * cost_bps / 2 / 10_000
    return gross_returns - cost


def turnover(positions: pd.Series) -> float:
    """Mean annualized absolute change in position. Report this for every signal.

    Units are position-units traded per year. A signal flipping between long and
    short daily scores in the hundreds; a 50/200 trend signal should score near 1.
    """
    return float(_position_changes(positions).mean() * TRADING_DAYS)
