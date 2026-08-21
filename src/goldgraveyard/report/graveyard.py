"""Assemble the verdict table.

The verdict rule is frozen in DECISIONS.md and implemented ONCE, here. It is
not allowed to become "well, this one is close enough".
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..engine.backtest import BacktestResult
from ..engine.metrics import sharpe
from ..stats.deflated_sharpe import deflated_sharpe
from ..stats.hac import newey_west_tstat
from ..stats.regimes import count_positive_regimes

DSR_THRESHOLD = 0.95  # Frozen. DECISIONS.md section 5.
MIN_POSITIVE_REGIMES = 2  # Frozen.


@dataclass(frozen=True)
class Verdict:
    signal: str
    hypothesis: str
    is_sharpe: float
    oos_sharpe: float
    oos_sharpe_stress: float
    hac_tstat: float
    deflated_sr: float
    regimes_positive: int
    turnover: float
    alive: bool
    cause_of_death: str


def adjudicate(
    name: str,
    hypothesis: str,
    result: BacktestResult,
    is_returns: pd.Series,
    oos_returns: pd.Series,
    n_trials: int,
    oos_sharpe_stress: float,
) -> Verdict:
    """Apply the frozen ALIVE rule to one signal's results.

    ALIVE requires ALL of:
        1. net-of-cost OOS mean return > 0
        2. Deflated Sharpe > 0.95
        3. mean-return sign positive in >= 2 of the 5 regimes

    Anything else is DEAD, and cause_of_death names the FIRST condition failed.

    Everything is judged on the OUT OF SAMPLE, NET-OF-COST series. The in-sample
    figure is reported for context and has no bearing on the verdict, because a
    number computed on data used during development is optimistically biased by
    an amount nobody can estimate.

    No appeals. A signal missing a threshold by a hair is dead. A rule that can
    be relaxed once its result is known is not evidence of anything.
    """
    hac_t, _, _ = newey_west_tstat(oos_returns)
    dsr = deflated_sharpe(oos_returns, n_trials=n_trials)
    n_regimes = count_positive_regimes(result.net_returns)

    conditions = [
        (oos_returns.mean() > 0, "negative out-of-sample return, net of costs"),
        (dsr > DSR_THRESHOLD, f"deflated Sharpe {dsr:.3f}, below the {DSR_THRESHOLD} bar"),
        (
            n_regimes >= MIN_POSITIVE_REGIMES,
            f"positive in only {n_regimes} of 5 regimes",
        ),
    ]
    failures = [why for ok, why in conditions if not ok]

    return Verdict(
        signal=name,
        hypothesis=hypothesis,
        is_sharpe=sharpe(is_returns),
        oos_sharpe=sharpe(oos_returns),
        oos_sharpe_stress=oos_sharpe_stress,
        hac_tstat=hac_t,
        deflated_sr=dsr,
        regimes_positive=n_regimes,
        turnover=result.turnover,
        alive=not failures,
        cause_of_death="" if not failures else failures[0],
    )


def to_markdown(
    verdicts: list[Verdict],
    out: Path,
    *,
    n_trials: int,
    sample: str,
    cost_bps: float,
    stress_bps: float,
    target_vol: float,
    regime_tables: dict[str, pd.DataFrame] | None = None,
) -> None:
    """Write the graveyard report: headline table, verdict rule, per-signal autopsies.

    The caveats section is not decoration. A report that states its results
    without stating what they rest on is the thing this project exists to argue
    against.
    """
    out.parent.mkdir(parents=True, exist_ok=True)
    alive = [v for v in verdicts if v.alive]

    lines = [
        "# The Gold Signal Graveyard",
        "",
        f"**{len(alive)} of {len(verdicts)} signals survived.**",
        "",
        f"Sample: {sample}. Every signal vol-targeted to {target_vol:.0%} annualized, "
        f"charged {cost_bps:.0f} bp round trip, executed with a one-bar lag.",
        f"Deflated Sharpe computed at N = {n_trials} trials "
        "(see DECISIONS.md section 6 for the ledger).",
        "",
        "## Verdict rule, frozen before any result was computed",
        "",
        "> ALIVE requires all three:",
        "> 1. positive out-of-sample return, net of costs;",
        f"> 2. Deflated Sharpe above {DSR_THRESHOLD};",
        f"> 3. mean return positive in at least {MIN_POSITIVE_REGIMES} of 5 regimes.",
        ">",
        "> Everything else is DEAD. Cause of death is the first condition failed.",
        "",
        "## The table",
        "",
        "| Signal | IS Sharpe | OOS Sharpe | OOS @stress | Turnover | HAC t | Deflated SR "
        "| Regimes | Verdict |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for v in sorted(verdicts, key=lambda x: -x.deflated_sr):
        lines.append(
            f"| `{v.signal}` | {v.is_sharpe:+.3f} | {v.oos_sharpe:+.3f} "
            f"| {v.oos_sharpe_stress:+.3f} | {v.turnover:.2f} | {v.hac_tstat:+.2f} "
            f"| {v.deflated_sr:.3f} | {v.regimes_positive}/5 "
            f"| {'**ALIVE**' if v.alive else 'DEAD'} |"
        )

    lines += ["", f"OOS @stress is the same signal charged {stress_bps:.0f} bp instead of "
              f"{cost_bps:.0f} bp.", "", "## Autopsies", ""]
    for v in sorted(verdicts, key=lambda x: -x.deflated_sr):
        lines += [
            f"### `{v.signal}`",
            "",
            f"**Hypothesis, stated before testing:** {v.hypothesis}",
            "",
            f"**Verdict: {'ALIVE' if v.alive else 'DEAD'}**"
            + ("" if v.alive else f", cause of death: {v.cause_of_death}."),
            "",
            f"Out of sample it returned a Sharpe of {v.oos_sharpe:+.3f} over "
            f"{v.turnover:.1f} units of annual turnover, with a Newey-West t-statistic of "
            f"{v.hac_tstat:+.2f}. Deflated against {n_trials} trials the Sharpe is "
            f"{v.deflated_sr:.3f}, meaning "
            + (
                "it clears the bar the luckiest of those trials would have set."
                if v.deflated_sr > DSR_THRESHOLD
                else f"there is a {1 - v.deflated_sr:.0%} chance a set of worthless "
                "strategies would have produced something this good by selection alone."
            )
            + f" The mean return was positive in {v.regimes_positive} of 5 frozen regimes.",
            "",
        ]
        if regime_tables and v.signal in regime_tables:
            t = regime_tables[v.signal]
            lines += [
                "| Regime | n | Annualized mean | Sharpe |",
                "|---|---|---|---|",
                *[
                    f"| {i} | {int(r['n'])} | {r['ann_mean']:+.4f} | {r['sharpe']:+.3f} |"
                    for i, r in t.iterrows()
                ],
                "",
            ]

    lines += [
        "## What these numbers rest on",
        "",
        "Stated because a result reported without its caveats is the failure mode this "
        "project exists to argue against.",
        "",
        "- **The futures series is not roll-adjusted.** `data/roll.py` is unimplemented. "
        "A continuous gold series spliced from expiring contracts carries a phantom "
        "price gap at every roll, systematically negative under contango, which no "
        "position could have earned. Until this is fixed every figure above is "
        "measuring gold plus an artifact.",
        "- **Yahoo's early gold data is corrupt.** 114 bars have a close above the "
        "session high and 116 below the low, concentrated in 2006 to 2011. See "
        "BUILD_LOG.md Entry 6.",
        "- **Condition 3 is weak and partly measures gold rather than the signal.** "
        "Gold's own returns are positive in the same 4 of 5 regimes, so any long-biased "
        "signal tends to pass. `mean > 0` is also a knife edge: one regime qualifies on "
        "an annualized mean of half a basis point. See BUILD_LOG.md Entry 21.",
        "- **N is the one input that cannot be audited from outside.** The ledger in "
        "DECISIONS.md is dated and was filled before these numbers were computed.",
        "",
        "*Generated by `scripts/run_gauntlet.py`. Do not edit by hand.*",
        "",
    ]
    out.write_text("\n".join(lines))
