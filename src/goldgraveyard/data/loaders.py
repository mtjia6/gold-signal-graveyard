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
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"

OHLCV = ("open", "high", "low", "close", "volume")


def _cache_path(symbol: str) -> Path:
    """Stable, filesystem-safe cache key. `GC=F` -> yahoo_GC_F.parquet."""
    safe = symbol.replace("=", "_").replace(".", "_").replace("-", "_")
    return CACHE_DIR / f"yahoo_{safe}.parquet"


def _normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Flatten yfinance's shape into the OHLCV contract.

    yfinance >= 0.2.51 returns a 2-level column MultiIndex (Price, Ticker) even
    for a single ticker, so `df["close"]` on the raw frame raises. Take level 0
    by name rather than positionally: the level order is not guaranteed.

    `Adj Close` is dropped. For futures there are no splits or dividends, so it
    equals `Close`; keeping both would leave downstream code a silent choice
    between two near-identical columns.
    """
    df = raw.copy()

    if isinstance(df.columns, pd.MultiIndex):
        level = "Price" if "Price" in (df.columns.names or []) else 0
        df.columns = df.columns.get_level_values(level)

    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    df = df.drop(columns=["adj_close"], errors="ignore")

    missing = [c for c in OHLCV if c not in df.columns]
    if missing:
        raise ValueError(f"yfinance response missing columns {missing}; got {list(df.columns)}")

    df = df[list(OHLCV)]

    idx = pd.DatetimeIndex(df.index)
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df.index = idx.normalize()
    df.index.name = "date"

    return df[~df.index.duplicated(keep="last")].sort_index()


def load_yahoo(symbol: str, start: str, end: str, *, refresh: bool = False) -> pd.DataFrame:
    """Daily OHLCV for `symbol`, tz-naive DatetimeIndex, cached to parquet.

    Returns columns: open, high, low, close, volume (lowercase).

    The cache is keyed on symbol alone, so a cached frame is only reused when it
    actually spans the requested window; otherwise it is refetched. Without that
    check, widening the sample in DECISIONS.md would silently return the old,
    narrower history and every backtest would quietly run on the wrong window.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(symbol)

    want_start, want_end = pd.Timestamp(start), pd.Timestamp(end)

    if path.exists() and not refresh:
        cached = pd.read_parquet(path)
        if not cached.empty and cached.index.min() <= want_start:
            return cached.loc[want_start:want_end].copy()

    raw = yf.download(symbol, start=start, end=end, auto_adjust=False, progress=False)
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol} over [{start}, {end}]")

    df = _normalize(raw)
    df.to_parquet(path)
    return df.loc[want_start:want_end].copy()


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
