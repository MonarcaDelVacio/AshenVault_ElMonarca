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


DECORATION_COLLISION_RADII = {
    "rock": 18.0, "bush": 16.0, "bench_small": 22.0, "bench_large": 28.0,
    "barrel_large": 18.0, "signpost": 13.0, "table": 25.0, "counter": 30.0,
    "crate_stack": 28.0, "crate_pair": 24.0, "wood_chest_decor": 20.0,
    "biome_red_bush": 18.0, "biome_lava_rock": 24.0,
    "biome_lava_rock_purple": 24.0, "biome_shared_rock": 22.0,
    "fountain_active": 24.0, "fountain_inactive": 24.0, "fountain_small": 18.0,
    "well_empty": 24.0,
}

def decoration_max_size(kind: str) -> int:
    return DECORATION_MAX_SIZE.get(str(kind), 56)

def decoration_collision_radius(kind: str) -> float | None:
    value = DECORATION_COLLISION_RADII.get(str(kind))
    return float(value) if value is not None else None
