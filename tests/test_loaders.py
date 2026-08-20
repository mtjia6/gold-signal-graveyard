"""Cache-correctness tests for load_yahoo.

These never touch the network. `yf.download` is replaced with a fake that serves
a synthetic price history in yfinance's real shape -- a (Price, Ticker) column
MultiIndex -- and counts how many times it was called. Counting calls is what
lets us assert that a cache HIT actually avoided the network, which is otherwise
invisible from the return value.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from goldgraveyard.data import loaders

FULL_START, FULL_END = "2000-01-01", "2030-01-01"


class FakeYahoo:
    """Stands in for yf.download. Serves business days from a fixed universe."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []
        idx = pd.bdate_range(FULL_START, FULL_END)
        rng = np.random.default_rng(0)
        close = pd.Series(1000 * (1 + rng.normal(0, 0.01, len(idx))).cumprod(), index=idx)
        self._universe = pd.DataFrame(
            {
                "Adj Close": close,
                "Close": close,
                "High": close * 1.01,
                "Low": close * 0.99,
                "Open": close,
                "Volume": 100,
            }
        )
        self._universe.columns = pd.MultiIndex.from_product(
            [self._universe.columns, ["GC=F"]], names=["Price", "Ticker"]
        )

    def __call__(self, symbol, start, end, **kwargs):
        self.calls.append((start, end))
        # yfinance's `end` is EXCLUSIVE. The fake must reproduce that, or the
        # suite would pass while the real loader dropped its final bar.
        lo, hi = pd.Timestamp(start), pd.Timestamp(end) - pd.Timedelta(days=1)
        return self._universe.loc[lo:hi].copy()


@pytest.fixture
def fake(monkeypatch, tmp_path):
    f = FakeYahoo()
    monkeypatch.setattr(loaders.yf, "download", f)
    monkeypatch.setattr(loaders, "CACHE_DIR", tmp_path)
    return f


def test_exact_repeat_hits_cache(fake):
    a = loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    b = loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    assert len(fake.calls) == 1, "second identical call should not hit the network"
    assert a.equals(b)


def test_narrower_request_hits_cache(fake):
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    inner = loaders.load_yahoo("GC=F", "2010-01-01", "2015-12-31")
    assert len(fake.calls) == 1, "a subset of a cached window needs no refetch"
    assert inner.index.min() >= pd.Timestamp("2010-01-01")
    assert inner.index.max() <= pd.Timestamp("2015-12-31")


def test_request_extending_past_cached_end_refetches(fake):
    """BUILD_LOG Entry 8. The bug: this silently returned data ending in 2020.

    The request starts AFTER the cached start, so a start-only coverage check
    was satisfied and the truncated cache was served with no error.
    """
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    out = loaders.load_yahoo("GC=F", "2006-06-01", "2026-06-30")
    assert len(fake.calls) == 2, "extending the end must trigger a refetch"
    assert out.index.max() > pd.Timestamp("2025-01-01"), (
        f"silently truncated: asked through 2026, got {out.index.max().date()}"
    )


def test_request_starting_before_cached_start_refetches(fake):
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    out = loaders.load_yahoo("GC=F", "2001-01-01", "2020-12-31")
    assert len(fake.calls) == 2
    assert out.index.min() < pd.Timestamp("2002-01-01")


def test_refetch_widens_cache_rather_than_replacing_it(fake):
    """A partial hit must fetch the union, or alternating callers thrash forever."""
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    loaders.load_yahoo("GC=F", "2015-01-01", "2026-06-30")  # refetch #2, union 2006-2026
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")  # original window again
    assert len(fake.calls) == 2, "the widened cache should still serve the first window"


def test_weekend_end_date_does_not_defeat_the_cache(fake):
    """2026-06-28 is a Sunday: no bar exists, but coverage is still satisfied.

    Comparing cached DATA end against the requested end would fail here and
    refetch on every single call, silently disabling the cache.
    """
    loaders.load_yahoo("GC=F", "2006-01-01", "2026-06-28")
    loaders.load_yahoo("GC=F", "2006-01-01", "2026-06-28")
    assert len(fake.calls) == 1


def test_cache_without_metadata_is_not_trusted(fake, tmp_path):
    """A file written by the old code has no coverage record, so it must refetch."""
    df = loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    df.to_parquet(loaders._cache_path("GC=F"))  # plain write, drops the metadata
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    assert len(fake.calls) == 2


def test_refresh_forces_network(fake):
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31", refresh=True)
    assert len(fake.calls) == 2


def test_end_date_is_inclusive(fake):
    """[start, end] is inclusive at both ends, despite yfinance's exclusive `end`.

    2020-12-31 is a Thursday and a trading day. Before this fix it was dropped,
    so a sample declared as ending 2026-06-30 quietly ended a day early.
    """
    out = loaders.load_yahoo("GC=F", "2006-01-01", "2020-12-31")
    assert out.index.max() == pd.Timestamp("2020-12-31")
