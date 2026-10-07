from game.world import Arena, FLOOR, WALL, TILE

def _arena_with_decoration():
    grid=[[FLOOR]*7 for _ in range(7)]
    for i in range(7):
        grid[0][i]=WALL
        grid[6][i]=WALL
        grid[i][0]=WALL
        grid[i][6]=WALL
    return Arena({
        "cols":7,"rows":7,"grid":grid,
        "doors":[],"player_spawn":(3,3),
        "enemy_spawns":[],"item_spawns":[],
        "room_type":"combat",
        "biome":"ruins",
        "decorations":[{"kind":"statue_goddess","x":3,"y":3,"variant":0}],
    })

def test_arena_can_skip_legacy_decoration_fallback():
    arena=_arena_with_decoration()
    x,y=arena.tile_center(3,3)
    moved_x,moved_y=arena.move(x,y,0,0,10,include_decorations=False)
    assert (moved_x,moved_y)==(x,y)

def test_arena_legacy_decoration_fallback_remains_available():
    arena=_arena_with_decoration()
    x,y=arena.tile_center(3,3)
    moved_x,moved_y=arena.move(x,y,0,0,10,include_decorations=True)
    assert (moved_x,moved_y)!=(x,y)


def test_reward_chest_is_not_a_world_collision():
    from types import SimpleNamespace
    from game.sim import Sim

    sim = object.__new__(Sim)
    sim.props = []
    sim.decoration_collider_provider = None
    sim.chest = SimpleNamespace(x=3.5 * 32, y=3.5 * 32)
    sim.arena = SimpleNamespace(decoration_hits=lambda x, y, radius: None)

    # Los cofres se interactúan por distancia; nunca forman parte de la
    # colisión física del actor aunque exista un cofre exactamente en la posición.
    assert sim._world_collision(sim.chest.x, sim.chest.y, 10.0) is False
