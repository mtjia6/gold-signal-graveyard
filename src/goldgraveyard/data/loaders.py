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
import pyarrow as pa
import pyarrow.parquet as pq
import yfinance as yf

CACHE_DIR = Path(__file__).resolve().parents[3] / "data" / "cache"

OHLCV = ("open", "high", "low", "close", "volume")

# Parquet schema-metadata keys recording the window a cache file was fetched for.
REQ_START_KEY = b"goldgraveyard.req_start"
REQ_END_KEY = b"goldgraveyard.req_end"


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


def _write_cache(df: pd.DataFrame, path: Path, start: pd.Timestamp, end: pd.Timestamp) -> None:
    """Persist `df` along with the WINDOW THAT WAS REQUESTED when it was fetched.

    The requested window is stored in the Parquet schema metadata rather than
    inferred from the data, because the two are not the same thing. Ask for data
    through Sunday 2026-06-30 and the last row is Monday 2026-06-29 -- the market
    was closed, not the download truncated. Only the request tells you whether the
    cache is complete.
    """
    table = pa.Table.from_pandas(df)
    meta = dict(table.schema.metadata or {})
    meta[REQ_START_KEY] = str(start.date()).encode()
    meta[REQ_END_KEY] = str(end.date()).encode()
    pq.write_table(table.replace_schema_metadata(meta), path)


def _read_cache(path: Path) -> tuple[pd.DataFrame, pd.Timestamp, pd.Timestamp] | None:
    """Return (frame, requested_start, requested_end), or None if unusable.

    None covers an unreadable file and a file written before this metadata
    existed. Both mean "refetch": a cache whose coverage cannot be established
    must not be trusted, since trusting it is exactly the silent-truncation bug.
    """
    try:
        table = pq.read_table(path)
    except Exception:
        return None

    meta = table.schema.metadata or {}
    if REQ_START_KEY not in meta or REQ_END_KEY not in meta:
        return None

    return (
        table.to_pandas(),
        pd.Timestamp(meta[REQ_START_KEY].decode()),
        pd.Timestamp(meta[REQ_END_KEY].decode()),
    )


def load_yahoo(symbol: str, start: str, end: str, *, refresh: bool = False) -> pd.DataFrame:
    """Daily OHLCV for `symbol`, tz-naive DatetimeIndex, cached to parquet.

    Returns columns: open, high, low, close, volume (lowercase).

    The range [start, end] is INCLUSIVE of both endpoints, unlike yfinance's own
    `end`, which is exclusive.

    CACHE CORRECTNESS
        The cache file is keyed on symbol alone, so it must carry its own record
        of which window it covers. It is reused only when the window requested at
        fetch time fully contains the window requested now -- both ends.

        Guarding only the start is not enough, and the failure is silent: a cache
        built for 2006-2020 would satisfy a 2006-2026 request and hand back five
        fewer years, with every downstream Sharpe computed on the wrong sample and
        nothing raising. See BUILD_LOG.md Entry 8.

        On a partial hit the refetch covers the UNION of the cached and requested
        windows, so the cache only ever grows. Fetching just the requested window
        would let two alternating callers evict each other's data forever.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = _cache_path(symbol)

    want_start, want_end = pd.Timestamp(start), pd.Timestamp(end)
    fetch_start, fetch_end = want_start, want_end

    if path.exists() and not refresh:
        hit = _read_cache(path)
        if hit is not None:
            cached, had_start, had_end = hit
            if had_start <= want_start and had_end >= want_end:
                return cached.loc[want_start:want_end].copy()
            fetch_start = min(fetch_start, had_start)
            fetch_end = max(fetch_end, had_end)

    # yfinance treats `end` as EXCLUSIVE, so asking for end=2026-06-30 returns the
    # last bar before it. Our API documents [start, end] as inclusive -- and
    # DECISIONS.md names 2026-06-30 as the sample end -- so add a day. Without
    # this the final trading day of the sample is silently missing.
    raw = yf.download(
        symbol,
        start=str(fetch_start.date()),
        end=str((fetch_end + pd.Timedelta(days=1)).date()),
        auto_adjust=False,
        progress=False,
    )
    if raw is None or raw.empty:
        raise RuntimeError(f"yfinance returned no data for {symbol} over [{start}, {end}]")

    df = _normalize(raw)
    _write_cache(df, path, fetch_start, fetch_end)
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
