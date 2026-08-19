# The Gold Signal Graveyard

## What this is

People invent rules for trading. *Buy gold when its price rises above the average of the
last 200 days.* *Buy gold when the dollar has been falling.* *Buy gold in September,
because Indian wedding season drives physical demand.* A rule like this is called a
**signal**: it looks at data available today and outputs a decision to be long (betting
the price rises), short (betting it falls), or flat.

To find out whether a signal works, you run it over historical prices and compute what it
would have earned. That is called a **backtest**.

**The problem is that most backtests are wrong.** Not fraudulent, and usually not even
careless. They are wrong in a handful of specific, well documented, technical ways that
each make a worthless rule look profitable, and that produce no error message when they
happen. The backtest returns an attractive number, the number is meaningless, and nothing
about the output indicates which of the two you are looking at.

There are five failure modes that account for most of it:

1. **The strategy uses information it could not have had.** If a rule decides today's
   position using today's closing price, it is trading on information that arrives after
   the decision. This is called lookahead bias, and it is the most destructive because it
   is invisible: the code runs fine and simply reports a better result.
2. **Trading costs are ignored.** Every time a position changes you pay a spread and a
   commission. A rule that trades constantly can be profitable before costs and
   comfortably unprofitable after them.
3. **Many rules were tried and only the best is reported.** Test twenty worthless rules
   and the luckiest one will look good, because the maximum of twenty noisy measurements
   is not centred on zero. Reporting that one is reporting noise with confidence.
4. **Rules are compared at different bet sizes.** A mediocre rule betting large will
   out-earn an excellent rule betting small. Comparing returns without equalizing risk
   measures who bet bigger, not who predicted better.
5. **The price series itself is constructed wrongly.** Gold futures contracts expire, so
   any long price history is spliced together from many contracts. Splice them naively
   and you introduce price jumps at every join that no trader could have captured, which
   in gold are systematically negative and look exactly like a real market phenomenon.

## What this project does about it

This repository builds one evaluation framework in which those failure modes are
**structurally impossible rather than merely avoided**, and then runs eight signals that
gold traders genuinely believe in through it.

Structurally impossible means the protections live in shared engine code that every
signal is forced through, not in each signal's own implementation. A signal in this
project can only return a direction: long, short, or flat. It cannot choose its own bet
size, it cannot control when its decision is executed, and it cannot exempt itself from
transaction costs. The engine applies a one bar execution delay, scales every signal to
the same 10% annual risk, and charges costs identically for all of them. So the claim
"these eight were compared fairly" is a property of the architecture, and not a promise
about how carefully the author worked.

On top of that sits a statistical gauntlet that every signal must survive: standard
errors that account for the fact that strategy returns are not independent observations,
a correction for how many strategies were tested to find the reported one, and a check
that the result holds across different market conditions rather than coming entirely from
one stretch of history.

Every parameter that could have been tuned was written down and frozen before any result
was computed, in [DECISIONS.md](DECISIONS.md), which is committed to git so that the
timestamps are checkable. That includes the cost assumption, the risk target, every
signal's parameters, the five market regimes, the date at which the data is split into
development and evaluation halves, and the exact rule for declaring a signal alive or
dead.

## Why a negative result is the goal

**The deliverable is not a profitable strategy. It is the framework, and the demonstrated
willingness to use it on your own ideas.**

If seven of the eight signals turn out to be worthless, this project has succeeded. The
skill being demonstrated is the ability to distinguish a real result from an artifact and
to say so plainly when the answer is that something does not work. That is a more useful
thing to be able to do than to have found a rule that appears to make money, because the
second is easy to fake and the first is not.

So far, three signals have been implemented and judged. None survived.

---

## Results so far

Three of the eight signals have been implemented and put through the full gauntlet. Gold
futures, January 2006 to June 2026.

```
signal                IS   gross     net    @4bp    turn   HAC t     DSR   reg  verdict
ma_cross           0.311   0.527   0.523   0.518    4.05    1.47   0.503   4/5  DEAD
ts_momentum        0.200   0.517   0.507   0.496   11.34    1.42   0.482   3/5  DEAD
seasonality        0.431   0.317   0.310   0.303    2.96    0.86   0.289   4/5  DEAD

0 of 3 survived.
```

