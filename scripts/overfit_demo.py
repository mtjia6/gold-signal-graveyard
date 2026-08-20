"""Stage 4: the overfitting sidecar.

Grid-search every (fast, slow) MA pair, keep the best in-sample, then show:
    1. its beautiful in-sample equity curve
    2. its collapse out-of-sample
    3. that the Deflated Sharpe, computed with n_trials = size of the grid,
       would have called it luck BEFORE you ever looked at the OOS period

That third point is the one that matters. Anyone can show an overfit curve
falling over; the claim here is that you had a test that caught it in advance.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
