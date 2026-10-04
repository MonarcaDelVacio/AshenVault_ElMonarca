"""Habilidades activas de personajes. Mantiene la lógica fuera de pygame para tests."""
import math


def use_ability(sim):
    p = sim.player
    if p.ability_cd > 0 or not p.alive:
        return False
    a = getattr(p, "ability", p.c.ability)
    ability_mult = getattr(p, "statue_ability_mult", 1.0)
    kind = a.get("kind", "none")
    if kind == "heal":
        amount = a.get("amount", 2) * ability_mult
        if p.hp >= p.max_hp and p.shield >= p.max_shield:
            return False
        p.hp = min(p.max_hp, p.hp + amount)
        sim.emit("ability_heal", p.x, p.y, amount)
    elif kind == "shield":
        amount = a.get("amount", 4) * ability_mult
        p.shield = min(p.max_shield, p.shield + amount)
        p.invuln = max(p.invuln, a.get("invuln", 0.8))
        p.ability_shield_fx = max(p.ability_shield_fx, a.get("invuln", 0.8) * ability_mult)
        sim.emit("ability_shield", p.x, p.y)
    elif kind == "burst":
        radius = a.get("radius", 120) * (0.9 + 0.1*ability_mult)
        damage = a.get("damage", 18) * p.damage_mult * ability_mult
        hits = 0
        for e in sim.enemies:
            if math.hypot(e.x - p.x, e.y - p.y) <= radius:
                if e.alive:
                    e.hurt(damage, math.atan2(e.y - p.y, e.x - p.x))
                    hits += 1
        sim.emit("ability_burst", p.x, p.y, radius, hits)
    elif kind == "haste":
        p.ability_buff = max(p.ability_buff, a.get("duration", 5.0) * ability_mult)
        sim.emit("ability_haste", p.x, p.y)
    elif kind == "freeze":
        duration = a.get("duration", 2.5) * ability_mult
        for e in sim.enemies:
            if math.hypot(e.x - p.x, e.y - p.y) <= a.get("radius", 180) * (0.9 + 0.1*ability_mult):
                e.frozen = max(getattr(e, "frozen", 0.0), duration)
        sim.emit("ability_freeze", p.x, p.y)
    elif kind == "drone":
        p.drones = min(getattr(p, "drones", 0) + 1, a.get("max_drones", 2))
        sim.emit("ability_drone", p.x, p.y, p.drones)
    else:
        return False
    p.ability_cd = a.get("cooldown", 8.0)
    sim.stats["abilities"] += 1
    return True