Reading the columns: **IS** is the Sharpe ratio over the development period and **net**
is the Sharpe over the evaluation period, which was untouched during development. The
Sharpe ratio is return divided by risk, so it is unaffected by how large the bets were.
**@4bp** repeats the evaluation at double the assumed trading cost. **turn** is turnover,
the amount of position traded per year. **HAC t** is a t-statistic computed with standard
errors that do not assume independent observations. **DSR** is the Deflated Sharpe Ratio,
explained below. **reg** counts how many of five market regimes had a positive mean
return.

The full report, with a written autopsy and a regime by regime breakdown for each signal,
is at **[reports/graveyard.md](reports/graveyard.md)**. It is generated by
`scripts/run_gauntlet.py` rather than written by hand.

### Trading costs are not what killed these signals

This is worth separating out, because "the strategy was eaten by fees" and "the pattern
was never there" are different findings with different implications.

The gap between the gross and net columns is under a hundredth of a Sharpe ratio in all
three cases, and doubling the cost assumption from 2 to 4 basis points changes no
verdict. If trading were free, all three would still be dead. These are not edges
consumed by implementation friction, which would be a solvable engineering problem. They
are patterns that cannot be distinguished from having tested eight things and reported
the best one.

### The number that makes the point

`ma_cross`, the 50 and 200 day moving average crossover, produced an out-of-sample Sharpe
ratio of **0.523** across nearly eight years of data it never saw during development.
Taken alone that is a respectable figure and it would pass most informal standards.

Now consider the same return series, unchanged, evaluated against different honest counts
of how many strategies were tried before this one was reported:

| Trials tested | Deflated Sharpe | Reading |
|---|---|---|
| 1 | 0.927 | looks good |
| 4 | 0.659 | |
| **8** | **0.503** | the honest count |
| 16 | 0.370 | |
| 50 | 0.211 | |

The Deflated Sharpe Ratio answers a specific question: given that some number of
strategies were tested, what is the probability that this one is genuinely better than
zero rather than being the luckiest of the batch? It works by computing how good the best
of N worthless strategies would be expected to look, and then asking whether the observed
result clears that bar.

**Nothing about the strategy changes between those rows.** The returns are identical. The
only thing that varies is how honestly the number of attempts is being counted. At one
trial the result looks convincing; at fifty it is plainly noise.

For eight trials the bar that luck alone would clear is a Sharpe ratio of 0.520.
`ma_cross` produced 0.523. It beat the luckiest of eight coin flippers by three
thousandths of a Sharpe ratio, across eight years of data.

The trial count is the one input in this entire framework that cannot be verified by
someone outside the project. There is no way to audit how many ideas were quietly tried
and discarded. That is precisely why the ledger in [DECISIONS.md](DECISIONS.md) is dated
and was filled in before these numbers were computed, rather than reconstructed
afterwards.

## How the framework prevents each failure mode

| Failure mode | Where it is prevented |
|---|---|
| Same-bar signal and execution | [`engine/backtest.py`](src/goldgraveyard/engine/backtest.py), one-bar lag applied in shared code so no signal can opt out |
| Comparing unequal risk | [`engine/sizing.py`](src/goldgraveyard/engine/sizing.py), every signal vol-targeted to 10% |
| Lookahead in the volatility estimate | [`engine/sizing.py`](src/goldgraveyard/engine/sizing.py), a second independent `.shift(1)` inside `realized_vol` |
| Ignored transaction costs | [`engine/costs.py`](src/goldgraveyard/engine/costs.py), charged on the sized position, reported at 2 bp and 4 bp |
| Autocorrelation inflating t-stats | [`stats/hac.py`](src/goldgraveyard/stats/hac.py), Newey-West standard errors |
| Multiple testing | [`stats/deflated_sharpe.py`](src/goldgraveyard/stats/deflated_sharpe.py) |
| Single-regime fragility | [`stats/regimes.py`](src/goldgraveyard/stats/regimes.py), five windows frozen in advance |
| Un-adjusted futures roll | [`data/roll.py`](src/goldgraveyard/data/roll.py), **not yet implemented** |

### The engine is verified adversarially, not by inspection

Reading code and concluding that it has no lookahead is not evidence, because lookahead
is specifically the class of bug that reads as correct. So the engine is tested by
attacking it.

