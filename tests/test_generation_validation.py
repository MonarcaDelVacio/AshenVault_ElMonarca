from game.gen import generate_layout, generate_room
from game.generation_validation import validate_layout, validate_room

def test_layout_validation_passes_for_seed_batch():
    for seed in range(32): assert validate_layout(generate_layout(seed))==[]

def test_room_validation_passes_for_seed_batch():
    for seed in range(32):
        for room_type in ("combat","elite","challenge","miniboss","boss","shop","healing","event","treasure","secret"):
            room=generate_room(seed*101+len(room_type),room_type,"ruins",("N","S","W","E"))
            assert validate_room(room)==[]

def test_room_validation_rejects_extra_perimeter_opening():
    room=generate_room(7,"combat","ruins",("N",)); room["grid"][0][0]=0
    assert "aberturas de perímetro no coinciden con las puertas" in validate_room(room)
