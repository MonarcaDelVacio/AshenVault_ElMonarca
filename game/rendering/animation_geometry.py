"""Pure animation timing helpers for renderer frame selection."""


def animation_frame_index(elapsed, frame_count, duration, loop=False):
    """Return the frame index for an elapsed animation time."""
    count = max(0, int(frame_count))
    if count <= 0:
        return 0
    duration = max(0.001, float(duration))
    index = int(max(0.0, float(elapsed)) * count / duration)
    return index % count if loop else min(count - 1, index)
