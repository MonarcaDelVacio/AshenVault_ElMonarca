"""Status/effect helpers extracted from Sim without changing its public API."""
import math


def freeze_duration(power):
    return max(0.45, min(3.5, 0.45 + float(power) / 18.0))


def apply_freeze(sim, target, power):
    duration = freeze_duration(power)
    if getattr(target, "is_boss", False):
        duration = min(duration, 1.2)
    elif getattr(target, "is_miniboss", False):
        duration = min(duration, 1.7)
    if hasattr(target, "frozen"):
        target.frozen = max(float(getattr(target, "frozen", 0.0)), duration)
    sim.emit("freeze", target.x, target.y, duration)


def apply_dot(sim, target, kind, duration=4.0, base_damage=1.0):
    if kind not in ("fire", "poison"):
        return
    state = getattr(target, "dot_effects", None)
    if state is None:
        state = {}
        target.dot_effects = state
    old = state.get(kind, {})
    state[kind] = {
        "time": max(float(duration), float(old.get("time", 0.0))),
        "tick": min(float(old.get("tick", 0.0)), 0.25),
        "damage": max(0.1, min(0.4, float(base_damage) * 0.12,)),
    }
    if hasattr(target, "set_status"):
        target.set_status({"fire": "burn", "poison": "poison"}[kind], duration)


def update_dot_effects(sim, dt):
    for target in [sim.player] + [e for e in sim.enemies if e.alive]:
        effects = getattr(target, "dot_effects", {})
        for kind, effect in list(effects.items()):
            effect["time"] -= dt
            effect["tick"] -= dt
            if effect["tick"] <= 0 and effect["time"] > 0:
                effect["tick"] = 0.65
                damage = min(0.4, max(0.1, float(effect.get("damage", 0.1))))
                if target is sim.player:
                    if sim.player.take_damage(damage, None):
                        sim.on_player_hit(sim.player.x, sim.player.y, damage)
                else:
                    target.hurt(damage, 0.0)
                    sim.emit("enemy_status_tick", target.x, target.y, kind, damage)
            if effect["time"] <= 0:
                effects.pop(kind, None)


def damage_shield(sim, enemy, damage, incoming_from_target, source="projectile"):
    if not getattr(enemy, "shield_active", False) or getattr(enemy, "shield_integrity", 0) <= 0:
        return False
    da = (incoming_from_target - enemy.facing + math.pi) % (2 * math.pi) - math.pi
    if abs(da) >= getattr(enemy.d, "shield_arc", 2.1) * 0.5:
        return False
    drain = max(2.0, float(damage) * 0.5)
    enemy.shield_integrity = max(0.0, enemy.shield_integrity - drain)
    if enemy.shield_integrity <= 0:
        enemy.shield_active = False
        enemy.shield_timer = 0.0
        sim.emit("shield_break", enemy.x, enemy.y, getattr(enemy.d, "color", (120, 190, 255)))
    else:
        sim.emit("projectile_block", enemy.x, enemy.y, (120, 190, 255))
    return True
