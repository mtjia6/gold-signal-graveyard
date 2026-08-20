"""Deflated Sharpe Ratio (Bailey & Lopez de Prado, 2014). The crown jewel.

THE PROBLEM
    Test 8 signals -- really more, once you count every variant you quietly
    tried -- and the best one looks good even if all 8 are worthless. The
    maximum of N noisy Sharpes has a positive expectation that grows with N.

THE FIX, IN TWO PARTS
    1. Expected maximum Sharpe under the null. If you run N independent trials
       whose true Sharpe is zero and whose Sharpe estimates have variance V,
       the expected best is approximately

           E[max SR] ~= sqrt(V) * ( (1-g) * z(1 - 1/N) + g * z(1 - 1/(N*e)) )

       where g is Euler-Mascheroni and z is the standard normal quantile. That
       is the bar luck alone clears -- the "Sharpe you must beat to be boring".

    2. The Probabilistic Sharpe Ratio of the observed Sharpe AGAINST that bar,
       using a standard error that corrects for skew and kurtosis:

           PSR(SR*) = Phi( (SR - SR*) * sqrt(T-1)
                           / sqrt(1 - skew*SR + (kurt-1)/4 * SR^2) )

       Negative skew and fat tails INFLATE the denominator, which is exactly
       right: a strategy that makes money slowly and loses it all at once has a
       less trustworthy Sharpe than its point estimate suggests.

    DSR = PSR evaluated at SR* = E[max SR]. Read it as a probability the true
    Sharpe exceeds zero given how hard you looked. Below 0.95 -> DEAD.

REFERENCES
    Bailey & Lopez de Prado (2014), "The Deflated Sharpe Ratio", J. Portfolio
    Management 40(5). Read section 3 before implementing.
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
    """PSR: P(true SR > benchmark_sr). kurtosis is the RAW fourth moment (3.0 = normal)."""
    raise NotImplementedError


def expected_max_sharpe(n_trials: int, sr_variance: float) -> float:
    """E[max SR] across n_trials independent zero-skill trials."""
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
    this test without noticing.
    """
    raise NotImplementedError