The test constructs a deliberately cheating signal, one that already knows the current
day's return and bets accordingly, and asserts that the engine extracts approximately
nothing from it. Run through the pipeline with the execution delay in place, that signal
earns a Sharpe ratio of **-0.256**. Remove the delay, and the identical signal earns
**+16.509**.

That gap is what the protection is worth, and it is also a useful reference point: a
Sharpe ratio of 16 is what a lookahead bug actually looks like in this dataset. The test
is permanent and runs with the rest of the suite.

## The verdict rule, frozen before any result

> **ALIVE** requires all three:
> 1. positive out-of-sample return, net of costs;
> 2. Deflated Sharpe above 0.95;
> 3. mean return positive in at least 2 of 5 regimes.
>
> Everything else is **DEAD**. Cause of death is the first condition failed.

There are no appeals and no borderline cases. A signal that misses a threshold narrowly
is dead, because the alternative is deciding after the fact that a threshold was too
strict, which would make the whole exercise unfalsifiable. A rule that can be relaxed
once its result is known provides no evidence about anything.

The same logic applies in the other direction. During development it became clear that
condition 3 is weaker than intended: because a trend following signal that is long most
of the time inherits gold's own regime pattern, almost any long biased signal passes it.
That weakness was documented rather than fixed, because tightening a condition after
seeing that it passed something too easily is the same act as loosening one after seeing
it fail.

## Running it

```bash
uv sync
uv run pytest
uv run python scripts/run_gauntlet.py
```

`run_gauntlet.py` is the front door. It runs every implemented signal through the
identical pipeline, applies the verdict rule, prints the table, and writes
`reports/graveyard.md`. Nothing of consequence is computed anywhere else.

Market data is downloaded once and cached to Parquet, so a second run is offline and
byte-identical.

## Layout

```
src/goldgraveyard/
  types.py        the signal contract: DataFrame -> position in [-1, +1], nothing else
  data/           loaders and caching; futures roll adjustment (stub)
  engine/         backtest pipeline, vol targeting, costs, metrics
  signals/        one file per signal, self-registering
  stats/          Newey-West, Deflated Sharpe, regime stability
  report/         verdict adjudication and the graveyard table
scripts/          run_gauntlet.py is the entry point
tests/            24 tests: engine invariants, cache correctness, statistics
DECISIONS.md      pre-registration: frozen parameters, regimes, verdict rule, trial ledger
BUILD_LOG.md      what was built, why, and every decision and mistake along the way
```

## Honest status

| Piece | State |
|---|---|
| Backtest engine | working, documented, adversarially tested |
| Statistical gauntlet | complete: HAC, Deflated Sharpe, regime stability |
| Verdict adjudication and report | working, generates `reports/graveyard.md` |
| Signals implemented | 3 of 8: `ma_cross`, `ts_momentum`, `seasonality` |
| Futures roll adjustment | **not implemented** |
| Overfitting sidecar | not started |
| One-page summary | not started |

The remaining five signals each need a data source the project does not yet load. Two
carry known complications: `carry` may be unbuildable from free front-month-only data,
and `gold_silver_ratio` is a spread trade the current single-asset engine cannot express.

Tests: 23 passing, 1 failing. The failure is the roll adjustment detection check, which
is red because the function it tests is a stub.

## What these numbers rest on

Stated here rather than buried, because a result reported without its caveats is the
failure mode this project exists to argue against.

- **The futures series is not roll-adjusted.** A continuous gold series spliced from
  expiring contracts carries a phantom price gap at every roll, systematically negative
  under contango, that no position could have earned. Until this is fixed, every figure
  above measures gold plus an artifact.
- **Yahoo's early gold data is corrupt.** 114 bars have a close above the session high
  and 116 below the low, concentrated in 2006 to 2011.
- **Condition 3 is weak and partly measures gold rather than the signal.** Gold's own
  returns are positive in the same 4 of 5 regimes, so any long-biased signal tends to
  pass it.

None of these is being quietly repaired. A documented weakness is a finding; a silently
patched one is a fabrication.

## Data

All free. Gold `GC=F`, silver `SI=F`, dollar index `DX-Y.NYB` via yfinance; 10-year TIPS
`DFII10` via FRED; CFTC disaggregated Commitments of Traders for the positioning signal.
