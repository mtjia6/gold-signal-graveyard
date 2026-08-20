"""Transaction costs.

Cost is charged on TURNOVER, not on trade count: every unit of position change
pays half-spread plus commission. Frozen default and a 2x stress case are both
declared in DECISIONS.md; nothing here may be tuned after seeing results.
"""

from __future__ import annotations

import pandas as pd

DEFAULT_COST_BPS = 2.0  # round-trip, GC front month. Frozen. See DECISIONS.md.
STRESS_COST_BPS = 4.0


def apply_costs(gross_returns: pd.Series, positions: pd.Series, cost_bps: float) -> pd.Series:
    """Net returns = gross - (|Δposition| * cost_bps / 2 / 10_000).

    The /2 is because cost_bps is quoted round-trip and |Δposition| of 1.0 is
    a one-way trade.
    """
    raise NotImplementedError


def turnover(positions: pd.Series) -> float:
    """Mean annualized |Δposition|. Report this for every signal."""
    raise NotImplementedError
