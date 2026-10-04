from game.data import GameData
from game.gen import generate_room
from game.world import Arena, TILE
from game.sim import Sim


def test_special_statue_is_centered_and_not_used_as_random_combat_decor():
    for room_type in ("combat", "elite", "boss", "secret", "treasure"):
        room=generate_room(123, room_type, "ruins", ["N","S","E","W"])
        statues=[d for d in room["decorations"] if d["kind"].startswith("statue_")]
        if room_type == "secret":
            assert len(statues)==1
            assert (statues[0]["x"],statues[0]["y"])==(12,8)
        else:
            assert not statues


def test_decoration_has_physical_collision_and_does_not_overlap_spawn():
    room=generate_room(321,"secret","ruins",["N","S"])
    arena=Arena(room)
    assert arena.decoration_colliders
    assert not arena.decoration_hits(*arena.player_spawn, 10)
    statue=next(d for d in room["decorations"] if d["kind"]=="statue_assassin")
    sx,sy=arena.tile_center(statue["x"],statue["y"])
    assert arena.decoration_hits(sx,sy,10)
    x,y=arena.move(arena.player_spawn[0],arena.player_spawn[1],(sx-arena.player_spawn[0])*0.9,(sy-arena.player_spawn[1])*0.9,10)
    assert ((x-sx)**2+(y-sy)**2)**0.5 >= 40


def test_decorations_are_reserved_from_enemy_and_item_spawn_tiles():
    room=generate_room(987,"combat","forest",["N","S","E","W"])
    deco={(d["x"],d["y"]) for d in room["decorations"]}
    assert not deco.intersection(set(room["enemy_spawns"]))
    assert not deco.intersection(set(room["item_spawns"]))


def test_render_source_does_not_draw_legacy_circle_for_sprite_backed_enemies():
    source=(__import__('pathlib').Path(__file__).resolve().parents[1]/'game'/'render.py').read_text()
    assert 'if not has_sprite and not getattr(e.d, "sprite_set", None):' in source
    assert 'if not getattr(e.d, "sprite_set", None):\n                ex, ey' in source


def test_floor_families_are_biome_specific():
    source=(__import__('pathlib').Path(__file__).resolve().parents[1]/'game'/'render.py').read_text()
    for biome in ("ruins","forest","dungeon","laboratory","volcanic","final"):
        assert f'"{biome}":' in source


def test_all_grounded_scene_objects_share_the_same_y_depth_pass():
    source=open("game/render.py",encoding="utf-8").read()
    assert 'actors.append((float(prop.get("y", 0)), "prop", prop))' in source
    assert 'actors.append((float(chest.y), "chest", chest))' in source
    assert 'actors.append((float(sim.portal_position[1]), "portal", sim.portal_position))' in source
    assert 'elif kind=="prop":' in source
    assert 'elif kind=="chest":' in source
    assert 'elif kind=="portal":' in source


def test_bonfires_and_decorations_are_physical_colliders():
    from game.sim import Sim
    from game.data import GameData
    d = GameData()
    sim = Sim(d, "soldier", seed=9)
    from game.world import bonfire_positions
    bonfires = bonfire_positions(sim.arena)
    assert bonfires
    bx, by = bonfires[0]
    assert sim.arena.decoration_hits(bx, by, 4)
    assert sim._world_collision(bx, by, 4)


def test_projectiles_hit_scene_decorations_instead_of_passing_through():
    from game.sim import Sim
    from game.data import GameData
    d = GameData()
    sim = Sim(d, "soldier", seed=9)
    from game.world import bonfire_positions
    bx, by = bonfire_positions(sim.arena)[0]
    pr = sim.spawn_projectile(0, bx - 36, by, 0.0, 300, 5, 3, 1.0, (255,255,255), "physical")
    sim._update_projectiles(0.12)
    assert not pr.active
