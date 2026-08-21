# Build Log

A running, plain-language record of everything built in this repo, why it was built
that way, and what was decided along the way.

**Who this is written for:** someone who knows how to program but has never seen this
project, does not know futures markets, and was not present for any of the
conversations. Every entry should be readable on its own. Jargon gets defined the
first time it appears.

**Calculations are explained where they are introduced**, in the entry that built
them: formula, units, frozen parameters, and a worked example, alongside the reasoning
for why it is computed that way.

**Convention:** newest entry at the bottom. Every working session appends an entry.
Entries record *decisions and reasoning*, not just "changed file X": git already
records that.

---

## Background: what this project actually is

Before any entry makes sense, three things need defining.

**Gold futures.** A futures contract is an agreement to buy or sell something at a
set price on a set future date. Gold futures trade on COMEX under the ticker `GC`.
Crucially, a futures contract *expires*. There is no single continuous "gold futures
price": there is a December 2026 contract, a February 2027 contract, and so on. The
"front month" is whichever contract is nearest to expiry and therefore most heavily
traded. To get a multi-year price history you have to stitch many contracts together,
and how you stitch them is a major source of bugs (see Entry 5's open question).

**A trading signal.** A rule that looks at data available today and outputs a
position: go long (bet the price rises), go short (bet it falls), or stay flat. For
example: "be long if the price is above its 200-day average." A *backtest* runs that
rule over historical data to see what it would have earned.

**What this project is testing.** Eight signals that gold traders widely believe in.
The goal is *not* to find one that makes money. The goal is to build an evaluation
framework rigorous enough that we can trust the answer either way, and then honestly
report which signals survive it and which don't. If seven of eight die, the project
succeeded. The framework is the deliverable; the signals are the test subjects.

The reason this is worth building: it is very easy to produce a backtest that looks
profitable and is entirely an artifact of a bug or of statistical luck. Most of the
engineering in this repo exists to make specific, well-known failure modes impossible
rather than merely unlikely.

---

## Entry 1: 2026-08-20: Environment and toolchain

### What was there before

The machine had exactly one Python: the macOS system Python, version 3.9.6. It had
accumulated packages installed directly into it (`fastapi`, `pandas`, `groq`, and
about forty others). Python 3.9 reached end-of-life in October 2025.

Two problems with using it:

1. **No isolation.** Every project shares one set of package versions. Project A
   needs pandas 1.x, project B needs pandas 2.x, and one of them breaks. There is no
   record of which packages this project actually needs.
2. **It is the OS's Python.** macOS itself uses it. Installing and upgrading packages
   in it can break system tooling in ways that are hard to diagnose.

### What was installed

**`uv`** (version 0.12.5), via Homebrew. `uv` is a Python package and version manager
it does the job of `pip`, `venv`, and `pyenv` in one tool, and it is roughly an
order of magnitude faster than pip because it is written in Rust and caches
aggressively.

What it does for this project specifically:

- It downloaded and installed **Python 3.13** *for this project only*. The system
  3.9.6 is untouched and no longer involved.
- It created a virtual environment at `.venv/` inside the repo. A virtual environment
  is a private directory holding this project's own Python interpreter and packages,
  so nothing here can affect any other project.
- It wrote **`uv.lock`**, which records the exact version of every package *and every
  package those packages depend on*. This file is committed to git. Anyone who clones
  the repo and runs `uv sync` gets byte-for-byte the same environment. Without a lock
  file, "it worked last month" is not reproducible: a dependency silently updates and
  results change.

### Packages installed

| Package | What it is used for here |
|---|---|
| `pandas` | The core data structure. A `DataFrame` is a table with labelled rows and columns; here rows are trading dates and columns are prices. |
| `numpy` | Numerical arrays; pandas is built on it. |
| `scipy` | Statistical distributions: needed for the normal-distribution math in the Deflated Sharpe calculation. |
| `statsmodels` | Regression with Newey–West standard errors (explained in Entry 3). |
| `matplotlib` | Charts for the final report. |
| `pyarrow` | Reads and writes the Parquet file format (explained in Entry 5). |
| `yfinance` | Downloads free market data from Yahoo Finance. |
| `pandas-datareader` | Downloads economic data from FRED, the St. Louis Fed's public database. |
| `requests` | HTTP, for fetching CFTC data files directly. |

Development-only (not needed to run the project, only to work on it): `pytest` for
tests, `ruff` for linting and formatting, `jupyterlab` for exploratory notebooks.

### How to use it

`uv run <command>` executes a command inside the project environment. You never
activate anything manually and you never type `pip install`:

```bash
uv sync                    # install exactly what uv.lock specifies
uv run pytest              # run the tests
uv run python script.py    # run a script
uv add somepackage         # add a dependency and update the lock file
```

### Decision recorded

Chose `uv` over the more familiar `python -m venv` + `pip install -r requirements.txt`.
**Cost:** a new tool to learn and slightly different commands. **Benefit:** a real
lock file, which plain `requirements.txt` does not give you: it pins direct
dependencies but not their dependencies, so environments still drift.

---

## Entry 2: 2026-08-20: Repository structure

Created at `~/Documents/Dev/gold-signal-graveyard`, git-initialised, local only (not
pushed to GitHub: the intent is to push once there is something worth showing).

```
src/goldgraveyard/
  types.py        the contracts every other module obeys
  data/           downloading data, and futures roll adjustment
  engine/         the backtest itself: costs, position sizing, metrics
  signals/        the eight signals, one file each
  stats/          the statistical tests a signal must pass
  report/         generating the final table and charts
scripts/          three entry points, run in order
tests/            automated checks
data/raw/         downloaded data (git-ignored)
data/cache/       processed cached data (git-ignored)
reports/          output
DECISIONS.md      parameters frozen in advance
BUILD_LOG.md      this file
```

### The single most important design decision: the signal contract

Written in `src/goldgraveyard/types.py`. Every signal is a function with this shape:

```
signal(DataFrame) -> Series
```

It receives a table of market data indexed by date, and returns one number per date:
the desired position. `+1` means fully long, `-1` means fully short, `0` means flat.

What a signal is **forbidden** from doing is as important as what it does. A signal
does **not** apply the trading delay, does **not** size the position, and does **not**
subtract trading costs. The engine does all three, identically, for all eight signals.

**Why this matters.** The project's central claim is "these eight signals were
compared fairly." That claim is only true if literally the only difference between
them is the signal logic. If each signal handled its own position sizing, then a
signal could look better simply because it happened to take larger bets, and you
would have no way to tell that apart from genuine predictive skill. Forcing everything
through one code path makes the comparison structurally honest rather than honest by
good intentions.

### Why every function is currently unimplemented

There are 41 functions defined across `src/` and `scripts/`. 38 of them consist of a
docstring and `raise NotImplementedError`. The remaining 3 are the small decorator
that lets a signal register itself.

This is deliberate. The signatures and docstrings are the *specification*: they
record what each piece must do and which bug it exists to prevent. They get filled in
one at a time. Nothing in this repo produces a number yet.

### Why the tests currently fail

`tests/` contains 11 tests. 10 fail with `NotImplementedError` and 1 passes. This is
the intended state: the tests were written first, and they describe correct behaviour
that does not exist yet. They go green one at a time as functions get implemented.

The single passing test is `test_lag_is_exactly_one_bar`, which only checks that a
constant equals 1: it needs no implementation.

The most important failing test is `test_execution_lag_kills_same_bar_foresight`. It
hands the engine a deliberately cheating signal that already knows today's return, and
asserts that the engine makes approximately **zero** money from it. If the engine is
built correctly, the one-day trading delay destroys the cheat. If that test ever
passes trivially or the engine shows a large profit there, information is leaking from
the future into the backtest: the most common and most destructive bug in this
domain.

**Commit:** `2df22bf`: "Scaffold: pre-registration, engine skeleton, and red test suite"

---

## Entry 3: 2026-08-20: The pre-registration document, and a correction

### What DECISIONS.md is

A "pre-registration" is a term borrowed from clinical trials. Before running the
experiment, you write down publicly what you are going to measure and what counts as
success, so you cannot later change the goalposts to match whatever result you got.

`DECISIONS.md` does that here. It fixes, in advance:

- the date range of the study, and where the in-sample/out-of-sample split falls
- every numeric parameter of the engine (trading cost, risk target, lookback windows)
- the parameters of all eight signals
- the five market "regimes" the results get broken down by
- the exact rule for declaring a signal alive or dead
- a ledger of how many strategy variants have been tested in total

It is committed to git *before* any result exists. Git history is what makes the
"nothing was tuned after seeing the results" claim checkable rather than just asserted.

### The verdict rule

> A signal is **ALIVE** only if all three hold:
> 1. Its out-of-sample return, after subtracting trading costs, is positive;
> 2. Its Deflated Sharpe Ratio exceeds 0.95;
> 3. Its return is positive in at least 2 of the 5 market regimes.
>
> Everything else is **DEAD**, and the cause of death is the first condition it failed.

Three terms in there need defining:

- **Out-of-sample.** The history is split: the first 60% is used for building and
  checking, the last 40% is set aside and evaluated once, at the end. A rule that
  works on data you developed it against proves nothing, you may simply have
  described the noise in that particular stretch of history. Out-of-sample data is the
  only real test.
- **Sharpe Ratio.** Average return divided by volatility, annualised. It measures
  return earned per unit of risk taken, so strategies of different sizes can be
  compared.
- **Deflated Sharpe Ratio.** A correction for the fact that testing many strategies
  guarantees at least one looks good by pure luck. Explained in the next section.

### The correction that happened here

The first version of `DECISIONS.md` was written by Claude, with every parameter filled
in: cost assumption, risk target, lookback windows, regime dates, split point. Every
*code* function was still an unimplemented stub, so on a narrow reading no
implementation had been written.

Miguel pushed back, and was right to. Choosing the frozen parameters of a study is the
intellectual content of the study. "The function bodies are empty" is a technicality,
not a defense. The same applied to `stats/deflated_sharpe.py`, whose docstring
originally contained the full mathematical formulas: handing over the hardest
derivation in the project.

**Actions taken:**

- The formulas in `deflated_sharpe.py` were removed and replaced with the two
  questions the math has to answer, plus a citation to the source paper: Bailey &
  López de Prado (2014), *"The Deflated Sharpe Ratio"*, Journal of Portfolio
  Management 40(5), pp. 94–107: Section 2 for the Probabilistic Sharpe Ratio,
  Section 3 for the deflation. One trap is flagged but deliberately not resolved:
  pandas' `.kurt()` returns *excess* kurtosis (normal distribution = 0) while the
  paper uses *raw* kurtosis (normal = 3). Getting that backwards shifts every result
  in the same direction, which makes it look plausible rather than obviously wrong.
- `DECISIONS.md` was kept, but **it is currently Claude's draft, not a real
  pre-registration.** It only becomes one once Miguel has reviewed and defended each
  number himself. The three most arguable are the 2 basis-point trading cost, the 10%
  volatility target, and the five regime start/end dates.

**Open item:** DECISIONS.md still needs to be rewritten by Miguel before any result
is computed. Until then it has no evidential value.

**Commit:** `2353e4d`: "Replace DSR formulas with the derivation questions and a paper citation"

### Why "Deflated" Sharpe at all: the problem it solves

Suppose you test 20 completely worthless strategies. Each one's measured Sharpe Ratio
is noise centred on zero, but noise has spread: some come out negative, some
positive. The *best of the 20* will look decent purely because you took a maximum over
20 random draws. Report only that one and you have "found" a strategy that does not
exist.

This project tests 8 headline signals, plus every variant tried during development.
The Deflated Sharpe Ratio quantifies how good the luckiest of N worthless strategies
would look, and requires the observed result to beat that bar. This is why
`DECISIONS.md` section 6 contains a trial ledger: the calculation needs an honest
count of *every* variant ever run, including ones abandoned for looking bad.
Under-counting it is the one way to quietly defeat the entire project.

---

## Entry 4: 2026-08-20: Checking what data is actually available

Before writing any download code, ran a throwaway script to see what Yahoo Finance
actually returns. Findings:

| Symbol | What it is | Rows | History starts |
|---|---|---|---|
| `GC=F` | COMEX gold futures, front month | 6,480 | 2000-08-30 |
| `SI=F` | COMEX silver futures, front month | 6,482 | 2000-08-30 |
| `DX-Y.NYB` | US Dollar Index | 6,690 | 2000-01-03 |

**Consequence for DECISIONS.md:** the frozen start date is 2006-01-01, chosen because
that is when the CFTC's detailed positioning data begins. But price history goes back
to 2000. So the project is voluntarily discarding five years of usable history that
seven of the eight signals could have used, in order to keep all eight running on an
identical window. That is a defensible trade: comparability is the whole point, but
it is a *choice*, and it should be written into DECISIONS.md as one rather than left
looking accidental.

**Open item:** record that reasoning in DECISIONS.md.

---

## Entry 5: 2026-08-20: `load_yahoo`: the first working code

This is the first function in the repo that actually does something.

### What it is, plainly

`load_yahoo` is the function that **gets price data into the project.** It lives in
`src/goldgraveyard/data/loaders.py`. You give it a ticker symbol and a date range, and
it hands back a table of daily prices:

```python
df = load_yahoo("GC=F", "2006-01-01", "2026-06-30")
```

```
                  open        high         low       close  volume
date
2006-01-03  518.599976  528.500000  518.599976  530.700012       7
2006-01-04  533.599976  533.599976  533.500000  533.900024       8
...
```

Each row is one trading day. `open` is the first traded price of the day, `close` the
last, `high` and `low` the extremes, `volume` the number of contracts traded. Every
other part of this project reads its prices through this function.

It is "step 1 of the slice": the first piece of a thin vertical slice through the
whole system, chosen first because everything downstream depends on it.

### What it does, step by step

1. Make sure the cache directory exists.
2. If a cache file for this symbol already exists and covers the requested dates, read
   it from disk and return: no network call.
3. Otherwise download from Yahoo Finance via the `yfinance` package.
4. Clean up the result into the standard shape (details below).
5. Save it to disk as a Parquet file so the next call is free.
6. Return the requested date range.

**What "caching" means here.** The first call takes about 1.5 seconds and hits the
network. It writes the result to `data/cache/yahoo_GC_F.parquet`. Every later call
reads that file instead: 19 milliseconds, no network. This matters for more than
speed: if the code re-downloaded every run, a Yahoo outage or a silent data revision
would mean today's backtest differs from yesterday's for reasons unrelated to any code
change. Caching makes runs reproducible.

**What Parquet is.** A binary columnar file format. Compared to CSV it is much smaller
(the 5,152-row gold history is 180 KB), much faster to read, and: the reason it was
chosen: it *preserves data types*. Save a CSV and every date becomes a string that
has to be re-parsed on load, with the parsing rules being another place bugs hide.
Parquet round-trips a pandas DataFrame exactly. The `pyarrow` package provides the
reader and writer.

### The three problems that had to be solved

**Problem 1: yfinance returns an awkward column structure.**

Modern `yfinance` (1.6.0 here) returns columns as a two-level *MultiIndex*: a column
index with two levels rather than one, so a column is identified by a pair like
`('Close', 'GC=F')` rather than just `'Close'`. It does this even when you request a
single ticker. If you don't flatten it, `df["close"]` raises an error everywhere
downstream.

The fix takes the outer level and discards the ticker level. Notably, it selects that
level **by name** (`"Price"`) rather than by position (`0`). Positional access would
silently break if a future yfinance version reordered the levels, and "silently"
is the operative word: it would produce a valid-looking table of wrong data.

**Problem 2: two nearly identical close columns.**

Called with `auto_adjust=False`, yfinance returns both `Close` and `Adj Close`. For
stocks these differ: `Adj Close` is adjusted for dividends and stock splits. Futures
have neither, so here the two columns are identical. `adj_close` is dropped. Keeping
both would leave every downstream piece of code an undocumented choice between two
columns that look interchangeable but conceptually are not.

**Problem 3: time zones.**

A pandas date index can be "timezone-aware" (each timestamp carries a UTC offset) or
"timezone-naive" (a bare date with no offset). If you try to combine one of each,
pandas either raises an error or, worse, misaligns rows by a day. Since this project
will later join Yahoo price data against FRED economic data, everything is forced to
timezone-naive at the point of loading.

As it happens, on this exact software stack yfinance already returns naive
timestamps, so this never fires, but the normalisation stays in as insurance against
a version change.

### One deliberate departure from the original spec

The spec said: if a cache file exists and `refresh` is False, use it.

That is subtly unsafe, because the cache filename is keyed on the *symbol only*, not
on the date range. Concretely: cache the years 2006–2020, then later widen the study
to 2006–2026. The file exists, so it gets used, and you silently backtest the old
narrower window while believing you widened it. Nothing errors. Nothing looks wrong.

So the implementation checks that the cached data actually *starts early enough* to
cover the request, and re-downloads if it doesn't. Four extra lines. This is precisely
the category of failure the project exists to catch, so it did not seem right to leave
it in the loader.

### Verification performed

```
columns          : ['open', 'high', 'low', 'close', 'volume']
rows             : 5152
range            : 2006-01-03 -> 2026-06-29
index sorted     : True
index timezone   : None  (naive, as required)
missing closes   : 0
duplicate dates  : 0
first call       : 1.52 s  (network)
second call      : 0.019 s (cache; returned an identical table)
cache file       : data/cache/yahoo_GC_F.parquet, 180 KB
```

5,152 rows over 20.5 years is about 251 rows per year, which matches the roughly 250
trading days in a year. That is a sanity check worth doing: a badly wrong row count
would indicate weekend rows, duplicated rows, or a truncated download.

### Status

**Implemented, verified, and committed** as `668c1e1`, "Implement load_yahoo: cached,
normalized daily OHLCV" (+66 lines, −1 in `src/goldgraveyard/data/loaders.py`).

---

## Entry 6: 2026-08-20: Data quality problem found in Yahoo's gold history

While verifying `load_yahoo`, ran an integrity check on the data it returned. By
definition, within a single trading day the closing price must fall between that day's
high and low. It is not a modelling assumption; it is what "high" and "low" mean.

Yahoo's `GC=F` history violates this:

| Impossible condition | Days affected |
|---|---|
| `close > high` | 114 |
| `close < low` | 116 |
| `open > high` | 2 |
| `volume == 0` | 102 |

Worst single case, 2008-09-17: reported high **808.00**, reported close **846.60**,
the close is **$38.60 above the highest price the market supposedly reached that day.**

The corruption is not spread evenly. It is concentrated at the beginning of the
sample:

```
2006: 43    2007: 37    2008: 18    2009: 4    2010: 2    2011: 10
```

### Why this matters

Every one of the eight signals is computed from the `close` column. A close outside
the day's range means that bar is simply wrong. And the densest corruption sits in
2006–2008: exactly the years included to match CFTC data coverage.

### Decision required: currently open

Three options, and this changes a frozen parameter so it is not a judgment call to be
made quietly:

1. **Keep the full window and disclose it** in the final report as a known data
   limitation.
2. **Move the start date to 2009**, where the corruption drops to a handful of days
   per year: at the cost of losing the 2008 financial crisis, which is arguably the
   single most informative regime in the sample.
3. **Add a validation gate** in the loader that detects and either flags or repairs
   impossible bars, and document the repair rule.

**No decision made yet.** This belongs in DECISIONS.md, in its own commit.

**Also open:** whether to turn this integrity audit into a permanent test in `tests/`
so the problem cannot silently reappear or worsen after a re-download.

---

## Entry 7: 2026-08-20: Made the build log a standing rule

Created `CLAUDE.md` at the repo root.

**What that file is.** Claude Code automatically reads a file named `CLAUDE.md`
from the project root at the start of every session and treats its contents as
standing instructions. It is the mechanism for making a convention stick without
having to restate it each time. Nothing else reads it: it has no effect on the
Python code.

**Why it was needed.** Entries 1–6 were written retrospectively, in one batch, after
a session summary used the phrase "we did `load_yahoo`", which meant nothing to
anyone who had not watched it being written. Writing the log after the fact is both
worse (details are already lost) and unreliable (it only happens if someone
remembers). The rule makes it part of doing the work instead.

**What the file says**, in short:

- Append to `BUILD_LOG.md` whenever anything is built, changed, decided, discovered,
  or deliberately deferred: as part of the work, not at the end.
- Write for a reader who programs competently but knows nothing about this project
  or about futures markets. Define domain terms on first use. Do not explain
  programming fundamentals.
- Never write "we did X" without saying what X is and why it exists.
- Record reasoning rather than file diffs: git already stores diffs, and cannot
  recover the reasoning.
- Be explicit when something is unverified, or is Claude's draft rather than
  Miguel's decision.
- Keep the state table and open-items list at the bottom of the log accurate.

It also restates three existing conventions so they are not lost: `DECISIONS.md` is
frozen and amended by dated append rather than edited; every strategy variant tested
goes in the trial ledger; tests are never weakened to make them pass.

**Status:** uncommitted, along with `BUILD_LOG.md` itself.

---

## Entry 8: 2026-08-20: Bug found in the `load_yahoo` cache check (open)

While explaining Entry 5's cache logic, a demonstration exposed a defect in the
already-committed `load_yahoo`.

**Background.** The cache file is named after the symbol only,
`yahoo_GC_F.parquet`, and carries no record of which date range it holds. Entry 5
described adding a "coverage check" so that a cache built for a narrow window is
not silently reused for a wider request.

**The defect.** The check that was written only validates the *start* of the range:

```python
if not cached.empty and cached.index.min() <= want_start:
    return cached.loc[want_start:want_end].copy()
```

Nothing validates the end. Demonstrated against the real loader, with a cache
holding 2006-01-03 to 2020-12-30:

| Case | Requested | Returned | Correct? |
|---|---|---|---|
| A: request starts before cached start | 2005 → 2026 | 2005 → 2026 | yes, refetched |
| B: request starts after cached start | 2006-06 → **2026** | 2006-06 → **2020** | **no** |

Case B is exactly the failure the check was supposed to prevent: ask for data
through 2026, silently receive data through 2020, with no error and no warning.

**Why it was not caught.** The verification in Entry 5 only ever called the
function with a single date range, so the cache was either absent or an exact
match. The mismatch case was never exercised.

**Why the obvious fix is wrong.** Adding `cached.index.max() >= want_end` does not
work. The last row is the last *trading day*: 2026-06-29, while the requested end
is typically a calendar date that may be a weekend, a holiday, or in the future.
That condition would fail on essentially every call and the cache would never be
used.

The fix has to compare the *requested* window against the *previously requested*
window, which means storing the request range alongside the data: in Parquet
schema metadata, or in a small sidecar file: rather than inferring it from the
data itself.

**Status: open, unfixed.** Left for Miguel. Also needs a regression test
reproducing Case B, or the bug can silently return.

---

## Entry 9: 2026-08-20: Fixed the cache bug, and found a second one

### Fix 1: cache coverage (closes Entry 8)

**The approach that does not work.** Adding `cached.index.max() >= want_end` is the
symmetric-looking fix and it is wrong. The last row of the data is the last
*trading day*; the requested end is a *calendar date* that is routinely a weekend,
a holiday, or in the future. That comparison would fail on nearly every call, the
cache would refetch every time, and it would look like it was working.

**The approach taken.** Store the window that was *requested* when the file was
written, in the Parquet file's schema metadata, and compare request against
request. Parquet files carry an arbitrary key/value metadata dictionary alongside
the data; two keys were added, `goldgraveyard.req_start` and
`goldgraveyard.req_end`. The cache is reused only when the stored window contains
the requested window at **both** ends.

Two consequences worth naming:

- **A cache file with no metadata is treated as unusable and refetched.** Files
  written by the previous version have no coverage record, and a cache whose
  coverage cannot be established must not be trusted: trusting it is the bug.
- **A partial hit refetches the UNION of the cached and requested windows**, so
  the cache only ever grows. Fetching just the newly requested window would let
  two callers with overlapping ranges evict each other's data on every call.

The docstring was also rewritten. The old one claimed the cache "is only reused
when it actually spans the requested window", which the code did not do: an
assertion of a guarantee that does not exist is worse than no comment, because it
stops the next reader from checking.

### Fix 2: the end date was off by one

Found while verifying Fix 1. Rebuilding the cache produced 3,773 rows where the
original run produced 3,772, which should not have been possible for the same
window.

**Cause: `yfinance`'s `end` parameter is exclusive.** Confirmed directly:

```
yf.download("GC=F", start="2020-12-01", end="2020-12-31") -> last row 2020-12-30
yf.download("GC=F", start="2020-12-01", end="2021-01-01") -> last row 2020-12-31
```

2020-12-31 was a Thursday and a normal trading day. It was simply being dropped.

This project's API documents its range as `[start, end]`: inclusive at both ends,
and `DECISIONS.md` names 2026-06-30 as the sample end. 2026-06-30 is a Tuesday and
a trading day, and it was missing from every load. The fix passes `end + 1 day` to
yfinance, and the docstring now states the inclusive convention explicitly.

**Impact:** the gold sample went from 5,152 rows ending 2026-06-29 to 5,153 rows
ending 2026-06-30. One row. But it was the *last* row, and it was missing silently
which is the same failure shape as the cache bug: a plausible-looking result
computed on not-quite-the-declared-sample.

### Tests added: `tests/test_loaders.py`, 9 tests, all passing

These do not touch the network. `yf.download` is monkeypatched with a fake that
serves synthetic prices in yfinance's real shape: a `(Price, Ticker)` column
MultiIndex, and, importantly, **reproduces the exclusive-end behaviour**. A test
double that is more convenient than the real thing lets the suite pass while
production breaks.

The fake also counts how many times it was called. That call count is the only way
to assert a cache *hit* actually avoided the network; the returned data looks
identical either way.

| Test | What it pins down |
|---|---|
| `test_exact_repeat_hits_cache` | A repeated identical call does not refetch |
| `test_narrower_request_hits_cache` | A subset of a cached window does not refetch |
| `test_request_extending_past_cached_end_refetches` | **The Entry 8 regression** |
| `test_request_starting_before_cached_start_refetches` | Start-side coverage still works |
| `test_refetch_widens_cache_rather_than_replacing_it` | Union behaviour; no thrashing |
| `test_weekend_end_date_does_not_defeat_the_cache` | A Sunday end date is still covered |
| `test_cache_without_metadata_is_not_trusted` | Old cache files are refetched |
| `test_refresh_forces_network` | `refresh=True` bypasses the cache |
| `test_end_date_is_inclusive` | Fix 2 regression |

### Note on who wrote this

Miguel asked for this one to be written rather than specified. Both fixes and all
nine tests were written by Claude.

---

## Entry 10: 2026-08-20: Volatility targeting (`engine/sizing.py`)

Second and third functions implemented. Written by Claude from a spec Miguel wrote.

### What volatility targeting is, and why the project needs it

**Volatility** here means the standard deviation of daily returns, annualised by
multiplying by sqrt(252): 252 being the approximate number of trading days in a
year. It is the standard measure of how much an asset moves around, and therefore
of how much risk a position in it carries.

The problem it solves: suppose signal A returns 12% a year and signal B returns 6%.
A looks twice as good. But if A was swinging around at 30% volatility and B at 5%,
then B earned more return per unit of risk, and anyone could have turned B into a
20%-return strategy just by trading it six times larger. Comparing raw returns
compares bet *sizes*, not predictive *skill*.

The fix is to scale every signal's position up or down so that all eight run at the
same risk level: 10% annual volatility, frozen in DECISIONS.md. After that, return
differences reflect skill only.

### The input: daily returns

Everything below operates on returns, not prices.

```python
returns = df["close"].pct_change()
```

A return is the percentage change from one closing price to the next, expressed as a
fraction: `0.01` means +1%. On 2020-03-13 gold closed at 1515.7 against the previous
close of 1589.3:

```
(1515.7 - 1589.3) / 1589.3 = -0.04631   ->   -4.63%
```

The first value is `NaN`, since there is no previous day to compare against.

**These are simple returns, not log returns**, and that choice is frozen in
`DECISIONS.md`. Log returns are tempting because they add up cleanly across time, but
they do not combine correctly across *positions*, and every number downstream is
`position × return`. Simple returns keep that multiplication correct. Mixing the two
conventions in one codebase silently corrupts every result, which is why the choice is
frozen rather than left to whoever writes the next function.

### `realized_vol(returns, lookback=60)`

```python
returns.rolling(60).std().shift(1) * np.sqrt(252)
```

Trailing 60-day standard deviation of returns, annualised, **then shifted forward
one day**. Three steps, with the real values for 2020-03-12:

| Step | What it does | Result |
|---|---|---|
| `.rolling(60).std()` | spread of the last 60 daily returns | `0.011138` per day |
| `* np.sqrt(252)` | converts a daily figure to a yearly one | `0.1768` per year |
| `.shift(1)` | makes day *t* use data only through *t−1* | n/a |

**On the √252.** Variance grows roughly linearly with time, so standard deviation
grows with the *square root* of time. There are about 252 trading days in a year, so
converting daily to annual means multiplying by √252. This step changes no decision,
the position sizing would be identical without it, since the target is expressed in the
same units. It exists so the number is comparable to how volatility is quoted
everywhere else.

**On the `.shift(1)`.** That shift is the entire correctness content of the function. A plain rolling
standard deviation computed at day *t* includes day *t*'s own return. But this
number is used to size a position that was decided at the close of day *t*: so
including *t* means the position size was chosen using knowledge of how *t* turned
out. That is lookahead: information from the future leaking into a decision made in
the past. Shifting by one day makes the estimate at *t* depend only on returns
through *t-1*.

This is subtle in a way worth naming: the lookahead is not in the signal. The
signal could be perfectly honest and this would still inflate results, because a
strategy that quietly bets bigger on days it knows will be calm looks skilful.

### `vol_target(raw_position, returns, target=0.10, max_leverage=3.0)`

```python
scale  = target / realized_vol(returns).clip(lower=VOL_FLOOR)
result = (raw_position * scale).clip(-max_leverage, max_leverage)
```

The core of it is one division: the target risk divided by the measured risk. Worked
both ways using real measurements from the sample:

| Conditions | measured vol | division | position |
|---|---|---|---|
| Feb 2019, calm | 7.8% | `0.10 / 0.078` | **1.29 units** |
| Dec 2008, crisis | 45.7% | `0.10 / 0.457` | **0.22 units** |

Calm markets require *more* than a full unit to reach 10% risk; a crisis requires
barely a fifth of one. Frozen parameters: `TARGET_ANNUAL_VOL = 0.10`,
`VOL_FLOOR = 0.04`, `MAX_LEVERAGE = 3.0`.

Two guards:

- **`VOL_FLOOR` (4% annualised) bounds the vol ESTIMATE, not the output.** During an
  unusually quiet stretch the estimate collapses toward zero, and `target/estimate`
  explodes: the position would become enormous precisely *because* nothing had
  moved recently, which is exactly when a shock is most damaging. Flooring the
  denominator stops that before the leverage cap has to.
- **`max_leverage` (3.0x)** is the final backstop on position size.

No `dropna` and no forward-fill. The first 60 values are NaN because no estimate
exists yet, and that absence is information the engine needs; filling it would
invent position sizes for days that had no volatility estimate.

### Verification

Miguel's check, on synthetic returns at ~15.5% volatility:

```
strategy vol : 0.1019     (target 0.10)
```

Near the target but not on it, which is the correct outcome. A causal estimate
always lags a changing volatility regime, so it should miss slightly. Landing on
0.1000 exactly would be evidence of lookahead, not of quality.

**An additional test was run, because "near 0.10" is weak evidence**: a subtly
leaky implementation would also produce a plausible number. The probe perturbs a
single day's return and asks which volatility estimates change:

```
estimate at t=500 changed by : 0.0     (day 500's return does not affect day 500's estimate)
first index that changed     : 501     (influence begins strictly afterwards)
```

That tests the causality property directly, independent of whether the headline
number looks reasonable.

### First live end-to-end run

`load_yahoo` was run against Yahoo with the cache deleted, and its output fed
straight into `vol_target`:

```
df.shape   : (5153, 5)
df.columns : ['open', 'high', 'low', 'close', 'volume']
index      : 2006-01-03 -> 2026-06-30

gold's own annual volatility     : 0.1857
always-long, vol-targeted        : 0.1069     (target 0.10)
leverage range                   : 0.22 to 1.29;  0 days at the 3.0 cap
```

Real data flows through real code and produces a sensible number. This is the first
time anything in the repo has done that.

Note that the very first row of the sample, 2006-01-03, has a close of 530.70
against a high of 528.50: the Entry 6 data corruption, in row one. Still
undecided.

---

## Entry 11: 2026-08-20: Added `CONCEPTS.md`

Created a second document alongside the build log, and a `CLAUDE.md` rule to keep
it fed.

**Why two documents.** They answer different questions. `BUILD_LOG.md` is a diary,
what was done, on which day, and why that choice was made over the alternatives. It
is ordered by time and most of it goes stale as reference material. `CONCEPTS.md` is
a reference: what volatility targeting *is*, what lookahead *is*, which has no
particular date attached and stays useful indefinitely.

Mixing them makes both worse: you cannot skim a diary to look something up, and a
reference cluttered with "on the 20th we decided X" is hard to read.

**What triggered it.** The volatility-targeting explanation took several attempts
before it landed, and what finally worked was not the definition: it was a table of
real numbers from the project's own data, showing gold's calmest day next to its
wildest:

| | gold's daily move | position | resulting risk |
|---|---|---|---|
| Feb 2019 (calm) | 0.42% | 1.29 units | 0.54% |
| Dec 2008 (wild) | 2.22% | 0.22 units | 0.49% |

That explanation existed only in the conversation, which is not somewhere it can be
found again. Hence the file.

**Initial contents:** what the project is doing and why a null result counts as
success; volatility; volatility targeting in full, with the table above; the
distinction between position size and lot size; lookahead and the `.shift(1)`,
including how to detect it; and why price data is cached (reproducibility, not
speed).

**The `CLAUDE.md` rule added:** when a concept is explained and confirmed
understood, write it into `CONCEPTS.md` using the explanation that actually worked,
including the concrete numbers, if numbers are what made it click, rather than a
tidied-up abstract version.

---

## Entry 12: 2026-08-20: `CONCEPTS.md` rewritten at a more basic level

The first version of `CONCEPTS.md` (Entry 11) was written plainly but still assumed
the reader knew what "long", "position", and "return" meant. Miguel's actual
questions were more basic than that: *"so vol_target is just the size of the lot?"*,
*"why are we estimating the volatility for the future?"*, and the file has been
rewritten to match that register. It went from 171 to 518 lines.

**Structural changes:**

- **Part 0, a vocabulary section.** Eight terms defined before anything else: return,
  position, long/short/flat, position size, signal, backtest, volatility, futures
  contract. Nothing later in the file uses a word that has not been defined.
- **Part 3 restructured as the questions actually asked**, rather than as a topic
  outline: what problem is this solving, what is the fix, why does the project need
  it, which function does what, why does the difference matter, is this just the lot
  size.
- **Part 3.5, worked examples**, added on request. Three, smallest first: the single
  multiplication `your return = position × asset return` across five position values;
  the sizing division done by hand for the calm and wild cases; and six real days from
  the March 2020 COVID crash straight out of the code, next to what a fixed 1-unit
  position would have done (worst day −2.84% vs −4.63%).
- **Parts 3.4 and 3.45**, added in response to two further questions.

### The substantive new content: why forecasting volatility is legitimate

Miguel asked why the project forecasts future volatility when its whole thesis is
that forecasting is mostly impossible. That is a sharp question and it deserved
measured evidence rather than assertion. Computed on this project's own gold data:

```python
returns.autocorr(1)                     # -0.0096   direction:  unpredictable
returns.abs().autocorr(1)               # +0.1132   magnitude:  predictable
past_60d_vol.corr(next_60d_vol)         # +0.5614   persistence of volatility
```

`autocorr(1)` correlates the series with itself shifted by one day: "does today tell
you anything about tomorrow?" Applied to returns it answers *direction*; applied to
`abs(returns)` it answers *size of move*, ignoring sign. The third line rolls a
60-day standard deviation forward and backward from each date and correlates the two,
asking directly whether the window `realized_vol` uses predicts the window it is used
over.

**Direction is unpredictable; magnitude is not.** Volatility clusters: violent days
follow violent days. This is the phenomenon the ARCH/GARCH literature describes
(Engle, Nobel 2003), and the 60-day rolling standard deviation used here is its
crudest usable form.

The connection worth keeping: **the +0.56 is why position sizing works, and the −0.01
is why most of the eight signals are expected to die.** Sizing leans on the one part
of the data that carries a forecastable pattern; the signals are all trying to predict
the part that does not.

This is now recorded in `CONCEPTS.md` Part 3.45.

### Honesty note kept in the file

The March 2020 example is explicit that volatility targeting **still lost money**. The
position only fell from 0.627 to 0.566 across the crash week, because it was reacting
to a 60-day window that mostly still looked calm. It reduces the loss; it does not
prevent it, and it never anticipates. That lag is the honest behaviour, not a defect,
removing it would require knowing the day being sized.

### `CLAUDE.md` updated

The concept-note guidelines now require: assume no finance background at all; always
include worked examples using real numbers from this project's data rather than
invented ones; show the arithmetic; and state a concept's limits in the same breath as
its benefits, so examples do not oversell.

---

## Entry 13: 2026-08-20: Calculations moved out of the appendix and into the entries

Entry 12's appendix ("Appendix A: Calculations reference") has been removed and its
content woven into the entries that built each calculation.

**Why.** The appendix collected eleven formulas in one lookup-friendly place, but
collecting them stripped out the reasoning. `returns.rolling(60).std() * sqrt(252)` in
a reference table is a fact to memorise; the same line inside Entry 10, next to the
explanation of why volatility has to be measured at all and what breaks if the shift is
missing, is something you can reconstruct from understanding. The appendix optimised
for looking a formula up, which is the thing you least need when you are trying to
learn it.

**What moved where:**

- **Daily returns**: into Entry 10, as the input everything else operates on,
  including the worked arithmetic on 2020-03-13 and why the project uses simple rather
  than log returns.
- **`realized_vol`**: the three steps are now a table inside Entry 10 with the real
  intermediate values (`0.011138` per day → `0.1768` per year), plus an explicit note
  that the √252 is cosmetic and changes no decision.
- **`vol_target`**: the division is now shown worked both ways in Entry 10, calm
  versus crisis, with the frozen parameters named alongside.
- **The clustering diagnostics**: into Entry 12, with an explanation of what
  `autocorr(1)` actually does, since the numbers mean nothing without it.
- **The unwritten calculations** (strategy return, turnover, costs, Sharpe, maximum
  drawdown, Newey–West, Deflated Sharpe): removed entirely. Each will be explained in
  the entry that implements it, which is when the explanation can be tied to working
  code rather than to a plan.

**`CLAUDE.md` updated** to require this pattern, and to require that the arithmetic in
every worked example be checked before it is written: after one was shipped in Entry
10 that used the same day's position instead of the previous day's, which is precisely
the bug the surrounding paragraph was explaining.

---

## Entry 14, 2026-08-21, CONCEPTS.md rewritten at course register and completed

Two rounds of feedback drove this: the file was pitched too low, and it was incomplete.

### Register

The previous version had drifted into simplified vocabulary, using phrases like "how
much it bounces around" in place of "the standard deviation of returns". That is the
wrong trade. Miguel has the mathematical background; what he lacks is the domain
vocabulary, and substituting plain words for the standard terms actively hinders him,
since the standard terms are how he finds the literature later.

Rewritten at the register of a university course: build from the ground up, define
every term properly on first use, order the material so that each definition uses only
terms already introduced, and never avoid a term because it sounds technical.

Terms now introduced and defined rather than paraphrased: notional exposure, leverage,
excess return, simple versus logarithmic returns and why the choice matters,
heteroskedasticity, ex ante versus ex post, the square root of time rule, Bessel's
correction, autocorrelation, volatility clustering, stylized facts, ARCH and GARCH,
measurability with respect to an information set, basis point, HAC standard errors,
extreme order statistics.

### Completeness

Several quantities were referenced throughout the file and never defined. Two new parts
close that gap.

**Part 11, measuring performance.** The basis point; turnover and why it is defined on
position changes rather than trade counts; the transaction cost formula including why
the round trip quote is halved; the Sharpe ratio, including why no risk free rate is
subtracted for futures and a rough reference scale for interpreting the number; maximum
drawdown and why it is reported alongside Sharpe rather than in place of it.

**Part 12, the statistical gauntlet.** In sample versus out of sample and why a
development set is optimistically biased; walk forward analysis and which of the eight
signals actually needs it; why the conventional t statistic is inflated under positive
autocorrelation and what Newey West does about it; multiple testing framed as the
expectation of an extreme order statistic; regime stability and why the breakpoints
must be chosen before results are seen; and the verdict rule itself.

The Deflated Sharpe Ratio is described conceptually in two stages but its formulas are
still deliberately absent, consistent with the decision in Entry 3. The kurtosis
convention trap is flagged and left unresolved.

### Style constraint

**No em dashes**, anywhere: prose, documentation, commit messages, chat. Forty three
were removed from `CONCEPTS.md`, replaced with a colon where the following clause
explains the preceding one, a comma where it qualifies, or a full stop where it is a
separate thought. `CLAUDE.md` now records the constraint, along with the register
guidance above.

The file went from 171 lines at Entry 11 to 899.

---

## Entry 15, 2026-08-21, First end to end backtest. The machine produces a number.

Five components implemented, wired together, and run against live data. This is the
first time the project has produced a performance figure of any kind.

**Headline result, `ma_cross` on gold, 2006 to 2026:**

```
IS Sharpe 0.311    OOS Sharpe 0.523    turnover 4.05    OOS at 4bp 0.518
```

### The components

**`signals/ma_cross.py`.** Long when the 50 day simple moving average exceeds the 200
day, short otherwise.

```python
fast = close.rolling(50).mean()
slow = close.rolling(200).mean()
position = (fast > slow).astype(float) * 2 - 1
return position.where(fast.notna() & slow.notna())
```

The `.where(...)` is the part worth explaining. The first 199 rows have no 200 day
average, so no signal exists. Filling those with a position would have the strategy
trading before its own rule is defined, and because a fill value is constant it would
register as a deliberate directional bet held for most of a year. Leaving them NaN
means no position, no trade, no P&L, which is the honest representation of "the signal
does not exist yet".

**`engine/costs.py`.** Cost is charged on position change, not on trade count:

```python
cost = positions.fillna(0.0).diff().abs() * cost_bps / 2 / 10_000
net  = gross_returns - cost
```

Three details. The `/10_000` converts basis points to a fraction. The `/2` is because
`cost_bps` is quoted round trip, meaning in and back out, while a single day position
change of 1.0 is one way. The `fillna(0.0)` before differencing charges the initial
entry: on the first day the signal exists the position moves from nothing to something,
which is a real trade, and differencing the raw series would produce NaN there and hand
the strategy a free entry.

The `positions` passed in must be the volatility sized position, not the raw plus or
minus one. Cost is paid on the quantity actually traded.

Turnover, annualized, on the same quantity:

```python
turnover = positions.fillna(0.0).diff().abs().mean() * 252
```

**`engine/metrics.py`.** Sharpe ratio only, for now:

```python
sharpe = returns.dropna().mean() / returns.dropna().std() * np.sqrt(252)
```

No risk free rate is subtracted, since futures positions are already financed and the
return series is therefore already an excess return.

**`engine/backtest.py`.** The pipeline, and the causality argument that justifies it:

```python
ret    = panel["close"].pct_change()
raw    = signal(panel)              # desired position at close of t
lagged = raw.shift(EXEC_LAG_BARS)   # held over t+1
sized  = vol_target(lagged, ret, target=target_vol)
gross  = sized * ret
net    = apply_costs(gross, sized, cost_bps)
```

The claim to verify is that `gross_t = sized_t * ret_t` uses nothing from day `t` on
the position side:

- `sized_t` takes its direction from `lagged_t`, which is `raw_{t-1}`. Decided at the
  close of t-1.
- `sized_t` takes its scale from the volatility estimate at t, and `realized_vol`
  carries its own internal `.shift(1)`, so that estimate spans data through t-1 only.
- `ret_t` is the move over day t.

Every day's P&L therefore uses only information available at the close of t-1 to earn
day t's return. **The two shifts are independent and both are required.** Removing the
explicit one leaks the direction; removing the one inside `realized_vol` leaks the
sizing. Neither failure would raise an error.

`split_is_oos` takes a positional split on the dropna'd series, first 60 percent in
sample, remainder out of sample, so the two halves hold comparable numbers of live
observations rather than comparable spans of calendar time.

### A defect found at runtime: the registry was empty

`REGISTRY["ma_cross"]` raised `KeyError` on the first run. Each signal module calls
`@register` at import time, but nothing imported the modules, so no decorator ever
executed and the registry stayed empty. The eight signals existed as files and did not
exist as far as the program was concerned.

Fixed with an explicit `_load_all()` at the bottom of `signals/__init__.py`, listing
the eight modules by name. **Explicit imports rather than a directory scan**, because
the Deflated Sharpe correction requires an honest count of how many signals were tested,
and auto discovery would let that count drift as files were added or removed without
anyone noticing.

### Verification, which matters more than the headline numbers

**The adversarial test, run on real gold rather than synthetic data.** Feed the engine a
signal that already knows the current day's return:

```
through the engine, lag applied  : Sharpe  -0.256
same signal, lag removed         : Sharpe +16.509
```

The engine extracts nothing from perfect foresight, which is the correct behaviour.
The second figure is the value of the protection: one removed `.shift()` converts a
worthless rule into a Sharpe of 16.5. Worth remembering as a reference point for what a
leak looks like in this dataset.

**Other checks:**

| Check | Result | Expected |
|---|---|---|
| Realized volatility of the strategy | 0.1064 | near the 0.10 target, missing slightly |
| First traded day | 2006-10-18 | 200 day window plus one bar of lag |
| Position range | -1.28 to 1.29 | below the 3.0 cap throughout |
| Days at the leverage cap | 0 | none expected at gold's volatility |
| Direction flips | 28 in 4,953 days | consistent with turnover 4.05 |
| Cost drag, out of sample | 0.527 gross to 0.523 net | negligible at 28 trades |

**Test suite: 14 passing, 6 failing.** All four engine invariant tests went green,
including `test_execution_lag_kills_same_bar_foresight`. The six remaining failures are
the roll adjustment and statistics stubs, still unimplemented by design.

### How not to read this result

The out of sample Sharpe of 0.523 is **not** evidence that trend following works on
gold. It is one signal, it has not been through the multiple testing correction, its
standard error has not been computed with autocorrelation in mind, and it has not been
checked for regime stability. Out of sample exceeding in sample is more readily
explained by sample variation than by anything real.

What this run establishes is narrower and more important at this stage: **the machine
runs, and it does not lie.** The verdict on the signal comes after Part 12 of
`CONCEPTS.md` is implemented.

---

## Entry 16, 2026-08-21, Pipeline overview added to CONCEPTS.md

A gap in the documentation, noticed when Miguel summarised the architecture back
correctly and neither document contained that summary. The pipeline was described
piecemeal, in the `run_backtest` docstring and across Entry 15, but nowhere as a single
path from idea to number.

Added as `CONCEPTS.md` sections 3.4 and 3.5, placed early so a reader gets the map
before the components, with forward references to the parts that define each term.

**Five stations produce a measurement:** signal, then lag and size, then costs, then
metrics, then the in sample and out of sample split. The six line code path is included
so the mapping from concept to implementation is explicit.

**Order within station 2 is called out separately.** Lag first, then size. Reversing
them allows the sizing layer to condition on a day the direction has not yet seen,
which introduces lookahead through ordering alone, without any single component being
individually wrong. That is a failure mode worth naming because it is invisible in a
review of the parts.

**Three further stations turn a measurement into a claim:** HAC standard errors,
the multiple testing correction, and regime stability. None are implemented.

The distinction this section is really recording: **the split produces an unbiased
measurement, not a verdict.** It removes the optimism introduced by developing against
the data. It says nothing about whether the number is distinguishable from zero. The
section states explicitly that `ma_cross`'s out of sample Sharpe of 0.523 has no verdict
attached to it yet, so the figure is not mistaken for a result on a later reading.

---

## Entry 17, 2026-08-21, Backtesting itself documented as a concept

`CONCEPTS.md` described this project's specific pipeline but never explained what a
backtest *is*, or what distinguishes a sound one from a misleading one. The term was
defined in a single line and otherwise assumed. Added as a new Part 4, placed after the
project overview and before the volatility material, with the subsequent parts
renumbered from 5 to 13.

**Contents of the new part:**

- **What a backtest is.** A simulation that replays historical data through a rule and
  computes the return series it would have produced. Stated precisely as a measurement
  of a counterfactual, under assumptions, and explicitly not a prediction.
- **The mechanism.** The four step loop of observe, decide, execute, account, and the
  equity curve as the cumulative product of the resulting return series. Noted that it
  compounds rather than sums, so a 10 percent gain followed by a 10 percent loss leaves
  0.99 rather than 1.00.
- **Event driven versus vectorized architectures**, and why this project is vectorized:
  the whole pipeline fits in six lines, so the causality argument can be verified by
  reading rather than by tracing mutable state. The tradeoff is recorded honestly, since
  a vectorized backtest cannot express path dependent logic such as stop losses. None of
  the eight signals need it.
- **The assumptions a daily bar backtest embeds**, as a table with each assumption, how
  reality differs, and whether the difference is material here. The general principle
  stated: an assumption is acceptable when its violation is small relative to the effect
  being measured. A strategy earning 20 basis points a trade tolerates imprecision about
  a 2 basis point cost; one earning 3 basis points does not.
- **Six requirements for an honest backtest**, five being the section 3.2 failure modes
  restated as positive obligations, the sixth being correct instrument construction.
- **The futures roll problem**, in full. This was previously described only in
  `data/roll.py` and in passing, despite being the failure mode most specific to this
  asset class.
- **What a backtest still cannot tell you**, even when correct.

### The roll section in particular

Worth recording why it earned several hundred words. At each contract roll the expiring
and replacement contracts trade at different prices, the difference reflecting cost of
carry. Concatenating raw prices turns that difference into an apparent one day return
that no position captured. Because gold is normally in contango, the deferred contract
being more expensive, these phantom gaps are **systematically negative** and recur
several times a year across the entire sample.

The result is a persistent artificial downward drift that does not look like a bug. It
looks like a market phenomenon, it makes every long biased signal look worse and every
short biased signal look better, and it is invisible on a twenty year price chart. That
combination is why `data/roll.py` specifies the check as a test rather than an
inspection.

Ratio adjustment is the method chosen, since everything downstream operates on
percentage returns. Difference adjustment, the Panama method, preserves dollar spreads
but can drive early history negative over a long sample. The two must never be mixed
within one series.

---

## Entry 18, 2026-08-21, Newey-West standard errors, and a wrong prediction corrected

`stats/hac.py` implemented. Two functions.

### `auto_bandwidth(n)`

```python
int(np.floor(4 * (n / 100) ** (2 / 9)))
```

Chooses how many lags of autocorrelation to correct for. It grows with sample size but
slowly: the exponent 2/9 means quadrupling the sample raises the bandwidth by about a
third. On the 1,982 out of sample observations it returns 7. The tradeoff is that too
few lags leaves autocorrelation uncorrected, while too many add noise, since each extra
autocovariance is itself estimated from the same finite sample.

### `newey_west_tstat(returns, lags=None)`

```python
model = sm.OLS(r.values, np.ones(len(r))).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
return float(model.tvalues[0]), float(model.bse[0]), lags
```

**The trick, which is worth understanding rather than copying.** Regressing a series on
nothing but a column of ones makes the fitted coefficient the sample mean, and its
t-statistic tests exactly the hypothesis of interest: is the mean return zero. So the
question becomes a regression, and regression machinery then allows a HAC covariance
estimator to be substituted with one argument.

**`cov_type="HAC"` is the whole function.** Omitting it returns the ordinary standard
error computed under an independence assumption. It raises no error and reports an
inflated t-statistic, which is precisely the failure this function exists to prevent.

### The result on `ma_cross`

```
                 IS          OOS
n              2971         1982      (11.8 and 7.9 years)
Sharpe       +0.311       +0.523
naive t      +1.067       +1.466
HAC t        +1.068       +1.472      lags 8 and 7
```

**Neither clears the conventional |t| > 2 threshold.** Nearly eight years of untouched
out of sample data, and the signal cannot be distinguished from zero before any
correction for multiple testing has been applied.

### A prediction that was wrong, and why it matters

The expectation going in was that the HAC t-statistic would be **smaller** than the
naive one, on the reasoning that a trend signal holds one position for months, so
consecutive daily returns express a single bet and are positively autocorrelated.

The measured result is that the two are equal to three decimal places, with the HAC
standard error 0.996 times the naive one. The autocorrelation of the strategy's out of
sample return series:

```
lag  1: -0.0037
lag  5: +0.0043
lag 20: -0.0211
```

**The first half of the reasoning is true and the second does not follow.** The daily
return is `w_{t-1} * r_t`. Where `w` is roughly constant across a stretch, that stretch
of strategy returns is gold's returns scaled by a constant, and gold's daily returns are
close to serially uncorrelated, measured at -0.0096 in Entry 12. Scaling an uncorrelated
series by a constant leaves it uncorrelated.

**A persistent position does not imply a persistent return.** These are different
statements about different series, and conflating them is easy.

The implementation is correct: `test_hac_widens_se_under_positive_autocorrelation`
constructs an AR(1) series and confirms HAC does shrink the t-statistic there.

**Where HAC will actually matter in this project:** signals whose returns genuinely
overlap, or whose positions track an autocorrelated quantity. Twelve month momentum is
the obvious candidate, and the real yield deviation signal is another, since a rolling
regression residual is autocorrelated by construction. For a slow binary trend signal on
daily bars, HAC and naive agreeing is itself the finding.

---

## Entry 19, 2026-08-21, Probabilistic Sharpe Ratio, and two traps of very unequal size

`probabilistic_sharpe` implemented, stage one of the Deflated Sharpe.

```python
variance = 1 - skew * sr + ((kurtosis - 1) / 4) * sr**2
z = (sr - benchmark) * sqrt(n - 1) / sqrt(variance)
return norm.cdf(z)
```

The denominator is the standard error of the Sharpe estimator corrected for
non-normality. Under normality, skew 0 and raw kurtosis 3, it reduces to
`sqrt(1 + sr**2 / 2)`, the classical Lo (2002) result. Returns nan rather than raising
when the variance term is non-positive, which extreme skew can produce and which has no
probability attached to it.

### Result on `ma_cross` out of sample

```
n                 1982
Sharpe annual     +0.5227
Sharpe per day    +0.03293
skew              -0.5150
kurtosis excess   +4.7079
kurtosis raw      +7.7079

PSR vs benchmark 0    0.9267
Phi(HAC t = 1.472)    0.9295     normal-assumption reference
```

### The finding: the two conventions differ enormously in how much they matter

Both were flagged in advance as traps. Measured, they are not comparable.

**Frequency consistency is catastrophic.** The Sharpe and the observation count must
refer to the same period. Passing the annualized 0.523 against a daily n of 1982
inflates the numerator by sqrt(252):

```
correct, per-day 0.033 against n=1982   ->  PSR 0.9267
wrong, annualized 0.523 against n=1982  ->  PSR 1.0000
```

A certainty, from a signal that cannot clear a t-statistic of 2.

**The kurtosis convention is negligible at this frequency.**

```
correct, raw kurtosis 7.71             ->  PSR 0.9267
wrong, excess 4.71 passed as raw       ->  PSR 0.9268
```

A difference of 0.0001. The reason is structural rather than a property of this
dataset: both correction terms are scaled by the per-period Sharpe.

```
skew term      -(-0.515)(0.033)      = +0.0170
kurtosis term  ((7.71-1)/4)(0.033^2) = +0.0018
variance       1.0188   ->   sqrt = 1.0094
```

The standard error is inflated by 0.94 percent in total. Gold's tails are genuinely fat,
excess kurtosis 4.7, but the kurtosis term carries a factor of SR squared and 0.033
squared is 0.001. **At daily frequency the higher moments barely enter PSR.** They
matter at monthly or annual frequency, where the per-period Sharpe is an order of
magnitude larger.

**This corrects an overstatement made in Entry 3 and repeated in the docstring**, which
claimed the kurtosis mistake "shifts every result in the project in the same direction".
It does, and by an amount too small to observe. The docstring now records the measured
figures and contrasts them with the frequency trap, so a future reader does not go
hunting for a large effect that is not there.

### A test that was wrong, not the code

`test_negative_skew_lowers_psr` failed on first run. Investigation showed the property
holds by a wide margin and the test could not observe it: at SR 1.0 with n 1000 the
z-scores are 25.807 and 16.895, and both CDFs round to exactly 1.0 in float64.

Rewritten at per-day magnitudes, SR 0.033 against n 1982, where the effect is visible.
Four further sign checks added, so that no single sign flip can pass the suite: positive
skew raises PSR, higher kurtosis lowers it, more observations raise it, and a
non-positive variance term returns nan.

Testing at the magnitudes the project actually produces is the stronger check. The
original parameters were chosen for readability and happened to be numerically blind.

---

## Entry 20, 2026-08-21, The first verdict. `ma_cross` is DEAD.

`expected_max_sharpe` implemented, `deflated_sharpe` wired, the trial ledger filled, and
the first signal adjudicated against the frozen rule.

### `expected_max_sharpe(n_trials, sr_variance)`

```python
gamma = np.euler_gamma
z1 = norm.ppf(1 - 1/N)
z2 = norm.ppf(1 - 1/(N * e))
return sqrt(V) * ((1 - gamma) * z1 + gamma * z2)
```

The expected maximum of N draws from a normal distribution, from extreme value theory.
The maximum of N standard normals concentrates around sqrt(2 ln N), and the two quantile
expression is the standard refinement.

Read it as **the bar that luck alone clears.** If N worthless strategies are tested, the
best of them will look about this good.

`N < 2` returns 0. One trial means no selection took place, so there is no selection bias
to correct. The formula cannot express this, since `norm.ppf(1 - 1/1)` is `norm.ppf(0)`,
negative infinity.

### `deflated_sharpe`

PSR evaluated against the expected maximum bar rather than against zero.

**The function computes the Sharpe as `mean/std` on the raw series with no
annualization**, so it lines up with `n_obs` by construction. `periods_per_year` is
accepted for interface consistency and deliberately unused: annualizing inside this
function would reintroduce the frequency mismatch that `probabilistic_sharpe` cannot
detect, and the wrapper is the only place that mismatch can be prevented.

### The verdict on `ma_cross`

```
observed Sharpe, out of sample   +0.523 annualized   (0.03293 per day)
expected-max bar at N = 8        +0.520 annualized   (0.03278 per day)
difference                       +0.003

PSR against zero                  0.9267
DEFLATED SHARPE                   0.5026
verdict, needs > 0.95             DEAD
```

Nearly eight years of untouched out of sample data, and the signal beats the luckiest of
eight coin flippers by three thousandths of a Sharpe ratio. A Deflated Sharpe of 0.5026
is the formal statement that it is a coin toss whether this strategy is better than
nothing.

### The bar as a function of N

```
N     1:  0.000      no selection, nothing to correct
N     2:  +0.185
N     8:  +0.520     <- ma_cross observes +0.523
N    20:  +0.678
N   100:  +0.903
N  1000:  +1.161
```

The sqrt(2 ln N) growth is visible: 8 to 1000 is a 125 fold increase in trials and
roughly a doubling of the bar. Testing more things is punished, and gently.

### The table that is the entire project

The same return series, judged against different honest trial counts:

```
N =  1:  DSR = 0.9267     "looks good"
N =  4:  DSR = 0.6589
N =  8:  DSR = 0.5026     the honest count
N = 16:  DSR = 0.3700
N = 50:  DSR = 0.2109
```

**Nothing about the strategy changes across those rows.** Only the honesty of the
accounting does. And N is the single input that cannot be audited from outside the
project, which is precisely why the ledger is dated and written down in advance rather
than reconstructed once the number is known.

### The trial ledger, and a correction to how it was being counted

Filled at **N = 8**. The definition was sharpened by Miguel and the previous count was
wrong: it was counting executions rather than candidates.

**A trial is a distinct strategy configuration that was a candidate to become the
reported result.** Consequences:

| Situation | Trials |
|---|---|
| One signal at 2 bp and again at 4 bp | 1, a cost sensitivity check |
| One signal in sample and out of sample | 1, two views of one candidate |
| Eight distinct signals | 8 |
| Four parameter settings tried, best kept | 4, a selection was made |
| `50/200` frozen from folklore, never varied | 1, no selection occurred |
| Cheat signals used to verify the engine | 0, never candidates |
| The overfitting sidecar grid search | 0 here, it carries its own DSR |

The weighting is toward parameter searches. A sweep over 100 moving average pairs is 100
trials even though it is one line of code, because the selection among them is exactly
what the correction penalises.

**Worth stating plainly: freezing `50/200` in advance was worth about 0.15 of Deflated
Sharpe** compared to having searched four pairs and kept the best. The pre-registration
is not paperwork; it is a term in the arithmetic.

### How to read this result

`ma_cross` is dead, and that is the framework working rather than failing. A moving
average crossover on gold, run honestly, cannot be distinguished from the best of eight
lucky coin flips. The signal was never expected to survive; what matters is that the
machinery said so with a number and a reason rather than with an opinion.

Cause of death, under the frozen verdict rule, is condition 2: Deflated Sharpe 0.5026,
below the 0.95 threshold. Conditions 1 and 3 were not reached, since the rule records the
first condition failed.

---

## Entry 21, 2026-08-21, Regime stability, and a weakness found in condition 3

`stats/regimes.py` implemented: `by_regime`, `count_positive_regimes`, `sign_stability`.
This is condition 3 of the frozen verdict rule.

The five windows come from the hardcoded `REGIMES` constant, which mirrors
`DECISIONS.md` section 4 and is never inferred from data. Choosing breakpoints after
seeing where a strategy performed well is a slower form of overfitting, and hardcoding
them makes it impossible rather than merely discouraged.

`by_regime` returns n, mean, annualized mean, Sharpe, sign, and a `thin` flag below 60
observations. **The count is reported deliberately.** The COVID window is a single
calendar year at 253 observations against 1,380 for the modern regime, and reading a
thin regime's mean as equally informative is the obvious way to misuse the table.

### Result for `ma_cross`

```
regime          n     mean/day   annualized   Sharpe   positive
bull_run     1229   +0.000513      +0.1292    +1.220     yes
bear_2013    1088   -0.000141      -0.0356    -0.340     no
range_recov  1003   +0.000021      +0.0053    +0.051     yes
covid_spike   253   +0.000565      +0.1423    +1.165     yes
modern       1380   +0.000139      +0.0350    +0.325     yes

positive regimes: 4 of 5      condition 3: PASS
```

The signal passes condition 3 and remains DEAD on condition 2, Deflated Sharpe 0.5026.

### Weakness 1: condition 3 mostly measures gold, not the signal

Running gold's own returns through the same five windows produces an **identical sign
pattern**:

| regime | `ma_cross` | gold itself |
|---|---|---|
| bull_run | positive | positive |
| bear_2013 | negative | negative |
| range_recov | positive | positive |
| covid_spike | positive | positive |
| modern | positive | positive |

A trend follower that is long most of the time inherits the underlying asset's regime
signs. So for this class of signal, condition 3 is largely reporting which regimes gold
rose in. It will tend to pass for any long biased signal in this sample and fail for any
short biased one, which is worth knowing before the remaining seven signals are judged
by it.

Worth noting separately: in the bear regime gold fell 11.5 percent annualized and
`ma_cross` **also lost**, 3.6 percent annualized. It was short and still lost money.
That is whipsaw, not a hedge, and it is the kind of detail a pass on condition 3 hides.

### Weakness 2: `mean > 0` is a knife edge

`range_recov` counts as a positive regime on an annualized mean of **+0.53 basis
points**, Sharpe 0.051. Statistically indistinguishable from zero, and it counts exactly
as much as `bull_run` at Sharpe 1.22.

So "4 of 5" reads stronger than the data supports. Honestly it is 3 of 5 with one coin
flip.

### Why neither weakness is being fixed

**The rule is frozen.** Changing a threshold after seeing a result is precisely the
failure the pre-registration exists to prevent, and a rule that can be tightened once its
weaknesses are visible provides no evidence at all.

Both weaknesses are therefore recorded here and must appear in the graveyard write up
rather than being quietly repaired. A documented weakness is a finding; a silently
patched one is a fabrication.

If a future version of this framework wants a stronger condition 3, the candidates are
requiring a positive Sharpe above some threshold rather than a positive mean, or judging
the signal against the asset's own regime returns rather than against zero. Either would
have to be frozen in advance of the next run.

---

## Entry 22, 2026-08-21, Two more signals. Three dead, five to go.

`ts_momentum` and `seasonality` implemented. Both needed no new data source, so they
plugged into the existing machinery unchanged.

### `ts_momentum`

```python
trail = close / close.shift(252) - 1
position = (trail > 0).astype(float) * 2 - 1
return position.where(trail.notna())
```

Hard +/-1 with no neutral band, per the frozen spec. A dead zone around zero would be a
parameter, and every parameter is a trial the Deflated Sharpe must be told about.

### `seasonality`

```python
month = df.index.month
return pd.Series(np.where(np.isin(month, LONG_MONTHS), 1.0, 0.0), index=df.index)
```

Values in {0, 1} rather than {-1, +1}, deliberately. The hypothesis is that certain
months are strong, not that the remaining months are weak, so shorting them would test a
claim nobody made.

It is the only signal in the project that needs no price history, which also makes it
the only one immune to the futures roll problem.

### Results, all three implemented signals

| signal | IS | OOS | turnover | HAC t | DSR | regimes | vol |
|---|---|---|---|---|---|---|---|
| `ma_cross` | 0.311 | 0.523 | 4.05 | 1.47 | 0.503 | 4/5 | 0.106 |
| `ts_momentum` | 0.200 | 0.507 | 11.34 | 1.42 | 0.482 | 3/5 | 0.107 |
| `seasonality` | 0.431 | 0.310 | 2.96 | 0.86 | 0.289 | 4/5 | 0.042 |

**All three DEAD on condition 2.** No Deflated Sharpe is within 0.45 of the 0.95 bar.

### Seasonality's low volatility is dilution, not a sizing failure

```
days in market        814 of 5153  (15.8%)
vol WHILE in market   0.106     targeted to 0.10, correct
vol over full series  0.042     diluted by being flat 84% of the time
```

Exposure is correctly targeted on the days it trades. The full-series figure is low
because the position is zero most of the year. Sharpe is invariant to leverage, so the
grade is unaffected, and 0.310 out of sample is a real comparison against the others.

### An expectation that was wrong: momentum turns over the MOST

The prediction going in was that a twelve month lookback would flip rarely. It has the
highest turnover of the three, 11.34 against `ma_cross`'s 4.05.

```
                direction changes    raw signal turnover    sized turnover
ma_cross                     28                    2.85              4.05
ts_momentum                 138                   14.19             11.34
seasonality                  81                    3.96              2.96
```

138 direction changes against 28. The cause is mechanical rather than statistical.
**`ma_cross` compares two smoothed series; `ts_momentum` compares today's price against
one single day's price 252 days ago.** That lone reference point is noisy, and whenever
it happens to sit near the current price the signal chatters. A long lookback does not
imply a slow signal if the test built on it is a single comparison.

### Turnover is a property of the sized position, not the signal

The two turnover columns diverge in both directions, which is worth understanding:

- `ma_cross` rises, 2.85 to 4.05, because volatility scaling adds continuous daily
  position drift on top of the discrete flips.
- `ts_momentum` falls, 14.19 to 11.34, because it chatters most during calm periods,
  where the volatility scaler is holding a smaller position, so those flips move less
  quantity than the raw count implies.

Cost is charged on the sized position, which is the correct quantity: you pay to trade
what you actually hold.

---

## Entry 23, 2026-08-21, The front door now shows the real work

`report/graveyard.py` implemented and `scripts/run_gauntlet.py` rewritten. The project's
committed entry point now produces the verdict table and writes `reports/graveyard.md`.

### The problem this fixes

Every meaningful number produced since Entry 18, the HAC statistics, the Deflated
Sharpe, the regime tables, the verdicts, was computed in throwaway scratch scripts that
were never part of the repository. `run_gauntlet.py` still ran a single hardcoded signal
and printed four columns: in sample Sharpe, out of sample Sharpe, turnover, and a stress
Sharpe.

**Anyone cloning the repo and running the program would have seen none of the rigour
that is the entire point of the project.** The work existed and the deliverable did not
expose it. That is a hole in the deliverable rather than a limitation to be documented,
and it is fixed rather than noted.

### `adjudicate`

Implements the frozen verdict rule exactly once, in one place:

```python
conditions = [
    (oos_returns.mean() > 0,            "negative out-of-sample return, net of costs"),
    (dsr > DSR_THRESHOLD,               f"deflated Sharpe {dsr:.3f}, below the bar"),
    (n_regimes >= MIN_POSITIVE_REGIMES, f"positive in only {n_regimes} of 5 regimes"),
]
failures = [why for ok, why in conditions if not ok]
alive = not failures
cause_of_death = failures[0] if failures else ""
```

Everything is judged on the **out of sample, net of cost** series. The in sample figure
is reported for context and carries no weight in the verdict, because a number computed
on data used during development is optimistically biased by an amount nobody can
estimate.

### `to_markdown`

Writes the report: headline table sorted by Deflated Sharpe, the verdict rule quoted
above the results so the reader sees the standard before the outcome, a per signal
autopsy carrying the hypothesis as stated before testing, the full regime breakdown, and
a caveats section.

The autopsies translate the Deflated Sharpe into a sentence rather than leaving it as a
number. For `seasonality`: *there is a 71 percent chance a set of worthless strategies
would have produced something this good by selection alone.*

### Three decisions inside the script

**`N_TRIALS = 8`, read from the ledger, deliberately not `len(GRADED)`.** Deriving the
trial count from how many signals happen to be implemented would make every verdict
quietly more flattering as work progressed, which is precisely backwards. All eight are
candidates; three merely exist yet.

**`GRADED` lists only implemented signals.** Including the five stubs would emit rows of
NaN that read like results.

**The caveats section is generated, not optional.** It states the unimplemented roll
adjustment, the 114 corrupt bars from Entry 6, and both weaknesses in condition 3 from
Entry 21. A report presenting verdicts while omitting what they rest on would be
committing the exact failure this project argues against.

### Output

```
signal                IS     OOS    @4bp    turn   HAC t     DSR   reg  verdict
ma_cross           0.311   0.523   0.518    4.05    1.47   0.503   4/5  DEAD
ts_momentum        0.200   0.507   0.496   11.34    1.42   0.482   3/5  DEAD
seasonality        0.431   0.310   0.303    2.96    0.86   0.289   4/5  DEAD

0 of 3 survived.
```

### A formatting bug caught on first read

The regimes sentence was emitted as a separate list element rather than appended to the
preceding string, so it rendered as its own line with a leading space. Fixed by
concatenation. Worth recording only because it was caught by reading the generated
output rather than by assuming the generator was correct, which is the habit that
matters.

---

## Current state at a glance

| | |
|---|---|
| Commits | 4 (through `04feaf3`) |
| Uncommitted | `sizing.py`, `costs.py`, `metrics.py`, `backtest.py`, `ma_cross.py`, `signals/__init__.py`, `run_gauntlet.py`, `CONCEPTS.md`, `CLAUDE.md`, log entries 19-23, DECISIONS.md ledger, graveyard report |
| Functions implemented | 21 of 41 (plus helpers) |
| Tests | 23 passing, 1 failing (roll adjustment, still a stub) |
| Linter | clean |
| Real results produced | `reports/graveyard.md`, generated by `run_gauntlet.py`. 3 of 8 signals judged, **0 survived** |

### Open items

1. Miguel to rewrite `DECISIONS.md` in his own words and defend each parameter.
2. Decide how to handle the 114+ corrupt bars in 2006–2011.
3. Record in DECISIONS.md the reasoning for starting at 2006 when data exists from 2000.
4. Decide whether the OHLC integrity audit becomes a permanent test.
5. Commit the build log and `CLAUDE.md`.

### Next piece of work

**1. The futures roll adjustment.** `data/roll.py` is still a stub and this is the last
untested correctness risk sitting underneath every number in `reports/graveyard.md`. A
continuous gold series spliced from expiring contracts carries a phantom price gap at
each roll, systematically negative under contango, that no position could have earned.
It looks like a market phenomenon rather than a bug. Explained in full in `CONCEPTS.md`
Part 4.6. The one red test in the suite is its detection check.

**2. The corrupt-bar decision.** Open since Entry 6 and still unmade: 114 bars with a
close above the session high, concentrated in 2006 to 2011. Disclose, move the sample
start to 2009, or gate it in the loader. It changes a frozen parameter, so it needs its
own commit against DECISIONS.md.

**3. The five remaining signals.** `carry`, `cot_contrarian`, `real_yield_dev`,
`gold_silver_ratio`, and `dollar_trend`. Each needs a data source the project does not
yet load, so `load_fred`, `load_cot`, and `load_all` come first. Two carry known
complications recorded at Entry 2: `carry` may be unbuildable from free front-month-only
data, and `gold_silver_ratio` is genuinely a spread trade that the current single-asset
engine cannot express.

**4. `sizing.py` still has no dedicated tests.** The lookahead probe from Entry 10 was
run ad hoc and should be permanent, since the `.shift(1)` it protects is exactly the kind
of line someone tidies away.

**5. The overfitting sidecar**, once the rest is done. Grid-search moving average pairs,
show the best one's in-sample curve, show it collapsing out of sample, and show that the
Deflated Sharpe would have flagged it in advance at the honest trial count.

