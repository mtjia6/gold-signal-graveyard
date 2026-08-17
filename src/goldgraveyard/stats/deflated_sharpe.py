"""Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014). The crown jewel.

THE PROBLEM
    Test 8 signals -- really more, once you count every variant you quietly
    tried -- and the best one looks good even if all 8 are worthless. The
    maximum of N noisy Sharpes has a positive expectation that grows with N.
    Your job is to work out what that expectation is and subtract it.

THE TWO QUESTIONS YOU HAVE TO ANSWER
    1. If N strategies with TRUE Sharpe of zero are tested, how high does the
       best one's MEASURED Sharpe get, on average, by luck alone? That number
       is the bar. Anything below it is indistinguishable from noise.
       (Hint: this is an extreme-value question about the max of N draws.)

    2. Given an observed Sharpe, how confident can you be that the true Sharpe
       exceeds that bar? This needs a standard error for the Sharpe estimator
       itself -- and the naive one is wrong, because it assumes returns are
       normal. Work out how skew and kurtosis should move that standard error,
       and sanity-check the sign of each effect before you trust the algebra:
       should a strategy that grinds up and crashes down get MORE or LESS
       credit than a symmetric one at the same Sharpe?

    DSR is (2) evaluated at the bar from (1). Below 0.95 -> DEAD.

WHERE TO GET THE MATH
    Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio: Correcting for
    Selection Bias, Backtest Overfitting and Non-Normality", Journal of
    Portfolio Management 40(5), 94-107. Section 2 gives the Probabilistic
    Sharpe Ratio, Section 3 the deflation. Derive it from the paper rather
    than from a blog post -- the blog versions routinely drop the (T-1) or
    misstate the kurtosis convention, and you will not catch it.

    Watch the kurtosis convention: RAW fourth moment (normal = 3) vs EXCESS
    (normal = 0). Pandas .kurt() returns excess. Getting this wrong shifts
    every DSR in the project in the same direction, so it will look plausible.
"""

from __future__ import annotations

import pandas as pd


def probabilistic_sharpe(
    observed_sr: float,
    benchmark_sr: float,
    n_obs: int,
    skew: float,
    kurtosis: float,
) -> float:
    """P(true SR > benchmark_sr), given the observed Sharpe and its higher moments.

    Decide and document your kurtosis convention in the docstring before you
    write the body. tests/test_stats.py assumes RAW (normal = 3.0).
    """
    raise NotImplementedError


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """E[max SR] across n_trials independent zero-skill trials.

    sr_variance is the variance of the Sharpe ESTIMATES across those trials,
    not the variance of returns. Be clear with yourself about which you have.
    """
    raise NotImplementedError


def deflated_sharpe(
    returns: pd.Series,
    n_trials: int,
    trial_sr_variance: float | None = None,
    periods_per_year: int = 252,
) -> float:
    """DSR for one strategy, given how many trials were actually run.

    n_trials is the honest count of EVERY variant tried across the project,
    not the 8 in the headline table. Under-reporting it is how people cheat
    this test without noticing. See DECISIONS.md section 6.
    """
    raise NotImplementedError
