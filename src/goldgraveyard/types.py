"""Shared type aliases and the core contracts every piece of the system obeys.

Two contracts hold the whole project together. Everything else is detail.

CONTRACT 1 -- SignalFn
    A signal is a pure function:  (pd.DataFrame) -> pd.Series

    Input:  a DataFrame indexed by trading date, containing every column the
            signal is allowed to see (prices, curve, COT, macro).
    Output: a float Series on the SAME index, giving the DESIRED position at
            the close of that date, in units of "target exposure", where
            +1 = fully long, -1 = fully short, 0 = flat.

    The signal does NOT apply the execution lag, does NOT vol-target, and does
    NOT subtract costs. The engine does all three, identically, for every
    signal. That uniformity is the entire point of the project.

CONTRACT 2 -- returns are simple, not log
    All return series are simple arithmetic returns of the back-adjusted
    continuous contract. Sharpe, drawdown, and vol targeting all assume this.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol

import pandas as pd

SignalFn = Callable[[pd.DataFrame], pd.Series]


class Signal(Protocol):
    """A named, frozen-parameter signal ready for the gauntlet."""

    name: str
    hypothesis: str
    requires: tuple[str, ...]

    def __call__(self, df: pd.DataFrame) -> pd.Series: ...
