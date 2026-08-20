"""Stage 3: run every registered signal through the identical pipeline.

    uv run python scripts/run_gauntlet.py

Writes reports/graveyard.md and reports/figures/*.png.

The trial count handed to the Deflated Sharpe step must include every variant
you ran during development, not just len(REGISTRY). Track it in DECISIONS.md.
"""

from __future__ import annotations


def main() -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
