"""Heteroskedasticity- and autocorrelation-consistent (Newey-West) inference.

WHY THE NAIVE t-STAT LIES
    The usual t = mean / (sd / sqrt(n)) assumes returns are i.i.d. Strategy
    returns are not: a 12-month momentum signal holds the same position for
    months, so consecutive daily returns share a common bet and are positively
    autocorrelated. Positive autocorrelation means the true variance of the
    sample mean is LARGER than sd^2/n, so the naive t-stat is too big -- it
    manufactures significance.

    Newey-West replaces sd^2/n with a variance estimate that sums the
    autocovariances out to a lag L, downweighting them (Bartlett kernel) so the
    estimate stays positive semi-definite.

    Standard automatic bandwidth: L = floor(4 * (n/100)^(2/9)).
"""

from __future__ import annotations

import pandas as pd


def newey_west_tstat(returns: pd.Series, lags: int | None = None) -> tuple[float, float, int]:
    """Return (t_stat, hac_se, lags_used) for H0: mean return = 0.

    Implement with statsmodels: regress returns on a constant, then
    .fit(cov_type="HAC", cov_kwds={"maxlags": lags}). Do not hand-roll the
    kernel unless you want to prove you can -- but if you do, test it against
    statsmodels.
    """
    raise NotImplementedError


def auto_bandwidth(n: int) -> int:
    """Newey-West (1994) rule of thumb: floor(4 * (n/100)^(2/9))."""
    raise NotImplementedError
