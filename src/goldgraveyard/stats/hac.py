"""Heteroskedasticity- and autocorrelation-consistent (Newey-West) inference.

WHY THE NAIVE t-STAT CAN LIE
    The usual t = mean / (sd / sqrt(n)) assumes returns are i.i.d. That
    assumption can fail in two independent ways, and the estimator's name names
    both of them:

    HETEROSKEDASTICITY. Return variance is not constant over time. Volatility
    clusters, which is well documented and measurable (see BUILD_LOG Entry 12:
    the autocorrelation of |return| is +0.11 while the autocorrelation of return
    is -0.01). This holds for essentially every strategy in this project.

    AUTOCORRELATION. Consecutive RETURNS are correlated with each other. Where
    present, the effective sample size is smaller than n, the true variance of
    the sample mean exceeds sd^2/n, and the naive t-stat is too big.

    Newey-West replaces sd^2/n with a variance estimate that sums the
    autocovariances out to a lag L, downweighting them (Bartlett kernel) so the
    estimate stays positive semi-definite.

    Standard automatic bandwidth: L = floor(4 * (n/100)^(2/9)).

THE MISCONCEPTION TO AVOID
    "A trend signal holds one position for months, so its returns are
    autocorrelated" is FALSE, and this project measured it directly.

    Strategy return is w_{t-1} * r_t. Where w is roughly constant across a
    stretch, those returns are the asset's returns scaled by a constant, and
    scaling an uncorrelated series by a constant leaves it uncorrelated. Gold's
    daily returns autocorrelate at -0.0096; ma_cross's returns autocorrelate at
    -0.0037 despite flipping direction only 28 times in twenty years. Naive and
    HAC t-stats agreed to three decimals (1.466 vs 1.472). See Entry 18.

    POSITIONS autocorrelate. RETURNS need not. They are different series.

WHERE AUTOCORRELATION GENUINELY ARISES
    * Overlapping return windows, e.g. testing k-month forward returns sampled
      more often than every k months. This is the classic case the estimator
      was designed for.
    * Positions that track an autocorrelated quantity rather than flipping
      between constants: a rolling-regression residual is autocorrelated by
      construction, so real_yield_dev is a candidate here.
    * Continuous, slow-moving signals whose position drifts daily.

    Run it regardless. The heteroskedasticity correction is doing work even when
    the autocorrelation correction is not, and finding that the two t-stats agree
    is itself a result worth reporting.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm


def auto_bandwidth(n: int) -> int:
    """Newey-West (1994) rule of thumb: floor(4 * (n/100)^(2/9)).

    Sets how many lags of autocorrelation to correct for. It grows with sample
    size but slowly: the exponent 2/9 means quadrupling the sample raises the
    bandwidth by only about a third. Too few lags leaves autocorrelation
    uncorrected; too many adds noise, since each extra autocovariance is itself
    estimated from the same finite sample.
    """
    return int(np.floor(4 * (n / 100) ** (2 / 9)))


def newey_west_tstat(returns: pd.Series, lags: int | None = None) -> tuple[float, float, int]:
    """Return (t_stat, hac_se, lags_used) for H0: mean return = 0.

    THE TRICK
        Regressing a series on nothing but a column of ones makes the fitted
        coefficient the sample MEAN, and its t-statistic tests exactly the
        hypothesis we care about. So "is the mean return different from zero"
        becomes a regression, and regression machinery then lets a HAC
        covariance estimator be swapped in with a single argument.

    WHY cov_type="HAC" IS NOT OPTIONAL
        Omit it and statsmodels returns the ordinary standard error, computed
        under the assumption that observations are independent. Strategy returns
        are not. Positive autocorrelation means the effective sample size is
        smaller than n, the true standard error of the mean is larger than the
        i.i.d. formula gives, and the naive t-statistic is therefore too large.
        It runs without error and reports significance that is not there.
    """
    r = returns.dropna()
    if lags is None:
        lags = auto_bandwidth(len(r))

    model = sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return float(model.tvalues[0]), float(model.bse[0]), lags
