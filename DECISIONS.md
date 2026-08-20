# Pre-Registration

**This file is committed before any result is computed, and every entry is frozen.**

The value of this project rests entirely on the claim that nothing here was chosen
after seeing performance. That claim is only credible if the choices are timestamped
in git history *before* the results are. If you change something below, do not edit
the line: add a dated amendment at the bottom saying what changed and why, and
accept that an amendment made after seeing results invalidates the finding.

---

## 1. Sample

| Item | Value | Why |
|---|---|---|
| Start | `2006-01-01` | First year of CFTC disaggregated COT data; using it for all signals keeps the graveyard apples-to-apples |
| End | `2026-06-30` | Fixed end date so re-runs are reproducible |
| Instrument | COMEX gold futures, front month, **ratio back-adjusted** | |
| Calendar | NYMEX gold trading days | |
| IS / OOS split | first **60 %** / last **40 %**, split date computed from the above and never re-chosen | |

## 2. Engine parameters (frozen)

| Parameter | Value | Location |
|---|---|---|
| Execution lag | 1 bar | `engine/backtest.py: EXEC_LAG_BARS` |
| Target annual vol | 10 % | `engine/sizing.py: TARGET_ANNUAL_VOL` |
| Vol estimate window | 60 days, strictly causal | `engine/sizing.py: VOL_LOOKBACK_DAYS` |
| Vol floor | 4 % annualized | `engine/sizing.py: VOL_FLOOR` |
| Max leverage | 3.0× | `engine/sizing.py: MAX_LEVERAGE` |
| Base cost | 2 bps round-trip | `engine/costs.py: DEFAULT_COST_BPS` |
| Stress cost | 4 bps round-trip | `engine/costs.py: STRESS_COST_BPS` |
| Returns | simple, not log | `types.py` |

## 3. Signals and their frozen parameters

| # | Name | Hypothesis stated in advance | Frozen params |
|---|---|---|---|
| 1 | `ts_momentum` | 12m return predicts next month's sign | lookback 252d |
| 2 | `carry` | Curve slope predicts return | near vs. deferred roll yield |
| 3 | `cot_contrarian` | Crowded managed money reverts | 156-week z-score, clipped ±2 |
| 4 | `real_yield_dev` | Gold reverts to its TIPS relationship | 500d rolling OLS, walk-forward |
| 5 | `gold_silver_ratio` | Ratio mean-reverts | 252d z-score, clipped ±2 |
| 6 | `ma_cross` | Trend persists | 50 / 200 |
| 7 | `seasonality` | Sep and Jan are strong | months (1, 9), chosen from folklore not data |
| 8 | `dollar_trend` | Past USD trend predicts gold | 60d DXY change |

## 4. Regimes (chosen on gold market history, not on strategy performance)

| Regime | Window |
|---|---|
| Bull run into the 2011 top | 2006-01-01 → 2011-09-05 |
| Post-top bear | 2011-09-06 → 2015-12-31 |
| Range and recovery | 2016-01-01 → 2019-12-31 |
| COVID spike | 2020-01-01 → 2020-12-31 |
| Modern | 2021-01-01 → 2026-06-30 |

## 5. The verdict rule

> A signal is **ALIVE** if and only if **all three** hold:
> 1. Out-of-sample mean return, **net of 2 bps costs**, is positive;
> 2. **Deflated Sharpe Ratio > 0.95**, with `n_trials` equal to the honest total in §6;
> 3. Mean-return **sign is positive in at least 2 of the 5 regimes**.
>
> Everything else is **DEAD**. The cause of death is the *first* condition it failed.

No appeals. A signal that misses by a hair is dead; that is what a pre-registered
threshold means.

## 6. Trial ledger, the honesty tax

The Deflated Sharpe needs the number of trials actually run. Undercounting it is the
one way to defeat the whole correction without noticing.

### What counts as a trial

A **distinct strategy configuration that was a candidate to become the reported
result.** This is narrower than an execution count, and the distinction decides the
number:

| Situation | Trials | Why |
|---|---|---|
| One signal run at 2 bp and again at 4 bp | **1** | Same strategy. A cost sensitivity check, not a candidate |
| One signal evaluated in sample and out of sample | **1** | Same strategy, two views of it |
| Eight distinct signals, each a genuine candidate | **8** | Eight candidates |
| Four moving average pairs tried, best one kept | **4** | A selection was made among them |
| `50/200` fixed in advance from folklore, never varied | **1** | No selection took place |
| Cheat signals used for lookahead verification | **0** | Never candidates. Diagnostics, not strategies |
| Overfitting sidecar grid search | **0 here** | A separate exercise, carrying its own Deflated Sharpe |

The weighting is toward **parameter searches**. A search over 100 moving average pairs
is 100 trials even though it is one line of code, because the selection among them is
exactly what the correction exists to penalise.

### Ledger

| Date | What was run | Trials | Notes |
|---|---|---|---|
| 2026-08-21 | The eight registered signals, each frozen at parameters chosen in advance | **8** | `ma_cross` implemented so far. Parameters fixed in section 3 before any result, so no selection occurred within any signal |
| 2026-08-21 | `ma_cross` at 2 bp and 4 bp | 0 | Cost sensitivity of an existing candidate |
| 2026-08-21 | `ma_cross` in sample and out of sample | 0 | Two views of one candidate |
| 2026-08-21 | Perfect-foresight cheat signals, engine verification | 0 | Diagnostics. Never candidates for the report |
| **Running total** | | **8** | |

**If any parameter is ever varied and the better result kept, every setting tried is
added here**, including the ones that looked bad, on the day it happens rather than
afterwards.

## 7. Amendments

*(none yet: append dated entries below, never edit above)*
