"""Figures. Kept separate so no analysis code ever imports matplotlib."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def equity_curve(returns: pd.Series, title: str, out: Path, *, oos_start=None) -> None:
    """Cumulative net return, with the IS/OOS boundary marked."""
    raise NotImplementedError


def overfit_demo_figure(is_curve: pd.Series, oos_curve: pd.Series, out: Path) -> None:
    """The mic-drop chart: gorgeous in-sample, flat-to-down out-of-sample."""
    raise NotImplementedError
