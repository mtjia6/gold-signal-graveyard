"""Stage 3: run every registered signal through the identical pipeline.

    uv run python scripts/run_gauntlet.py

Currently runs the vertical slice only: one signal, end to end, to prove the
machine works. The remaining seven plug in unchanged once they are written.

The trial count handed to the Deflated Sharpe step must include every variant
run during development, not just len(REGISTRY). Track it in DECISIONS.md.
"""

from __future__ import annotations

from goldgraveyard.data.loaders import load_yahoo
from goldgraveyard.engine.backtest import run_backtest, split_is_oos
from goldgraveyard.engine.costs import DEFAULT_COST_BPS, STRESS_COST_BPS
from goldgraveyard.engine.metrics import sharpe
from goldgraveyard.engine.sizing import TARGET_ANNUAL_VOL
from goldgraveyard.signals import REGISTRY

START, END = "2006-01-01", "2026-06-30"
SLICE_SIGNALS = ("ma_cross",)


def main() -> None:
    panel = load_yahoo("GC=F", START, END)
    span = f"{panel.index.min().date()} to {panel.index.max().date()}"
    print(f"panel: {panel.shape[0]} rows, {span}\n")

    header = f"{'signal':<16}{'IS':>8}{'OOS':>8}{'turnover':>10}{'OOS @4bp':>10}"
    print(header)
    print("-" * len(header))

    for name in SLICE_SIGNALS:
        res = run_backtest(
            REGISTRY[name], panel,
            name=name, cost_bps=DEFAULT_COST_BPS, target_vol=TARGET_ANNUAL_VOL,
        )
        is_r, oos_r = split_is_oos(res.net_returns)

        stress = run_backtest(
            REGISTRY[name], panel,
            name=name, cost_bps=STRESS_COST_BPS, target_vol=TARGET_ANNUAL_VOL,
        )
        _, oos_stress = split_is_oos(stress.net_returns)

        print(
            f"{name:<16}{sharpe(is_r):>8.3f}{sharpe(oos_r):>8.3f}"
            f"{res.turnover:>10.2f}{sharpe(oos_stress):>10.3f}"
        )


if __name__ == "__main__":
    main()
