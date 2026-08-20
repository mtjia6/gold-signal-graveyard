# The Gold Signal Graveyard

**One honest evaluation framework, eight well-known gold signals, and a cause of death for each.**

The deliverable is not a winning strategy. It is a demonstration that real alpha can be
told apart from fake alpha — which is the thing the job actually is. A null result is a
win here: if most of these signals die, the project succeeded.

> **Status:** scaffolding. No results yet. Nothing in `reports/` is real until it is.

---

## The claim

Most retail backtests find alpha because they are broken in one of five specific ways.
This repo is built so that all five are impossible by construction, and then runs eight
signals that traders genuinely believe through it:

| Bug | Where it is prevented |
|---|---|
| Un-adjusted futures roll → phantom contango drift | [`data/roll.py`](src/goldgraveyard/data/roll.py) |
| Same-bar signal and execution | [`engine/backtest.py`](src/goldgraveyard/engine/backtest.py) — one-bar lag, no exceptions |
| COT release-lag lookahead | [`signals/cot.py`](src/goldgraveyard/signals/cot.py) — conditions on release date, not report date |
| Comparing unequal risk | [`engine/sizing.py`](src/goldgraveyard/engine/sizing.py) — every signal vol-targeted to 10 % |
| Multiple testing | [`stats/deflated_sharpe.py`](src/goldgraveyard/stats/deflated_sharpe.py) |

Plus autocorrelation-aware inference in [`stats/hac.py`](src/goldgraveyard/stats/hac.py),
because overlapping strategy returns make naive t-stats lie upward.

Everything that could be tuned is frozen in advance in **[DECISIONS.md](DECISIONS.md)**,
committed before the first result.

## The verdict rule

> **ALIVE** = positive out-of-sample return net of costs **and** Deflated Sharpe > 0.95
> **and** the sign holds in ≥ 2 of 5 regimes. Everything else is **DEAD**.

## Layout

```
src/goldgraveyard/
  types.py        the two contracts everything obeys
  data/           loaders + futures back-adjustment
  engine/         backtest, vol targeting, costs, metrics
  signals/        eight signal functions, one per file, self-registering
  stats/          Newey-West, Deflated Sharpe, regime stability
  report/         graveyard table and figures
scripts/          fetch_data → run_gauntlet → overfit_demo
tests/            engine invariants (currently red, by design)
DECISIONS.md      pre-registration: frozen params, regimes, verdict rule, trial ledger
```

## Running it

```bash
uv sync
uv run pytest
uv run python scripts/fetch_data.py
uv run python scripts/run_gauntlet.py
```

## Data

All free. Gold `GC=F`, silver `SI=F`, dollar `DX-Y.NYB` via yfinance; 10-year TIPS
`DFII10` via FRED; CFTC disaggregated Commitments of Traders for the COT signal.

## Build order

1. Engine + `ma_cross` end to end, with costs and an OOS split — plumbing first
2. The statistical gauntlet: Newey–West, then Deflated Sharpe
3. The remaining seven signals — they are just different `signal()` functions
4. The overfitting sidecar
5. The graveyard table and the autopsies
