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

import numpy as np
import pandas as pd
from scipy import stats


def probabilistic_sharpe(
    observed_sr: float,
    benchmark_sr: float,
    n_obs: int,
    skew: float,
    kurtosis: float,
) -> float:
    """P(true SR > benchmark_sr), given the observed Sharpe and its higher moments.

        PSR = Phi( (SR_hat - SR*) * sqrt(n - 1)
                   / sqrt(1 - g3*SR_hat + ((g4 - 1)/4) * SR_hat**2) )

    The denominator is the standard error of the Sharpe estimator, corrected for
    non-normality. Under normality (g3 = 0, g4 = 3) it reduces to
    sqrt(1 + SR_hat**2 / 2), the classical Lo (2002) result.

    TWO CONVENTIONS THAT SILENTLY WRECK THIS
        1. FREQUENCY CONSISTENCY. `observed_sr`, `benchmark_sr` and `n_obs` must
           all refer to the SAME period. `n_obs` is a count of observations, so
           if those are daily bars then the Sharpes must be PER-DAY, not
           annualized. Passing an annualized Sharpe (0.523) against a daily n
           (1982) is the single most common PSR bug: it inflates the numerator by
           sqrt(252) and returns a probability of essentially 1.

           This function cannot detect the error, because both arguments are
           plain floats. It trusts the caller. `deflated_sharpe` is the caller
           and is responsible for de-annualizing.

        2. KURTOSIS IS RAW, normal = 3.0, NOT excess. The (g4 - 1)/4 term assumes
           it. `pandas.Series.kurt()` returns EXCESS kurtosis, normal = 0, so
           callers must pass `series.kurt() + 3`.

           HOW MUCH IT MATTERS DEPENDS ON FREQUENCY, and the deciding factor
           is the SR_hat**2 factor on the kurtosis term:

             daily   SR_hat ~ 0.033  ->  SR_hat**2 ~ 0.001   negligible
             monthly SR_hat ~ 0.15   ->  SR_hat**2 ~ 0.023   ~20x larger
             annual  SR_hat ~ 0.5    ->  SR_hat**2 ~ 0.25    dominant

           Measured on ma_cross OOS at daily frequency: correct raw kurtosis
           gives PSR 0.9267, the mistake gives 0.9268. Get it right regardless,
           but at daily frequency do not expect it to explain a surprising
           result. Point this framework at monthly returns and it comes back to
           life.

    THE TWO CONVENTIONS ARE THE SAME TRAP
        Both are governed by the magnitude of the per-period Sharpe. Convention 1
        goes wrong by inflating SR_hat directly, moving PSR from 0.927 to 1.000.
        Convention 2 goes wrong through the SR_hat**2 term, which is why it is
        invisible when SR_hat is small and material when it is not.

    SIGN CHECKS, all satisfied by the formula above
        * positive skew raises PSR: -g3*SR_hat shrinks the denominator
        * higher kurtosis lowers PSR: (g4-1)/4 grows the denominator
        * more observations push PSR toward 1: sqrt(n-1) grows the numerator

    Returns nan rather than raising if the variance term is non-positive, which
    extreme skew can produce and which has no meaningful probability attached.
    """
    if n_obs < 2:
        return float("nan")

    variance = 1.0 - skew * observed_sr + ((kurtosis - 1.0) / 4.0) * observed_sr**2
    if variance <= 0:
        return float("nan")

    z = (observed_sr - benchmark_sr) * np.sqrt(n_obs - 1) / np.sqrt(variance)
    return float(stats.norm.cdf(z))


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """E[max SR] across n_trials independent zero-skill trials.

        E[max] ~= sqrt(V) * [ (1 - g) * Phi^-1(1 - 1/N)
                              + g     * Phi^-1(1 - 1/(N*e)) ]

    where g is the Euler-Mascheroni constant. This is the expected maximum of N
    draws from a normal distribution, from extreme value theory: the maximum of N
    standard normals concentrates around sqrt(2*ln N), and the two-quantile
    expression above is the standard refinement of that approximation.

    Read the result as THE BAR LUCK ALONE CLEARS. If N strategies with true
    Sharpe of zero are tested, the best of them will look about this good. A
    result must beat this to be distinguishable from selection.

    Growth in N is slow, since it goes as sqrt(2*ln N). Going from 8 trials to 80
    raises the bar by roughly 40 percent, not by a factor of ten. Testing more
    things is punished, but gently.

    ARGUMENTS
        sr_variance is the variance of the Sharpe ESTIMATES across trials, not
        the variance of returns. With several trial Sharpes in hand, that is
        np.var(trial_sharpes, ddof=1). Without them, the analytic value under the
        null is 1/(n_obs - 1).

        Both sqrt(sr_variance) and the return value are PER PERIOD. Keep them on
        the same footing as the Sharpe passed to probabilistic_sharpe.

    N = 1 means nothing was selected, so there is no selection bias to correct
    and the bar is zero. The formula cannot express this: Phi^-1(1 - 1/1) is
    Phi^-1(0), which is negative infinity.
    """
    if n_trials < 2:
        return 0.0

    gamma = np.euler_gamma
    z1 = stats.norm.ppf(1.0 - 1.0 / n_trials)
    z2 = stats.norm.ppf(1.0 - 1.0 / (n_trials * np.e))
    return float(np.sqrt(sr_variance) * ((1.0 - gamma) * z1 + gamma * z2))


def deflated_sharpe(
    returns: pd.Series,
    n_trials: int,
    trial_sr_variance: float | None = None,
    periods_per_year: int = 252,
) -> float:
    """DSR for one strategy, given how many trials were actually run.

    The Probabilistic Sharpe Ratio evaluated against the expected-maximum bar
    rather than against zero. Read it as: the probability that this strategy's
    true Sharpe exceeds what the luckiest of n_trials worthless strategies would
    have shown. Below 0.95 is DEAD under the frozen verdict rule.

    EVERYTHING HERE IS PER PERIOD, deliberately. This function computes the
    Sharpe as mean/std of the raw return series, with no annualization, so it
    lines up with n_obs by construction. `periods_per_year` is accepted for
    interface consistency and is not used: annualizing anything inside this
    function would reintroduce the frequency mismatch that probabilistic_sharpe
    cannot detect.

    WHAT COUNTS AS A TRIAL
        A distinct strategy configuration that was a candidate to become the
        reported result. Not an execution count.

        * The same strategy at two cost levels is ONE trial, a sensitivity check.
        * The same strategy in sample and out of sample is ONE trial, two views.
        * Several parameter settings from which the best was kept are N trials,
          because a selection was made among them.

        DECISIONS.md section 6 maintains the ledger, and undercounting it is the
        one way to defeat this correction without noticing.
    """
    r = returns.dropna()
    n = len(r)
    if n < 2:
        return float("nan")

    sd = r.std()
    if sd == 0:
        return float("nan")

    sr = float(r.mean() / sd)
    variance = 1.0 / (n - 1) if trial_sr_variance is None else trial_sr_variance
    benchmark = expected_max_sharpe(n_trials, variance)

    return probabilistic_sharpe(sr, benchmark, n, float(r.skew()), float(r.kurt()) + 3.0)
