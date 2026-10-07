"""Phase 13 integration tests.

These tests exercise the seams between the validated data graph, procedural world,
simulation systems, combat/projectiles, abilities, and the pygame renderer.
They intentionally avoid starting the interactive App so CI/headless execution
does not depend on a desktop session.
"""
import importlib
import math
import os

import pytest


def _headless_pygame():
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
    import pygame
    pygame.init()
    if not pygame.display.get_init():
        pygame.display.init()
    if not pygame.display.get_surface():
        pygame.display.set_mode((960, 540))
    return pygame


def test_application_module_imports_without_starting_runtime():
    module = importlib.import_module("main")
    assert hasattr(module, "App")
    assert hasattr(module, "main")


def test_data_to_renderer_contract_is_loadable():
    pygame = _headless_pygame()
    try:
        from game.data import GameData
        from game.render import Renderer

        data = GameData()
        renderer = Renderer(data)

        assert len(data.weapons) >= 50
        assert data.characters
        assert data.enemies
        assert data.bosses
        assert data.asset_registry is not None
        assert renderer.enemy_sprites
        assert renderer.player_walk_frames
    finally:
        pygame.quit()


def test_each_playable_character_can_construct_and_advance_simulation():
    from game.data import GameData
    from game.sim import Input, Sim

    data = GameData()
    for index, char_id in enumerate(data.characters):
        sim = Sim(data, char_id, seed=100 + index)
        sim.player.invuln = 999.0
        inp = Input()
        inp.aim_x = sim.player.x + 120.0
        inp.aim_y = sim.player.y
        inp.move_x = 0.35
        inp.move_y = -0.2
        inp.fire_held = True

        for _ in range(90):
            sim.update(inp, 1.0 / 60.0)
            inp.clear_edges()

        assert sim.time > 1.0
        assert sim.player.alive
        assert sim.arena is sim.room.arena
        assert len(sim.pool.items) == 600


def test_cross_system_combat_ability_and_laser_lifecycle():
    from game.abilities import use_ability
    from game.data import GameData
    from game.sim import Input, Sim
    from game.weapons import WeaponState

    data = GameData()
    sim = Sim(data, "engineer", seed=31337)
    sim.player.invuln = 999.0

    # Ability -> drone system -> simulation update.
    sim.player.ability_cd = 0.0
    assert use_ability(sim) is True
    assert len(sim.drones) >= 1
    for _ in range(60):
        sim.update(Input(), 1.0 / 60.0)
    assert sim.drones

    # Data weapon -> WeaponState -> Sim combat -> laser state.
    laser = WeaponState(data.weapons["prism_beam"])
    sim.player.weapon = laser
    sim.player.inventory[sim.player.selected_slot] = laser
    sim.player.energy = sim.player.max_energy
    inp = Input()
    inp.aim_x = sim.player.x + 500.0
    inp.aim_y = sim.player.y
    inp.fire_held = True

    for _ in range(75):  # 1.25 s: crosses the one-second laser activation threshold.
        sim.update(inp, 1.0 / 60.0)

    assert sim.player.energy < sim.player.max_energy
    assert any(l.get("owner") is sim.player for l in sim.lasers)

    inp.fire_held = False
    sim.update(inp, 1.0 / 60.0)
    assert not any(l.get("owner") is sim.player for l in sim.lasers)


def test_projectile_pool_and_room_state_remain_integrated_under_load():
    from game.data import GameData
    from game.sim import Input, Sim

    sim = Sim(GameData(), "soldier", seed=4242)
    sim.player.invuln = 999.0
    sim.wave_delay = 99.0

    for n in range(180):
        angle = (n % 24) * (math.tau / 24.0)
        sim.spawn_projectile(
            0,
            sim.player.x,
            sim.player.y,
            angle,
            420.0,
            4.0,
            3.0,
            1.0,
            (255, 255, 255),
            "physical",
            0,
            0,
            False,
        )

    for _ in range(120):
        sim.update(Input(), 1.0 / 60.0)

    assert len(sim.pool.items) == 600
    assert sim.room is sim.dungeon.room
    assert sim.arena is sim.room.arena
    assert sim.player.alive
    assert sim.stats["damage_taken"] == 0


def test_final_room_completion_and_portal_transition_integrate_with_difficulty():
    from game.data import GameData
    from game.sim import Input, Sim

    sim = Sim(GameData(), "soldier", seed=9090)
    final = next(
        room for room in sim.dungeon.rooms.values()
        if room.room_type == "boss" and room.arena.biome == "final"
    )
    sim.dungeon.current = final.id
    sim._enter_room(final)
    sim.enemies.clear()
    final.cleared = False

    sim._complete_room()
    assert sim.portal is True
    assert final.portal_room is True

    old_difficulty = sim.difficulty
    sim.player.x, sim.player.y = sim.portal_position
    inp = Input()
    inp.interact_pressed = True
    sim.update(inp, 1.0 / 60.0)

    assert sim.portal is False
    assert sim.difficulty == old_difficulty + 1
    assert sim.room.room_type == "start"
