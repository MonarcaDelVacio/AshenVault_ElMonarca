"""Phase 14 stress tests.

The stress suite deliberately exercises bounded pools, high entity counts,
long-running simulation updates, projectile/laser pressure, drone pressure,
and repeated procedural dungeon construction. It does not change gameplay
behavior and is designed to expose runaway allocations, stale entities,
NaNs, and state leaks before cleanup/final audit.
"""
import math
import os

import pytest


def test_projectile_pool_survives_repeated_full_pressure():
    from game.data import GameData
    from game.sim import Input, Sim

    sim = Sim(GameData(), "soldier", seed=14001)
    sim.player.invuln = 999.0
    sim.wave_delay = 99.0

    for cycle in range(24):
        for n in range(600):
            angle = (n % 96) * (math.tau / 96.0)
            sim.spawn_projectile(
                0,
                sim.player.x,
                sim.player.y,
                angle,
                700.0,
                2.0,
                2.5,
                0.45,
                (220, 220, 220),
                "physical",
                0,
                0,
                False,
            )
        sim.update(Input(), 1.0 / 60.0)

        assert len(sim.pool.items) == 600
        assert sum(1 for p in sim.pool.items if p.active) <= 600

    assert sim.player.alive
    assert sim.stats["damage_taken"] == 0


def test_many_enemies_can_update_without_non_finite_state():
    from game.data import GameData
    from game.sim import Input, Sim

    sim = Sim(GameData(), "soldier", seed=14002)
    sim.player.invuln = 999.0
    sim.wave_delay = 99.0

    definition = next(iter(sim.data.enemies.values()))
    for n in range(72):
        a = math.tau * n / 72.0
        x = sim.player.x + math.cos(a) * 230.0
        y = sim.player.y + math.sin(a) * 150.0
        safe = sim._safe_npc_position(x, y, float(definition.radius))
        if safe is None:
            continue
        sim.enemies.append(sim._new_enemy(definition, *safe))

    for _ in range(180):
        sim.update(Input(), 1.0 / 60.0)

    assert sim.player.alive
    for e in sim.enemies:
        assert math.isfinite(e.x)
        assert math.isfinite(e.y)
        assert math.isfinite(e.hp)
        assert math.isfinite(e.kx)
        assert math.isfinite(e.ky)


def test_mira_drone_stress_keeps_entities_bounded_and_finite():
    from game.data import GameData
    from game.sim import Input, Sim

    sim = Sim(GameData(), "engineer", seed=14003)
    sim.player.invuln = 999.0
    sim.player.ability_cd = 0.0

    for _ in range(8):
        sim.spawn_drone((_ * math.tau) / 8.0)

    for _ in range(900):
        sim.update(Input(), 1.0 / 60.0)

    assert len(sim.drones) <= 8
    for d in sim.drones:
        assert math.isfinite(d["x"])
        assert math.isfinite(d["y"])
        assert math.isfinite(d["hp"])
        assert d["lifetime"] > 0.0


def test_laser_stress_with_many_targets_remains_finite():
    from game.data import GameData
    from game.sim import Input, Sim
    from game.weapons import WeaponState

    sim = Sim(GameData(), "soldier", seed=14004)
    sim.player.invuln = 999.0
    sim.player.weapon = WeaponState(sim.data.weapons["prism_beam"])
    sim.player.energy = sim.player.max_energy

    definition = next(iter(sim.data.enemies.values()))
    for n in range(48):
        a = math.tau * n / 48.0
        safe = sim._safe_npc_position(
            sim.player.x + math.cos(a) * 260.0,
            sim.player.y + math.sin(a) * 180.0,
            float(definition.radius),
        )
        if safe is not None:
            sim.enemies.append(sim._new_enemy(definition, *safe))

    inp = Input()
    inp.aim_x = sim.player.x + 500.0
    inp.aim_y = sim.player.y
    inp.fire_held = True

    for _ in range(180):
        sim.update(inp, 1.0 / 60.0)

    assert math.isfinite(sim.player.energy)
    assert all(
        math.isfinite(float(l["angle"])) and math.isfinite(float(l["charge"]))
        for l in sim.lasers
    )


def test_procedural_dungeons_repeat_without_state_corruption():
    from game.data import GameData
    from game.world import Dungeon

    data = GameData()
    generated = []

    for seed in range(14010, 14040):
        dungeon = Dungeon(seed, None, 1)
        assert dungeon.rooms
        assert dungeon.room is not None
        assert dungeon.room.arena is not None
        assert dungeon.room.arena.width > 0
        assert dungeon.room.arena.height > 0
        generated.append((seed, len(dungeon.rooms)))

    assert len(generated) == 30
    assert all(count > 0 for _, count in generated)


def test_long_simulation_does_not_accumulate_unbounded_event_state():
    from game.data import GameData
    from game.sim import Input, Sim

    sim = Sim(GameData(), "soldier", seed=14005)
    sim.player.invuln = 999.0

    for _ in range(3600):
        sim.update(Input(), 1.0 / 60.0)

    assert sim.time >= 59.0
    assert len(sim.events) <= 250
    assert sim.player.alive
    assert math.isfinite(sim.player.x)
    assert math.isfinite(sim.player.y)
