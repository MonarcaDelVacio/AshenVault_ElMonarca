"""Pure helpers for renderer rotation/cache geometry."""
import math


def quantized_sprite_angle(angle_radians, step_degrees=8):
    """Return the renderer's cached rotation angle in degrees.

    The legacy renderer quantizes sprite rotations to fixed degree buckets.
    Keeping this arithmetic centralized prevents different sprite paths from
    producing incompatible cache keys.
    """
    step = max(1, int(step_degrees))
    return int(round((-math.degrees(float(angle_radians))) / step)) * step


def quantized_facing_flip(facing_radians):
    """Return whether a sprite facing angle should be horizontally flipped."""
    return math.cos(float(facing_radians)) < 0
