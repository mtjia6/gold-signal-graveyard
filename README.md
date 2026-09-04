# The Gold Signal Graveyard

This repository implements a backtesting framework for COMEX gold futures signals. It is
built so that no signal can influence how it is executed, sized, costed, or counted among
the candidates the multiple-testing correction accounts for. Those decisions are made
once, in shared engine code, and applied identically regardless of which signal is
running, which is what allows the framework to claim that any two signals in it were
compared fairly. Eight signals have been pre-registered, each with a hypothesis and a set
of parameters fixed in advance of any result. Three of the eight have been implemented
and carried through the full evaluation pipeline to date, and none of them meets the
pre-registered bar for a genuine effect. The strongest of the three, a 50/200-day
moving-average crossover, produces an out-of-sample Sharpe ratio of 0.523. Once that
estimate is corrected for the fact that eight candidate signals were tested and this was
the best-performing one, its Deflated Sharpe Ratio falls to 0.503, a value statistically
indistinguishable from what the best of eight strategies with no real predictive power
would be expected to produce by chance.

What distinguishes this framework from a conventional backtest is that each of the
following is enforced in shared engine code rather than left to each signal's own
implementation:

- **No lookahead bias.** A signal's raw position is computed from data through day *t*'s
  close, but the position actually traded is shifted forward one bar, so every day's P&L
  is earned using only information known as of the previous close. This is verified with
  an adversarial test, not just asserted; see Execution pipeline below.
- **Uniform volatility targeting.** Every signal is scaled to the same 10% annualized
  risk target using a strictly causal estimator, so Sharpe ratios are comparable across
  signals rather than reflecting which one took the larger position.
- **Uniform, non-zero transaction costs.** Every signal is charged the same cost per unit
  of turnover, at both a base and a stress assumption, rather than being evaluated
  frictionlessly or at a cost only some signals pay.
- **A pre-registered, dated record of every trial.** Parameters, regimes, and the verdict
  rule were committed to version control before any result existed, and the ledger of
  what counts as a distinct trial is fixed in advance rather than reconstructed after
  seeing which signals looked good.
- **A correction for having tested multiple candidates.** The Deflated Sharpe Ratio
  discounts each signal's Sharpe for the number of other candidates it was tested
  against, so a result that only looks good because it was the best of several is not
  reported as if it were tested in isolation.
- **A check for single-regime dependence.** Each signal's return is required to be
  positive in at least 2 of 5 pre-registered market regimes, so a result driven entirely
  by one historical period does not pass as a general finding.

## Methodology

### The signal contract

`types.py` defines a signal as a function from the available data panel to a position in
`[-1, +1]` at the close of each trading day, and nothing more. The signal itself has no
say in how that position is lagged before execution, how it is scaled for risk, what it
costs to trade, or how many other signals it is being evaluated alongside. Those
decisions are made in engine code that every registered signal is routed through. This
matters because most of what makes a conventional backtest unreliable, a lookahead bug in
one strategy, inconsistent risk scaling between two strategies, transaction costs applied
selectively, tends to originate in each strategy owning its own execution logic. Centralizing
those five decisions removes the opportunity for that kind of inconsistency to enter the
comparison at all, so the claim that two signals were evaluated on equal terms can be
verified by reading one module rather than trusted on the author's word.

### Execution pipeline

Every signal passes through the same six steps, implemented in `engine/backtest.py`:

```
1. signal(df)          raw position at close of day t, in [-1, +1]
2. .shift(1)            EXEC_LAG_BARS = 1, applied unconditionally
3. vol_target(...)      scale to 10% annualized vol, causal 60-day estimate
4. * returns            gross P&L
5. apply_costs(...)     net P&L, charged on turnover
6. split_is_oos(...)    60/40 split, date fixed before any signal ran
```

The signal function computes its raw position for day *t* using the data panel through
day *t*'s own close, since that is the only way to construct something like a
moving-average crossover or a trailing-return signal in the first place. A trader cannot
act on a closing price at the instant it is set, so that raw position is not what is
actually traded on day *t*. Step 2 shifts the entire raw series forward by one bar, so
the position held during day *t* is the one the signal computed as of day *t-1*'s close:
the decision for today's trading is made from yesterday's price, not today's. This shift
is the mechanism the "no lookahead" claim rests on, and every other property claimed for
the engine depends on it being applied uniformly and without exception.

