from itertools import combinations

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
