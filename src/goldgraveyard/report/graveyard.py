"""Assemble the verdict table.

The verdict rule is frozen in DECISIONS.md and implemented ONCE, here. It is
not allowed to become "well, this one is close enough".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass(frozen=True)
class Verdict:
    signal: str
    is_sharpe: float
    oos_sharpe: float
    net_oos_sharpe: float
    hac_tstat: float
    deflated_sr: float
    regimes_positive: int
    turnover: float
    alive: bool
    cause_of_death: str


def adjudicate(name: str, is_result, oos_result, regime_table: pd.DataFrame) -> Verdict:
    """Apply the frozen ALIVE rule to one signal's results.

    ALIVE requires ALL of:
        net-of-cost OOS mean return > 0
        Deflated Sharpe > 0.95
        mean-return sign positive in >= 2 of the 5 regimes
    Anything else is DEAD, and cause_of_death names the FIRST condition failed.
    """
    raise NotImplementedError


def to_markdown(verdicts: list[Verdict], out: Path) -> None:
    """Write reports/graveyard.md -- the headline table."""
    raise NotImplementedError
