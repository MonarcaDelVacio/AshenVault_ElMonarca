from types import SimpleNamespace

from game.systems import drones


def test_spawn_drone_uses_ability_stats_and_registers_it():
    player = SimpleNamespace(x=100.0, y=100.0, ability={"drone_hp": 23}, drones=[])
    sim = SimpleNamespace(
        player=player,
        drones=[],
        rng=SimpleNamespace(random=lambda: 0.25),
        _safe_drone_position=lambda x, y, radius: (x, y),
    )
    drone = drones.spawn_drone(sim, 0.0)
    assert drone["hp"] == 23.0
    assert drone["max_hp"] == 23.0
    assert sim.drones == [drone]
    assert player.drones is sim.drones


def test_damage_drone_caps_single_hit_and_destroys_when_depleted():
    drone = {"x": 20.0, "y": 30.0, "hp": 10.0, "max_hp": 10.0}
    events = []
    sim = SimpleNamespace(
        drones=[drone],
        emit=lambda *event: events.append(event),
    )
    assert drones.damage_drone(sim, drone, 100.0) is True
    assert drone["hp"] == 5.8
    assert drone in sim.drones
    assert events[-1][0] == "drone_hit"


def test_drone_update_fires_at_nearest_enemy_when_ready():
    drone = {"x": 100.0, "y": 100.0, "radius": 10.0, "hp": 18.0,
             "max_hp": 18.0, "shot_cd": 0.0, "burst_cd": 0.0,
             "phase": 0.0, "orbit": 0.0, "orbit_speed": 0.28,
             "orbit_radius": 82.0, "idle_phase": 0.0,
             "stuck_time": 0.0, "repath_time": 0.0,
             "avoid_x": 0.0, "avoid_y": 0.0, "vx": 0.0, "vy": 0.0}
    player = SimpleNamespace(x=100.0, y=100.0, ability={"drone_attack_interval": 1.0, "drone_damage_mult": 1.0}, damage_mult=1.0, alive=True, drones=[])
    enemy = SimpleNamespace(alive=True, spawn_delay=0.0, x=180.0, y=100.0)
    calls = []
    arena = SimpleNamespace(width=600.0, height=400.0, box_hits=lambda *a: False)
    sim = SimpleNamespace(
        player=player, drones=[drone], enemies=[enemy], hazards=[], pool=SimpleNamespace(items=[]),
        arena=arena, rng=SimpleNamespace(random=lambda: 0.1),
        _world_collision=lambda *a: False,
        _drone_collision=lambda *a: False,
        _drone_path_clear=lambda *a: True,
        move_actor=lambda x, y, dx, dy, radius: (x + dx, y + dy),
        spawn_projectile=lambda *args: calls.append(args),
    )
    drones.update_drones(sim, 0.1)
    assert calls
    assert calls[0][0] == 0
    assert calls[0][9] == "physical"
