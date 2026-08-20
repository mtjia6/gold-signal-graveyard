"""Invariants the engine must satisfy no matter which signal is running.

These are RED right now. That is correct: they are the specification, and you
turn them green one at a time. Do not weaken a test to make it pass.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from goldgraveyard.engine.backtest import EXEC_LAG_BARS, run_backtest


@pytest.fixture
def perfect_foresight_panel() -> pd.DataFrame:
    """A panel where tomorrow's return is known today, on purpose.

    A correct engine must NOT make money here, because the one-bar execution
    lag should destroy the foresight. If this test shows a big Sharpe, the lag
    is missing somewhere.
    """
    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2010-01-01", periods=2000)
    rets = pd.Series(rng.normal(0, 0.01, len(idx)), index=idx)
    close = 1000 * (1 + rets).cumprod()
    return pd.DataFrame({"close": close, "ret": rets})


def test_execution_lag_kills_same_bar_foresight(perfect_foresight_panel):
    """Signal = sign of TODAY's return should earn ~0 after the lag."""
    def cheat(df):
        return np.sign(df["ret"])

    res = run_backtest(
        cheat, perfect_foresight_panel, name="cheat", cost_bps=0.0, target_vol=0.10
    )
    ann = res.gross_returns.mean() * 252
    assert abs(ann) < 0.05, "engine leaked same-bar information"


def test_lag_is_exactly_one_bar():
    assert EXEC_LAG_BARS == 1


def test_positions_are_shifted_not_reindexed(perfect_foresight_panel):
    """The first EXEC_LAG_BARS positions must be NaN/zero, never back-filled."""
    def always_long(df):
        return pd.Series(1.0, index=df.index)

    res = run_backtest(
        always_long, perfect_foresight_panel, name="long", cost_bps=0.0, target_vol=0.10
    )
    assert res.positions.iloc[0] in (0.0,) or pd.isna(res.positions.iloc[0])


def test_costs_reduce_returns(perfect_foresight_panel):
    def flippy(df):
        return pd.Series(np.where(np.arange(len(df)) % 2 == 0, 1.0, -1.0), index=df.index)

    res = run_backtest(
        flippy, perfect_foresight_panel, name="flippy", cost_bps=2.0, target_vol=0.10
    )
    assert res.net_returns.sum() < res.gross_returns.sum()


def test_vol_target_is_achieved(perfect_foresight_panel):
    def always_long(df):
        return pd.Series(1.0, index=df.index)

    res = run_backtest(
        always_long, perfect_foresight_panel, name="long", cost_bps=0.0, target_vol=0.10
    )
    realized = res.gross_returns.std() * np.sqrt(252)
    assert 0.07 < realized < 0.14, f"vol target missed: {realized:.3f}"
