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