The pipeline is vectorized rather than event-driven, which forgoes order-book simulation
in exchange for an execution path short enough to audit in full and identical across
every signal that runs through it, a tradeoff appropriate for a daily-bar directional
study of this kind.

The causality of the pipeline can be checked directly rather than taken on faith. Gross
P&L on day *t* is `sized_t * ret_t`. The sized position, `sized_t`, is derived from
`raw_{t-1}`, so the direction of the trade is fixed at the close of day *t-1*. It is also
scaled by the volatility estimate at day *t*, and that estimator carries its own
independent lag, so the sizing of the trade is fixed as of *t-1* as well. Day *t*'s return
is the only term in the product that depends on information from day *t* itself. Both
lags are necessary on their own terms: removing the explicit shift on the signal would
let its direction see the future, and removing the shift inside the volatility estimator
would let position size see it instead. This claim is tested rather than argued.
`test_engine_invariants.py` constructs a signal that is given tomorrow's return directly
and bets on it. Run through the pipeline with the lag in place, that signal scores a
Sharpe ratio of -0.256. Run with the lag removed, it scores +16.509. The difference of
roughly 17 Sharpe is the value of that one line of code, and it also serves as a
reference point: a Sharpe ratio near 16 on daily gold data is what a lookahead bug looks
like when one is present. Reading the pipeline and concluding it contains no lookahead is
not sufficient evidence on its own, since a lookahead bug is specifically the kind of
error that reads as correct code.

### Position sizing

```python
scale = target / realized_vol(returns).clip(lower=VOL_FLOOR)
sized = (raw_position * scale).clip(-max_leverage, max_leverage)
```

The constants here, `TARGET_ANNUAL_VOL = 0.10`, `VOL_LOOKBACK_DAYS = 60`,
`VOL_FLOOR = 0.04`, and `MAX_LEVERAGE = 3.0`, were frozen before any signal was run.
Scaling every signal to the same target volatility is what allows the Sharpe ratio to
serve as the sole basis for comparison between them; comparing raw returns instead would
measure which signal took the larger position rather than which one predicted more
accurately. The floor on the volatility estimate exists because during an unusually quiet
period the estimate can approach zero, at which point `target / estimate` grows very
large and produces a position size that reflects an estimation artifact rather than
conviction. The sized series is not forward-filled or dropped of missing values, so the
first 60 observations remain undefined because no volatility estimate yet exists for
them; filling those values would assign a position to a day for which the model had no
basis to do so. One diagnostic follows directly from the construction: if realized
strategy volatility lands exactly on the 10% target, the estimator is very likely using
information from the day it is sizing, since a properly causal estimate lags a changing
volatility regime and should measurably miss the target rather than match it.

### Transaction costs

```python
cost = |Δposition| * cost_bps / 2 / 10_000
net  = gross - cost
```

Cost is charged as a function of turnover, the day-on-day change in the sized position,
rather than as a flat per-trade charge, so a signal running at 0.3x exposure incurs less
cost to reverse than one running at 2.0x. Because `cost_bps` is quoted round-trip, the
formula divides by two to arrive at the cost of a single one-way change in position. The
base case assumes 2 basis points round-trip on the GC front-month contract, and every
reported result is also computed under a 4 basis point stress case.

### Statistical evaluation

Passing through the engine produces a Sharpe ratio, which by itself says nothing about
whether the result reflects a genuine effect. Three further checks are applied to each
signal before that question can be answered.

