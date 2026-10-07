from game.gen import generate_layout, generate_room
from game.generation_validation import validate_layout, validate_room, validate_dungeon
from game.world import Dungeon


ROOM_TYPES = ("combat","elite","challenge","miniboss","boss","shop","healing","event","treasure","secret")
DOOR_SETS = (
    ("N",), ("S",), ("W",), ("E",),
    ("N","S"), ("W","E"), ("N","E"), ("N","W"), ("S","E"), ("S","W"),
    ("N","S","E"), ("N","S","W"), ("N","E","W"), ("S","E","W"),
    ("N","S","E","W"),
)


def test_layout_validation_passes_for_large_seed_batch():
    for seed in range(128):
        assert validate_layout(generate_layout(seed)) == []


def test_room_validation_passes_for_large_seed_and_door_batch():
    for seed in range(64):
        for room_type in ROOM_TYPES:
            for door_sides in DOOR_SETS:
                room = generate_room(
                    seed * 101 + len(room_type),
                    room_type,
                    "ruins",
                    door_sides,
                )
                assert validate_room(room) == []


def test_dungeon_validation_passes_for_seed_batch():
    for seed in range(64):
        assert validate_dungeon(Dungeon(seed)) == []


def test_room_validation_rejects_extra_perimeter_opening():
    room = generate_room(7, "combat", "ruins", ("N",))
    room["grid"][0][0] = 0
    assert "aberturas de perímetro no coinciden con las puertas" in validate_room(room)

def test_dungeon_bosses_are_not_spatially_adjacent():
    for seed in range(128):
        dungeon = Dungeon(seed)
        bosses = [rid for rid, room in dungeon.rooms.items() if room.room_type == "boss"]
        assert len(bosses) == 6
        for i, rid in enumerate(bosses):
            for other in bosses[i + 1:]:
                assert abs(rid[0] - other[0]) + abs(rid[1] - other[1]) > 1


def test_generation_validator_treats_pillars_as_solid():
    room = generate_room(3, "combat", "ruins", ("N",))
    pillar = next(
        ((x, y) for y, row in enumerate(room["grid"]) for x, value in enumerate(row) if value in (2, 4)),
        None,
    )
    assert pillar is not None
    from game.generation_validation import _walkable_tiles
    assert pillar not in _walkable_tiles(room)

def test_dungeon_room_doors_match_topology():
    for seed in range(64):
        dungeon = Dungeon(seed)
        for rid, room in dungeon.rooms.items():
            for side, delta in {"N":(0,-1),"S":(0,1),"W":(-1,0),"E":(1,0)}.items():
                neighbor=(rid[0]+delta[0],rid[1]+delta[1])
                assert (side in room.arena.doors) == (neighbor in dungeon.rooms)


def test_room_validation_rejects_decoration_over_player_spawn():
    room = generate_room(11, "combat", "ruins", ("N",))
    room["decorations"] = [{"kind":"rock","x":room["player_spawn"][0],"y":room["player_spawn"][1],"variant":0}]
    assert "decoración invade el spawn del jugador" in validate_room(room)
