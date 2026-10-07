"""Pure sprite sizing helpers used by the renderer.

The helpers here intentionally know nothing about Pygame. They centralize the
math used to preserve sprite aspect ratio while fitting a maximum dimension.
"""

from __future__ import annotations


def fit_dimensions(width: int, height: int, max_dimension: float) -> tuple[int, int]:
    """Return integer dimensions preserving aspect ratio within max_dimension."""
    width = max(1, int(width))
    height = max(1, int(height))
    limit = max(1.0, float(max_dimension))
    scale = min(limit / max(width, height), 1.0)
    return max(1, int(width * scale)), max(1, int(height * scale))
