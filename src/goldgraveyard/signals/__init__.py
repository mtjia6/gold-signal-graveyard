"""The eight corpses.

Every signal here obeys CONTRACT 1 in goldgraveyard.types: it maps the panel to
a desired position in [-1, +1] at the close of each day, and does nothing else.
No lag, no vol scaling, no costs -- the engine owns those.

Registration is explicit so that the count of trials in the Deflated Sharpe
step can never silently drift away from the count of signals actually run.
"""

from __future__ import annotations

from ..types import SignalFn

REGISTRY: dict[str, SignalFn] = {}


def register(name: str, hypothesis: str, requires: tuple[str, ...] = ()):
    """Decorator: add a signal to the gauntlet, with its hypothesis stated up front."""

    def wrap(fn: SignalFn) -> SignalFn:
        fn.name = name           # type: ignore[attr-defined]
        fn.hypothesis = hypothesis  # type: ignore[attr-defined]
        fn.requires = requires   # type: ignore[attr-defined]
        REGISTRY[name] = fn
        return fn

    return wrap


def _load_all() -> None:
    """Import every signal module so its @register decorator executes.

    Without this the REGISTRY is empty: defining a signal in a module that nobody
    imports registers nothing. Done at the bottom of this file, after `register`
    exists, because each module imports `register` from here.

    Explicit imports rather than a directory scan, so that adding a file is a
    deliberate act. The Deflated Sharpe step needs an honest count of signals, and
    a magic auto-discovery would let that count drift without anyone noticing.
    """
    from . import (  # noqa: F401
        carry,
        cot,
        dollar,
        gold_silver,
        ma_cross,
        momentum,
        real_yield,
        seasonality,
    )


_load_all()
