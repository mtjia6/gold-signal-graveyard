# Build Log

A running, plain-language record of everything built in this repo, why it was built
that way, and what was decided along the way.

**Who this is written for:** someone who knows how to program but has never seen this
project, does not know futures markets, and was not present for any of the
conversations. Every entry should be readable on its own. Jargon gets defined the
first time it appears.

**Convention:** newest entry at the bottom. Every working session appends an entry.
Entries record *decisions and reasoning*, not just "changed file X" — git already
records that.

---

## Background: what this project actually is

Before any entry makes sense, three things need defining.

**Gold futures.** A futures contract is an agreement to buy or sell something at a
set price on a set future date. Gold futures trade on COMEX under the ticker `GC`.
Crucially, a futures contract *expires*. There is no single continuous "gold futures
price" — there is a December 2026 contract, a February 2027 contract, and so on. The
"front month" is whichever contract is nearest to expiry and therefore most heavily
traded. To get a multi-year price history you have to stitch many contracts together,
and how you stitch them is a major source of bugs (see Entry 5's open question).

**A trading signal.** A rule that looks at data available today and outputs a
position: go long (bet the price rises), go short (bet it falls), or stay flat. For
example: "be long if the price is above its 200-day average." A *backtest* runs that
rule over historical data to see what it would have earned.

**What this project is testing.** Eight signals that gold traders widely believe in.
The goal is *not* to find one that makes money. The goal is to build an evaluation
framework rigorous enough that we can trust the answer either way — and then honestly
report which signals survive it and which don't. If seven of eight die, the project
succeeded. The framework is the deliverable; the signals are the test subjects.

The reason this is worth building: it is very easy to produce a backtest that looks
profitable and is entirely an artifact of a bug or of statistical luck. Most of the
engineering in this repo exists to make specific, well-known failure modes impossible
rather than merely unlikely.

---

## Entry 1 — 2026-08-20 — Environment and toolchain

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
— it does the job of `pip`, `venv`, and `pyenv` in one tool, and it is roughly an
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
  file, "it worked last month" is not reproducible — a dependency silently updates and
  results change.

### Packages installed

| Package | What it is used for here |
|---|---|
| `pandas` | The core data structure. A `DataFrame` is a table with labelled rows and columns; here rows are trading dates and columns are prices. |
| `numpy` | Numerical arrays; pandas is built on it. |
| `scipy` | Statistical distributions — needed for the normal-distribution math in the Deflated Sharpe calculation. |
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
lock file, which plain `requirements.txt` does not give you — it pins direct
dependencies but not their dependencies, so environments still drift.

---

## Entry 2 — 2026-08-20 — Repository structure

Created at `~/Documents/Dev/gold-signal-graveyard`, git-initialised, local only (not
pushed to GitHub — the intent is to push once there is something worth showing).

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
signal could look better simply because it happened to take larger bets — and you
would have no way to tell that apart from genuine predictive skill. Forcing everything
through one code path makes the comparison structurally honest rather than honest by
good intentions.

### Why every function is currently unimplemented

There are 41 functions defined across `src/` and `scripts/`. 38 of them consist of a
docstring and `raise NotImplementedError`. The remaining 3 are the small decorator
that lets a signal register itself.

This is deliberate. The signatures and docstrings are the *specification* — they
record what each piece must do and which bug it exists to prevent. They get filled in
one at a time. Nothing in this repo produces a number yet.

### Why the tests currently fail

`tests/` contains 11 tests. 10 fail with `NotImplementedError` and 1 passes. This is
the intended state: the tests were written first, and they describe correct behaviour
that does not exist yet. They go green one at a time as functions get implemented.

The single passing test is `test_lag_is_exactly_one_bar`, which only checks that a
constant equals 1 — it needs no implementation.

The most important failing test is `test_execution_lag_kills_same_bar_foresight`. It
hands the engine a deliberately cheating signal that already knows today's return, and
asserts that the engine makes approximately **zero** money from it. If the engine is
built correctly, the one-day trading delay destroys the cheat. If that test ever
passes trivially or the engine shows a large profit there, information is leaking from
the future into the backtest — the most common and most destructive bug in this
domain.

**Commit:** `2df22bf` — "Scaffold: pre-registration, engine skeleton, and red test suite"

---

## Entry 3 — 2026-08-20 — The pre-registration document, and a correction

### What DECISIONS.md is

A "pre-registration" is a term borrowed from clinical trials. Before running the
experiment, you write down publicly what you are going to measure and what counts as
success — so you cannot later change the goalposts to match whatever result you got.

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
  works on data you developed it against proves nothing — you may simply have
  described the noise in that particular stretch of history. Out-of-sample data is the
  only real test.
- **Sharpe Ratio.** Average return divided by volatility, annualised. It measures
  return earned per unit of risk taken, so strategies of different sizes can be
  compared.
- **Deflated Sharpe Ratio.** A correction for the fact that testing many strategies
  guarantees at least one looks good by pure luck. Explained in the next section.

### The correction that happened here

The first version of `DECISIONS.md` was written by Claude, with every parameter filled
in — cost assumption, risk target, lookback windows, regime dates, split point. Every
*code* function was still an unimplemented stub, so on a narrow reading no
implementation had been written.

Miguel pushed back, and was right to. Choosing the frozen parameters of a study is the
intellectual content of the study. "The function bodies are empty" is a technicality,
not a defense. The same applied to `stats/deflated_sharpe.py`, whose docstring
originally contained the full mathematical formulas — handing over the hardest
derivation in the project.

**Actions taken:**

- The formulas in `deflated_sharpe.py` were removed and replaced with the two
  questions the math has to answer, plus a citation to the source paper: Bailey &
  López de Prado (2014), *"The Deflated Sharpe Ratio"*, Journal of Portfolio
  Management 40(5), pp. 94–107 — Section 2 for the Probabilistic Sharpe Ratio,
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

**Commit:** `2353e4d` — "Replace DSR formulas with the derivation questions and a paper citation"

### Why "Deflated" Sharpe at all — the problem it solves

Suppose you test 20 completely worthless strategies. Each one's measured Sharpe Ratio
is noise centred on zero, but noise has spread — some come out negative, some
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

## Entry 4 — 2026-08-20 — Checking what data is actually available

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
identical window. That is a defensible trade — comparability is the whole point — but
it is a *choice*, and it should be written into DECISIONS.md as one rather than left
looking accidental.

**Open item:** record that reasoning in DECISIONS.md.

---

## Entry 5 — 2026-08-20 — `load_yahoo`: the first working code

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

It is "step 1 of the slice" — the first piece of a thin vertical slice through the
whole system, chosen first because everything downstream depends on it.

### What it does, step by step

1. Make sure the cache directory exists.
2. If a cache file for this symbol already exists and covers the requested dates, read
   it from disk and return — no network call.
3. Otherwise download from Yahoo Finance via the `yfinance` package.
4. Clean up the result into the standard shape (details below).
5. Save it to disk as a Parquet file so the next call is free.
6. Return the requested date range.

**What "caching" means here.** The first call takes about 1.5 seconds and hits the
network. It writes the result to `data/cache/yahoo_GC_F.parquet`. Every later call
reads that file instead — 19 milliseconds, no network. This matters for more than
speed: if the code re-downloaded every run, a Yahoo outage or a silent data revision
would mean today's backtest differs from yesterday's for reasons unrelated to any code
change. Caching makes runs reproducible.

**What Parquet is.** A binary columnar file format. Compared to CSV it is much smaller
(the 5,152-row gold history is 180 KB), much faster to read, and — the reason it was
chosen — it *preserves data types*. Save a CSV and every date becomes a string that
has to be re-parsed on load, with the parsing rules being another place bugs hide.
Parquet round-trips a pandas DataFrame exactly. The `pyarrow` package provides the
reader and writer.

### The three problems that had to be solved

**Problem 1: yfinance returns an awkward column structure.**

Modern `yfinance` (1.6.0 here) returns columns as a two-level *MultiIndex* — a column
index with two levels rather than one, so a column is identified by a pair like
`('Close', 'GC=F')` rather than just `'Close'`. It does this even when you request a
single ticker. If you don't flatten it, `df["close"]` raises an error everywhere
downstream.

The fix takes the outer level and discards the ticker level. Notably, it selects that
level **by name** (`"Price"`) rather than by position (`0`). Positional access would
silently break if a future yfinance version reordered the levels — and "silently"
is the operative word: it would produce a valid-looking table of wrong data.

**Problem 2: two nearly identical close columns.**

Called with `auto_adjust=False`, yfinance returns both `Close` and `Adj Close`. For
stocks these differ — `Adj Close` is adjusted for dividends and stock splits. Futures
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
timestamps, so this never fires — but the normalisation stays in as insurance against
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

## Entry 6 — 2026-08-20 — Data quality problem found in Yahoo's gold history

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

Worst single case, 2008-09-17: reported high **808.00**, reported close **846.60** —
the close is **$38.60 above the highest price the market supposedly reached that day.**

The corruption is not spread evenly. It is concentrated at the beginning of the
sample:

```
2006: 43    2007: 37    2008: 18    2009: 4    2010: 2    2011: 10
```

### Why this matters

Every one of the eight signals is computed from the `close` column. A close outside
the day's range means that bar is simply wrong. And the densest corruption sits in
2006–2008 — exactly the years included to match CFTC data coverage.

### Decision required — currently open

Three options, and this changes a frozen parameter so it is not a judgment call to be
made quietly:

1. **Keep the full window and disclose it** in the final report as a known data
   limitation.
2. **Move the start date to 2009**, where the corruption drops to a handful of days
   per year — at the cost of losing the 2008 financial crisis, which is arguably the
   single most informative regime in the sample.
3. **Add a validation gate** in the loader that detects and either flags or repairs
   impossible bars, and document the repair rule.

**No decision made yet.** This belongs in DECISIONS.md, in its own commit.

**Also open:** whether to turn this integrity audit into a permanent test in `tests/`
so the problem cannot silently reappear or worsen after a re-download.

---

## Entry 7 — 2026-08-20 — Made the build log a standing rule

Created `CLAUDE.md` at the repo root.

**What that file is.** Claude Code automatically reads a file named `CLAUDE.md`
from the project root at the start of every session and treats its contents as
standing instructions. It is the mechanism for making a convention stick without
having to restate it each time. Nothing else reads it — it has no effect on the
Python code.

**Why it was needed.** Entries 1–6 were written retrospectively, in one batch, after
a session summary used the phrase "we did `load_yahoo`" — which meant nothing to
anyone who had not watched it being written. Writing the log after the fact is both
worse (details are already lost) and unreliable (it only happens if someone
remembers). The rule makes it part of doing the work instead.

**What the file says**, in short:

- Append to `BUILD_LOG.md` whenever anything is built, changed, decided, discovered,
  or deliberately deferred — as part of the work, not at the end.
- Write for a reader who programs competently but knows nothing about this project
  or about futures markets. Define domain terms on first use. Do not explain
  programming fundamentals.
- Never write "we did X" without saying what X is and why it exists.
- Record reasoning rather than file diffs — git already stores diffs, and cannot
  recover the reasoning.
- Be explicit when something is unverified, or is Claude's draft rather than
  Miguel's decision.
- Keep the state table and open-items list at the bottom of the log accurate.

It also restates three existing conventions so they are not lost: `DECISIONS.md` is
frozen and amended by dated append rather than edited; every strategy variant tested
goes in the trial ledger; tests are never weakened to make them pass.

**Status:** uncommitted, along with `BUILD_LOG.md` itself.

---

## Entry 8 — 2026-08-20 — Bug found in the `load_yahoo` cache check (open)

While explaining Entry 5's cache logic, a demonstration exposed a defect in the
already-committed `load_yahoo`.

**Background.** The cache file is named after the symbol only —
`yahoo_GC_F.parquet` — and carries no record of which date range it holds. Entry 5
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
| A — request starts before cached start | 2005 → 2026 | 2005 → 2026 | yes, refetched |
| B — request starts after cached start | 2006-06 → **2026** | 2006-06 → **2020** | **no** |

Case B is exactly the failure the check was supposed to prevent: ask for data
through 2026, silently receive data through 2020, with no error and no warning.

**Why it was not caught.** The verification in Entry 5 only ever called the
function with a single date range, so the cache was either absent or an exact
match. The mismatch case was never exercised.

**Why the obvious fix is wrong.** Adding `cached.index.max() >= want_end` does not
work. The last row is the last *trading day* — 2026-06-29 — while the requested end
is typically a calendar date that may be a weekend, a holiday, or in the future.
That condition would fail on essentially every call and the cache would never be
used.

The fix has to compare the *requested* window against the *previously requested*
window, which means storing the request range alongside the data — in Parquet
schema metadata, or in a small sidecar file — rather than inferring it from the
data itself.

**Status: open, unfixed.** Left for Miguel. Also needs a regression test
reproducing Case B, or the bug can silently return.

---

## Current state at a glance

| | |
|---|---|
| Commits | 3 (`2df22bf`, `649b18b`, `668c1e1`) |
| Uncommitted | `BUILD_LOG.md`, `CLAUDE.md` |
| Functions implemented | 1 of 41 |
| Tests | 1 passing, 10 failing (failing by design) |
| Linter | clean |
| Real results produced | none |

### Open items

0. **Fix the `load_yahoo` cache end-coverage bug (Entry 8) and add a regression test.**
1. Miguel to rewrite `DECISIONS.md` in his own words and defend each parameter.
2. Decide how to handle the 114+ corrupt bars in 2006–2011.
3. Record in DECISIONS.md the reasoning for starting at 2006 when data exists from 2000.
4. Decide whether the OHLC integrity audit becomes a permanent test.
5. Commit the build log and `CLAUDE.md`.

### Next piece of work

Continuing the vertical slice: the remaining loaders (`load_fred`, `load_cot`,
`load_all`), then futures roll adjustment.

Before roll adjustment gets written, the underlying concept needs to be understood
properly — it is the single largest correctness risk in the project. In outline: a
continuous futures price series is many expiring contracts glued together, and at each
join the old and new contracts trade at genuinely different prices. Glue the raw
prices together and that gap appears in the data as a price move that no trader could
ever have captured. Gold contracts further out in time are normally *more* expensive,
so these fake gaps are systematically negative — producing a persistent, entirely
artificial downward drift that looks exactly like a real market phenomenon. This
lecture has not happened yet.