**Newey-West standard errors.** The ordinary t-statistic assumes returns are independent
and identically distributed, an assumption that fails here in two respects. Return
variance is not constant over time: the autocorrelation of the absolute return measures
at +0.11, against -0.01 for the signed return itself, indicating that volatility clusters
even though the direction of returns does not. And to the extent that consecutive returns
are correlated at all, the effective sample size is smaller than the raw observation
count, which the ordinary t-statistic does not account for. `stats/hac.py` addresses this
by regressing the return series on a constant, whose fitted coefficient is simply the
sample mean, and requesting a heteroskedasticity- and autocorrelation-consistent
covariance estimate from `statsmodels`, using the Newey-West (1994) automatic bandwidth
rule, `L = floor(4*(n/100)^(2/9))`. One assumption worth verifying directly rather than
assuming: a trend-following signal that holds a single position for months does not
necessarily produce autocorrelated returns, because the strategy's return is `w_{t-1} *
r_t`, and scaling an uncorrelated series by a roughly constant weight leaves it
uncorrelated. Gold's own daily returns autocorrelate at -0.0096, and `ma_cross`'s
strategy returns autocorrelate at -0.0037 despite the position changing direction only 28
times across twenty years; its naive and HAC-corrected t-statistics agree to three
decimal places, 1.466 against 1.472. Positions can be autocorrelated even when the
returns they generate are not, since the two are distinct series related only through the
signal's own persistence.

**Deflated Sharpe Ratio**, following Bailey and López de Prado (2014). Testing *N*
candidate signals and reporting only the best-performing one biases the reported Sharpe
ratio upward even when every candidate has a true Sharpe of zero, because the expected
value of the maximum of *N* noisy draws increases with *N*. The Deflated Sharpe Ratio
estimates the probability that the true Sharpe ratio is positive once that selection
effect has been accounted for, using a standard error for the Sharpe estimate that is
corrected for the skewness and kurtosis of the return distribution rather than assuming
normality. Its derivation is not reproduced in this document; it is best worked through
from the original paper (*Journal of Portfolio Management* 40(5), pages 94 to 107) rather
than a secondary summary, since several widely circulated summaries drop a `(T-1)` term
or invert the convention for raw versus excess kurtosis, either of which biases every
downstream figure in the same direction without producing an obvious symptom. The
`ma_cross` result illustrates why the trial count matters as much as the point estimate:

| N (trials) | Deflated Sharpe |
|---|---|
| 1 | 0.927 |
| 4 | 0.659 |
| 8 (actual) | 0.503 |
| 16 | 0.370 |
| 50 | 0.211 |

The underlying return series is identical across every row of this table; only the
assumed number of trials changes, and that alone moves the estimate from a Sharpe ratio
that would ordinarily be considered reliable to one that would not. At the actual trial
count of 8, the Sharpe ratio expected from selection bias alone, in a population of
strategies with no true edge, is 0.520; `ma_cross` produced 0.523, a margin of 0.003.
Because the trial count is the one input in this framework that cannot be verified from
outside the repository, the trial ledger is committed to version control and dated before
any result existed, with an explicit definition of what qualifies as a trial: rerunning a
signal under a second cost assumption is a sensitivity check on an existing candidate
rather than a new trial, while each distinct configuration evaluated in a parameter
search counts as its own trial regardless of how the search itself is implemented.

**Regime stability.** Five market regimes for gold are defined in advance, based on
gold's own price history, the run-up into the 2011 peak, the bear market that followed
it, the COVID period, and so on, rather than on periods during which any particular
signal happened to perform well. Selecting regime boundaries after observing results
would reintroduce the same overfitting problem at a coarser time scale. `stats/regimes.py`
reports the number of observations in each regime alongside its mean return and Sharpe
ratio, since the COVID regime spans a single calendar year and carries roughly a fifth of
the observation count of the bull-run regime, and a mean computed over a small sample
should not be weighted the same as one computed over a large one. One limitation in this
check was identified during development and documented rather than corrected: because
gold's own unconditional return is positive in 4 of the 5 regimes, a signal with a
persistent long bias will tend to clear the "positive in at least 2 of 5" requirement as
a consequence of that general tendency rather than because of anything specific to the
signal. In one instance the margin involved is narrow enough to state directly:
`ts_momentum` satisfies one regime on an annualized mean return of roughly half a basis
point. The threshold has been left as originally specified rather than tightened, on the
same reasoning that governs the rest of the pre-registration: a threshold adjusted after
observing that it was too easy to satisfy is methodologically equivalent to one relaxed
after observing that it was too hard to satisfy, and neither is defensible once results
are known.

### The verdict rule and its rationale

> A signal is classified ALIVE if all three of the following hold: a positive
> out-of-sample return net of trading costs; a Deflated Sharpe Ratio above 0.95; and a
> mean return that is positive in at least 2 of the 5 pre-registered regimes. A signal
> that fails any of these is classified DEAD, with cause of death recorded as the first
> condition it failed to satisfy.

Each condition targets a distinct way a backtest result can be misleading, and the rule
requires all three because satisfying any two alone would leave one failure mode
unaddressed. The net-of-cost return requirement is a minimum condition for economic
relevance: a signal that cannot clear its own transaction costs is not tradeable
regardless of any statistical property it might otherwise have, and this condition is
checked before either statistical correction is applied. The Deflated Sharpe threshold of
0.95 addresses selection bias specifically, and was set to correspond to a conventional
95 percent confidence level rather than to make a first result easy to pass; a lower
threshold would accept a strategy no more reliable than the best of a handful of coin
flips. The regime condition addresses a failure mode neither of the other two conditions
can catch on its own, which is a result driven almost entirely by a single historical
period; a signal profitable in exactly one of five regimes may be describing that period
rather than a durable relationship, even if its aggregate Sharpe ratio and Deflated
Sharpe Ratio both look acceptable when computed over the full sample.

The rule permits no exceptions and no allowance for a result that falls just short of a
threshold, because a threshold that can be revised once its outcome is known no longer
functions as a constraint on anything. All three signals evaluated so far were classified
DEAD on the same condition, the Deflated Sharpe threshold, meaning each cleared the
economic-relevance bar and at least two of five regimes, but none produced a result
distinguishable from what selection bias alone would generate given eight candidates.

## Results

Three of eight pre-registered signals have been implemented and evaluated, using gold
futures front-month data from January 2006 through June 2026. The Deflated Sharpe Ratio
in the table below is computed at N = 8, the actual trial count recorded in the ledger,
rather than the count of signals graded to date.

```
signal                IS   gross     net    @4bp    turn   HAC t     DSR   reg  verdict
ma_cross           0.311   0.527   0.523   0.518    4.05    1.47   0.503   4/5  DEAD
ts_momentum        0.200   0.517   0.507   0.496   11.34    1.42   0.482   3/5  DEAD
seasonality        0.431   0.317   0.310   0.303    2.96    0.86   0.289   4/5  DEAD
```

IS and net refer to the Sharpe ratio over the development and evaluation periods
respectively, with the net figure computed on data that was not examined during
development. The @4bp column repeats the evaluation under double the assumed trading
cost. Turn reports annualized turnover in position-units traded per year. HAC t is the
Newey-West t-statistic described above, and reg reports how many of the five
pre-registered regimes had a positive mean return. The complete report, including a
per-regime breakdown for each signal and generated by `scripts/run_gauntlet.py` rather
than compiled by hand, is available at `reports/graveyard.md`.

The difference between gross and net Sharpe is under 0.01 in all three rows, and doubling
the assumed cost to the 4 basis point stress case changes no signal's verdict; at zero
trading cost, all three would still fall short of the Deflated Sharpe threshold. This
distinction is worth stating explicitly, since a result eliminated by transaction costs
would represent a solvable engineering problem, whereas a result that cannot be
distinguished from having tested eight candidates and reported the best one does not.

**`ma_cross`**, the 50/200-day simple moving-average crossover (Deflated Sharpe 0.503,
positive in 4 of 5 regimes):

| Regime | n | Ann. mean | Sharpe |
|---|---|---|---|
| bull_run (2006 to 2011) | 1229 | +0.1292 | +1.220 |
| bear_2013 (2011 to 2015) | 1088 | -0.0356 | -0.340 |
| range_recov (2016 to 2019) | 1003 | +0.0053 | +0.051 |
| covid_spike (2020) | 253 | +0.1423 | +1.165 |
| modern (2021 to 2026) | 1380 | +0.0350 | +0.325 |

**`ts_momentum`**, the sign of the trailing 252-day return (Deflated Sharpe 0.482,
positive in 3 of 5 regimes):

| Regime | n | Ann. mean | Sharpe |
|---|---|---|---|
| bull_run | 1176 | +0.1086 | +1.014 |
| bear_2013 | 1088 | -0.0034 | -0.032 |
| range_recov | 1003 | -0.0486 | -0.474 |
| covid_spike | 253 | +0.1423 | +1.165 |
| modern | 1380 | +0.0427 | +0.397 |

**`seasonality`**, long positions held in September and January (Deflated Sharpe 0.289,
positive in 4 of 5 regimes):

| Regime | n | Ann. mean | Sharpe |
|---|---|---|---|
| bull_run | 1368 | +0.0348 | +0.847 |
| bear_2013 | 1088 | -0.0032 | -0.076 |
| range_recov | 1003 | +0.0082 | +0.210 |
| covid_spike | 253 | +0.0174 | +0.457 |
| modern | 1380 | +0.0184 | +0.390 |

## Limitations

**Signal coverage is 3 of 8.** `carry`, `cot_contrarian`, `real_yield_dev`,
`gold_silver_ratio`, and `dollar_trend` are registered against the signal contract but
each raises `NotImplementedError`, pending data loaders that have not yet been built for
term structure, CFTC COT releases, TIPS real yields, silver, and the dollar index
respectively. Two of the five involve an open question beyond the missing loader:
`carry` may not be constructible at all from front-month-only data, and
`gold_silver_ratio` is a spread trade that the current single-asset engine cannot express
without extension.

**The futures series is not roll-adjusted.** The `ratio_back_adjust` function in
`data/roll.py` is a stub. A continuous series spliced together from expiring contracts
carries a price gap at each roll that no position could actually have earned, and because
gold trades in contango most of the time, that gap is systematically negative. This is
only partially bounded at present: the fifteen largest daily moves in the current series
all correspond to identifiable macroeconomic events, the 2008 crisis, the April 2013
crash, and the COVID spike, rather than to periodic roll gaps, suggesting the vendor's
own splice method is not introducing large jumps on its own. Every figure reported here
nonetheless measures gold plus a residual, unquantified artifact until roll adjustment is
implemented against genuine per-contract data.

**Vendor price data contains 230 corrupt bars**, 114 with a closing price above the
session high and 116 with a closing price below the session low, concentrated between
2006 and 2011. This is bounded in direction though not in magnitude: an erroneous price
adds noise to the return series, which raises its variance and therefore lowers both the
Sharpe ratio and the Deflated Sharpe Ratio, so these errors could make a genuinely
profitable signal appear worse but could not manufacture the roughly 0.45 of additional
Deflated Sharpe a currently dead signal would need to cross the 0.95 threshold. No second
price source is yet available for cross-validation.

**There is no capacity or market-impact model.** Trading cost is modeled as a flat spread
applied to turnover, with no term for order size relative to available volume. This
appears immaterial for the three signals evaluated so far, whose turnover ranges from
2.96 to 11.34 units per year and whose verdicts are unchanged at double the assumed cost,
but it would become material for a higher-turnover candidate or at meaningful trading
size.

**`engine/metrics.py`'s `summarize` and `max_drawdown` functions are stubs.** The Sharpe
ratio, which is used throughout this document, is implemented and tested; the
consolidated performance summary and maximum drawdown calculation are not.

**Walk-forward validation is a stub**, in `engine/backtest.py`. It is required only for
signals that estimate a parameter from data, such as the rolling regression coefficient
in `real_yield_dev`, rather than applying a fixed rule, and its absence currently prevents
those signals from being evaluated even once their data loaders exist.

**The Deflated Sharpe Ratio has no independent cross-check.** A bootstrap procedure or
comparable method would remove the project's current dependence on a single statistical
technique for its central claim.

**Test suite: 24 tests collected, 23 passing, 1 failing.** The failing test,
`test_roll.py::test_unadjusted_stitch_is_detected`, exercises `verify_no_roll_artifacts`,
which is itself unimplemented. It is left failing rather than marked as skipped, in
keeping with the project's convention against weakening a test in order to make it pass.

### Planned work, in priority order

1. Mask the corrupt bars and rerun the evaluation to confirm the Sharpe ratios move
   negligibly. This is inexpensive and would close the most immediate open question
   about the underlying data.
2. Implement `gold_silver` and `dollar_trend`, both of which require only price data
   already accessible, making them the least costly way to extend signal coverage from
   3 to 5.
3. Load a second price source, the London PM fix series available through FRED, for
   cross-validation against the primary vendor feed.
4. Build walk-forward validation. This is the highest-value methodological addition
   remaining, since it removes the dependence on a single in-sample/out-of-sample split
   and is a prerequisite for every fitted signal.
5. Implement `real_yield_dev`, `cot_contrarian`, and then `carry`, once their respective
   data loaders and walk-forward validation are both available.
6. Add a bootstrap or comparable independent check on the Deflated Sharpe Ratio.
7. Implement proper per-contract roll adjustment and load the full futures curve. This
   would unlock the `carry` signal and remove the project's last significant data
   artifact, but it depends on a paid per-contract data feed such as Databento, which is
   why it is last in this list despite underlying much of what precedes it.

Multi-asset or cross-sectional testing, non-directional trades, and intraday execution
are explicitly out of scope; each would constitute a distinct project rather than an
extension of this one.

## Data sources

Gold (`GC=F`), silver (`SI=F`), and the dollar index (`DX-Y.NYB`) are sourced through
`yfinance`. The 10-year TIPS real yield (`DFII10`) is sourced from FRED. The CFTC's
disaggregated Commitments of Traders report supplies the positioning signal. All sources
are free of charge and cached to Parquet under `data/cache/` on first use; the cache
directory is excluded from version control and can be reproduced with `fetch_data.py`.

## Repository layout

```
src/goldgraveyard/
  types.py        signal contract: DataFrame -> position in [-1, +1], nothing else
  data/           loaders and Parquet cache (Yahoo, FRED, CFTC COT); roll adjustment (stub)
  engine/         backtest pipeline, vol targeting, costs, metrics
  signals/        one file per signal, registered explicitly through a decorator so the
                  trial count feeding the DSR cannot silently drift from signals run
  stats/          Newey-West HAC, Deflated Sharpe, regime stability
  report/         verdict adjudication and graveyard table generation
