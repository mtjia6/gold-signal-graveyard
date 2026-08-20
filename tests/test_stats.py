"""The gauntlet's statistics, checked against cases with known answers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from goldgraveyard.stats.deflated_sharpe import expected_max_sharpe, probabilistic_sharpe
from goldgraveyard.stats.hac import auto_bandwidth, newey_west_tstat


def test_hac_widens_se_under_positive_autocorrelation():
    """The whole reason HAC exists: autocorrelated returns must lose t-stat."""
    rng = np.random.default_rng(1)
    n = 2000
    eps = rng.normal(0, 0.01, n)
    ar = np.zeros(n)
    for i in range(1, n):
        ar[i] = 0.7 * ar[i - 1] + eps[i]
    s = pd.Series(ar + 0.001)
    naive_t = s.mean() / (s.std() / np.sqrt(n))
    hac_t, _, _ = newey_west_tstat(s)
    assert abs(hac_t) < abs(naive_t)


def test_auto_bandwidth_matches_rule_of_thumb():
    assert auto_bandwidth(1000) == int(np.floor(4 * (1000 / 100) ** (2 / 9)))


def test_expected_max_sharpe_grows_with_trials():
    v = 0.5
    assert expected_max_sharpe(100, v) > expected_max_sharpe(10, v) > expected_max_sharpe(2, v)


def test_psr_at_own_sharpe_is_half():
    """PSR of an observed Sharpe against itself is 0.5 by construction."""
    assert probabilistic_sharpe(1.0, 1.0, 1000, 0.0, 3.0) == pytest.approx(0.5, abs=1e-6)


def test_negative_skew_lowers_psr():
    """Slow-gains/fast-losses profiles deserve less confidence at the same Sharpe."""
    hi = probabilistic_sharpe(1.0, 0.0, 1000, 0.0, 3.0)
    lo = probabilistic_sharpe(1.0, 0.0, 1000, -2.0, 3.0)
    assert lo < hi
