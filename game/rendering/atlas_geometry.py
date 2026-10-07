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

def split_grid_frames(surface, cols: int, rows: int, *, alpha_threshold: int = 8):
    """Split a regular atlas into trimmed frames without importing Pygame."""
    if cols <= 0 or rows <= 0:
        return []
    width, height = surface.get_width(), surface.get_height()
    if width % cols or height % rows:
        return []
    cell_w, cell_h = width // cols, height // rows
    frames = []
    frame_index = 0
    for row in range(rows):
        for col in range(cols):
            source_rect = (col * cell_w, row * cell_h, cell_w, cell_h)
            cell = surface.subsurface(source_rect).copy()
            bbox = cell.get_bounding_rect(min_alpha=alpha_threshold)
            if bbox.width and bbox.height:
                frame = cell.subsurface(bbox).copy()
                frames.append((frame_index, source_rect, bbox, frame))
            frame_index += 1
    return frames
