"""Shared visual-bound sizing rules for world decorations.

These values are presentation geometry, not gameplay stats. Keeping them in one
place prevents the renderer and its collision provider from using different
scales for the same PNG.
"""

DECORATION_MAX_SIZE = {
    "fountain_active": 104,
    "fountain_inactive": 104,
    "fountain_small": 68,
    "well_empty": 104,
    "bench_large": 92,
    "bench_small": 66,
    "barrel_large": 62,
    "signpost": 70,
    "crate_stack": 76,
    "crate_pair": 68,
    "table": 72,
    "counter": 84,
    "wood_chest_decor": 68,
    "statue_goddess": 510,
    "statue_archer": 510,
    "statue_assassin": 510,
    "statue_knight": 510,
    "statue_mage": 510,
    "bush": 56,
    "rock": 58,
    "biome_red_bush": 86,
    "biome_lava_rock": 88,
    "biome_lava_rock_purple": 82,
    "biome_shared_rock": 88,
}


def decoration_max_size(kind: str) -> int:
    return DECORATION_MAX_SIZE.get(str(kind), 56)
