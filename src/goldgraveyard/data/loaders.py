"""Fetch and cache every raw series the project needs.

Everything lands in data/cache/*.parquet keyed by source+symbol so that a
re-run never re-hits the network. Network flakiness is not an excuse for a
different backtest today than yesterday.

Sources (all free):
    GC=F, SI=F, DX-Y.NYB   yfinance
    DFII10, CPIAUCSL       FRED via pandas_datareader
    COT disaggregated      CFTC annual zip files
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"


def load_yahoo(symbol: str, start: str, end: str, *, refresh: bool = False) -> pd.DataFrame:
    """Daily OHLCV for `symbol`, tz-naive DatetimeIndex, cached to parquet.

    Returns columns: open, high, low, close, volume (lowercase).
    """
    raise NotImplementedError


def load_fred(series_id: str, start: str, end: str, *, refresh: bool = False) -> pd.Series:
    """A single FRED series as a float Series on its native (often daily) index.

    Note: FRED series are AS-REVISED, not as-first-published. DFII10 is not
    revised, so it is safe here; CPIAUCSL IS revised, which is a lookahead
    hazard if you build the optional value signal on it.
    """
    raise NotImplementedError


def load_cot(*, refresh: bool = False) -> pd.DataFrame:
    """CFTC disaggregated COT for gold, weekly.

    Must preserve BOTH dates:
        report_date   the Tuesday the positions were measured
        release_date  the Friday 15:30 ET the public could first see them

    The backtest may only condition on a row once release_date has passed.
    Conflating these two is the classic COT lookahead bug.
    """
    raise NotImplementedError


def load_all(start: str, end: str, *, refresh: bool = False) -> pd.DataFrame:
    """Assemble the single wide daily panel that every signal is handed.

    One index, one calendar (NYMEX gold trading days), forward-filled only
    where forward-filling is economically honest (a stale weekly COT print is
    still the latest known value; a stale price is not).
    """
    raise NotImplementedError
