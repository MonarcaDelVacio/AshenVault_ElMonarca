"""Pure helpers for atlas geometry and alpha projections.

This module intentionally has no Pygame dependency. It is safe to unit-test
independently and can be used by both legacy and future renderer components.
"""

from __future__ import annotations

from collections.abc import Iterable


def alpha_runs(values: Iterable[bool]) -> list[tuple[int, int]]:
    """Return inclusive contiguous ranges of truthy alpha projection values."""
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for index, active in enumerate(values):
        if active and start is None:
            start = index
        elif not active and start is not None:
            runs.append((start, index - 1))
            start = None
    if start is not None:
        runs.append((start, index))
    return runs
