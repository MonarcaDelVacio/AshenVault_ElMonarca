"""Pure weapon geometry policy used by the renderer."""

from __future__ import annotations


def melee_grip_anchor(weapon_sprite: str) -> tuple[float, float]:
    """Return the normalized grip point for known melee sprite families."""
    path = str(weapon_sprite or "").lower()
    if "guadana" in path:
        return (0.20, 0.82)
    if "martillo" in path:
        return (0.19, 0.78)
    if "hacha" in path:
        return (0.18, 0.78)
    if "lanza" in path:
        return (0.17, 0.78)
    if "espada" in path:
        return (0.18, 0.79)
    return (0.18, 0.78)


def weapon_max_dimension(weapon_class: str) -> int:
    """Return the established maximum rendered weapon dimension."""
    return {
        "pistol": 29,
        "smg": 32,
        "shotgun": 34,
        "rifle": 38,
        "precision": 42,
        "machinegun": 39,
        "launcher": 37,
        "magic": 35,
        "special": 38,
        "experimental": 34,
        "melee": 37,
        "throwable": 24,
    }.get(weapon_class, 32)
