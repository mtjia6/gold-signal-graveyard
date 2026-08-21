"""Run every implemented signal through the identical pipeline and adjudicate it.

    uv run python scripts/run_gauntlet.py

This is the front door. It prints the verdict table and writes reports/graveyard.md.
Everything the project can compute is computed here: execution lag, volatility
targeting, transaction costs, the in-sample/out-of-sample split, Newey-West
standard errors, the Deflated Sharpe Ratio, regime stability, and the frozen
verdict rule. Nothing of consequence lives in a scratch file.

N_TRIALS is read from the ledger in DECISIONS.md section 6 and is deliberately
NOT len(GRADED). The Deflated Sharpe must be told how many candidates were in the
running, which is the eight registered signals, not the subset implemented so far.
Setting it to the implemented count would make every verdict quietly more
flattering as work progressed, which is exactly backwards.
"""

from __future__ import annotations

from pathlib import Path

from goldgraveyard.data.loaders import load_yahoo
from goldgraveyard.engine.backtest import run_backtest, split_is_oos
from goldgraveyard.engine.costs import DEFAULT_COST_BPS, STRESS_COST_BPS
from goldgraveyard.engine.metrics import sharpe
from goldgraveyard.engine.sizing import TARGET_ANNUAL_VOL
from goldgraveyard.report.graveyard import adjudicate, to_markdown
from goldgraveyard.signals import REGISTRY
from goldgraveyard.stats.regimes import by_regime

START, END = "2006-01-01", "2026-06-30"
N_TRIALS = 8  # DECISIONS.md section 6. All eight signals are candidates.
OUT = Path(__file__).resolve().parents[1] / "reports" / "graveyard.md"

# Signals with a working implementation. The rest are stubs; listing them here
# before they exist would produce a row of NaNs that reads like a result.
GRADED = ("ma_cross", "ts_momentum", "seasonality")


def main() -> None:
    panel = load_yahoo("GC=F", START, END)
    span = f"{panel.index.min().date()} to {panel.index.max().date()}"
    print(f"panel: {panel.shape[0]} rows, {span}")
    print(f"trials for deflation: N = {N_TRIALS}\n")

    verdicts, regime_tables = [], {}

    for name in GRADED:
        signal = REGISTRY[name]

        res = run_backtest(
            signal, panel, name=name, cost_bps=DEFAULT_COST_BPS, target_vol=TARGET_ANNUAL_VOL
        )
        is_r, oos_r = split_is_oos(res.net_returns)
        _, oos_gross = split_is_oos(res.gross_returns)

        stress = run_backtest(
            signal, panel, name=name, cost_bps=STRESS_COST_BPS, target_vol=TARGET_ANNUAL_VOL
        )
        _, oos_stress = split_is_oos(stress.net_returns)

        verdicts.append(
            adjudicate(
                name=name,
                hypothesis=getattr(signal, "hypothesis", ""),
                result=res,
                is_returns=is_r,
                oos_returns=oos_r,
                oos_gross_returns=oos_gross,
                n_trials=N_TRIALS,
                oos_sharpe_stress=sharpe(oos_stress),
            )
        )
        regime_tables[name] = by_regime(res.net_returns)

    header = (
        f"{'signal':<16}{'IS':>8}{'gross':>8}{'net':>8}{'@4bp':>8}{'turn':>8}"
        f"{'HAC t':>8}{'DSR':>8}{'reg':>6}  verdict"
    )
    print(header)
    print("-" * (len(header) + 8))
    for v in sorted(verdicts, key=lambda x: -x.deflated_sr):
        print(
            f"{v.signal:<16}{v.is_sharpe:>8.3f}{v.oos_sharpe_gross:>8.3f}"
            f"{v.oos_sharpe:>8.3f}{v.oos_sharpe_stress:>8.3f}"
            f"{v.turnover:>8.2f}{v.hac_tstat:>8.2f}{v.deflated_sr:>8.3f}"
            f"{v.regimes_positive:>4}/5  {'ALIVE' if v.alive else 'DEAD'}"
        )

    n_alive = sum(v.alive for v in verdicts)
    print(f"\n{n_alive} of {len(verdicts)} survived.\n")
    for v in verdicts:
        if not v.alive:
            print(f"  {v.signal:<16} died of: {v.cause_of_death}")

    to_markdown(
        verdicts,
        OUT,
        n_trials=N_TRIALS,
        sample=span,
        cost_bps=DEFAULT_COST_BPS,
        stress_bps=STRESS_COST_BPS,
        target_vol=TARGET_ANNUAL_VOL,
        regime_tables=regime_tables,
    )
    print(f"\nwrote {OUT.relative_to(Path.cwd()) if OUT.is_relative_to(Path.cwd()) else OUT}")


if __name__ == "__main__":
    main()
