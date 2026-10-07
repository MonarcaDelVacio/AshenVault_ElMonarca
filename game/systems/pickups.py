"""Pickup simulation helpers extracted from Sim without changing its public API."""

import math


def update_pickups(sim, dt):
    """Magnetizes and collects coin pickups while preserving Sim state semantics."""
    p = sim.player
    kept = []
    for pickup in sim.pickups:
        if pickup.get("kind") != "coin":
            kept.append(pickup)
            continue

        dx = pickup["x"] - p.x
        dy = pickup["y"] - p.y
        dist = math.hypot(dx, dy)
        magnet = 64.0 + float(getattr(p, "coin_radius", 0))

        if dist <= magnet:
            pickup_radius = float(pickup.get("radius", 7.0))
            collect_radius = float(getattr(p, "radius", 10.0)) + pickup_radius
            if dist > collect_radius:
                pull = 520.0 * dt
                step = min(dist - collect_radius, max(0.0, pull))
                if dist > 0.001:
                    pickup["x"] -= dx / dist * step
                    pickup["y"] -= dy / dist * step
                kept.append(pickup)
                continue

            p.coins += 1
            sim.stats["coins"] += 1
            sim.emit("coin_pickup", pickup["x"], pickup["y"], 1)
        else:
            kept.append(pickup)

    sim.pickups = kept