scripts/          run_gauntlet.py is the entry point; also fetch_data.py, overfit_demo.py
tests/            24 tests: engine invariants including the lookahead check, cache
                  correctness, statistics
BUILD_LOG.md      dated log of what was built, why, and every decision and mistake
```

The project targets Python 3.13 and is managed with `uv`. `pandas` and `numpy` handle the
data plane, `statsmodels` provides HAC inference, `scipy.stats` supports the Deflated
Sharpe Ratio's non-normal correction, `pyarrow` backs the Parquet cache, `yfinance` and
`pandas-datareader` handle data ingestion, and `pytest` and `ruff` handle correctness and
linting.

```bash
uv sync
uv run pytest
uv run python scripts/run_gauntlet.py
```

`run_gauntlet.py` runs every implemented signal through the identical pipeline, applies
the verdict rule, and writes `reports/graveyard.md`; no computation of consequence
happens outside this path. Market data is downloaded once and cached to Parquet, so a
subsequent run is offline and produces byte-identical output.

## Further reading

- [CONCEPTS.md](CONCEPTS.md): the mathematical background at course register, covering
  the return identity through volatility targeting, Newey-West inference, and the
  Deflated Sharpe Ratio, each accompanied by a worked example drawn from this project's
  own data.
- [LIMITATIONS.md](LIMITATIONS.md): the complete detail behind the summary above,
  including the reasoning for why each caveat does or does not affect the current
  verdicts.
- [BUILD_LOG.md](BUILD_LOG.md): a dated entry for every decision made over the course of
  this project, including decisions that were later found to be wrong.
