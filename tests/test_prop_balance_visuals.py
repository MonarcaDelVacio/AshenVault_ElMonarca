from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from game.data import GameData
from game.sim import Sim


def test_crates_are_one_tile_and_barrels_keep_larger_radius():
    sim = Sim(GameData(), "soldier", seed=35)
    sim._spawn_room_props(sim.room)
    crates = [p for p in sim.room.props if p["kind"] == "crate"]
    barrels = [p for p in sim.room.props if p["kind"] != "crate"]
    assert all(p["radius"] == 22 for p in crates)
    assert all(p["radius"] == 24 for p in barrels)


def test_barrel_hazards_last_longer_and_emit_elemental_particles():
    sim = Sim(GameData(), "soldier", seed=36)
    for kind in ("fire", "poison", "electric"):
        prop = {"kind": kind, "x": sim.player.x + 300, "y": sim.player.y + 100,
                "hp": 1, "max_hp": 1, "broken": False, "fade": 0.0, "radius": 24}
        sim.props = [prop]
        sim._break_prop(prop)
        hazard = sim.hazards[-1]
        assert hazard["life"] == 9.0
        assert hazard["max_life"] == 9.0
        assert "particles" in hazard
        sim._update_hazards(0.2)
        assert len(hazard["particles"]) > 0


def test_room_crates_spawn_in_destructible_groups_and_fit_one_tile():
    from game.sim import TILE
    sim = Sim(GameData(), "soldier", seed=0)
    room = next(r for r in sim.dungeon.rooms.values() if r.room_type == "combat")
    sim.arena = room.arena
    sim._spawn_room_props(room)
    crates = [p for p in room.props if p["kind"] == "crate"]
    assert len(crates) >= 4
    assert all(p["radius"] <= TILE / 2 for p in crates)
    positions = {(round(p["x"] / TILE - 0.5), round(p["y"] / TILE - 0.5)) for p in crates}
    assert any((x + 1, y) in positions or (x, y + 1) in positions for x, y in positions)


def test_intact_crate_blocks_player_but_breaking_it_restores_passage():
    from game.world import TILE
    sim = Sim(GameData(), "soldier", seed=1)
    sim.props = [{"kind": "crate", "x": 13 * TILE + TILE / 2, "y": 8 * TILE + TILE / 2,
                  "hp": 2, "max_hp": 2, "broken": False, "fade": 0.0, "radius": 15}]
    x, y = sim.arena.tile_center(12, 8)
    nx, ny = sim.move_actor(x, y, TILE, 0, sim.player.radius)
    assert nx < sim.props[0]["x"]
    sim.props[0]["broken"] = True
    nx, ny = sim.move_actor(x, y, TILE, 0, sim.player.radius)
    assert nx > x


def test_open_door_transitions_automatically_without_interact_key():
    from game.sim import Input
    sim = Sim(GameData(), "soldier", seed=2)
    side = next(side for side in sim.arena.doors
                if sim.dungeon.neighbor(sim.dungeon.current, side) in sim.dungeon.rooms)
    door = sim.arena.doors[side]
    door.open = True
    tx, ty = sim.arena.tile_center(door.x, door.y)
    if side == "N": sim.player.x, sim.player.y = tx, 20
    elif side == "S": sim.player.x, sim.player.y = tx, sim.arena.height - 20
    elif side == "W": sim.player.x, sim.player.y = 20, ty
    else: sim.player.x, sim.player.y = sim.arena.width - 20, ty
    before = sim.dungeon.current
    sim.update(Input(), 0.01)
    assert sim.dungeon.current != before
    assert sim.stats["rooms"] == 2


def test_door_rendering_uses_blocked_gate_and_white_directional_arrow():
    from pathlib import Path
    source = (Path(__file__).resolve().parents[1] / "game" / "render.py").read_text(encoding="utf-8")
    assert "Puertas arquitectónicas" in source
    assert "(250,250,255)" in source
    assert "if not d.open:" in source
    assert "column_image" in source
