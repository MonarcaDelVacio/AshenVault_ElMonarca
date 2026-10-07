"""Regression coverage for room-local state lifecycle."""

from types import SimpleNamespace

from game.systems.rewards import open_chest


class _Chest:
    def __init__(self):
        self.x = 10.0
        self.y = 20.0
        self.chest_type = "common"
        self.is_open = False

    def open(self):
        if self.is_open:
            return False
        self.is_open = True
        return True


class _Rng:
    def choice(self, values):
        return values[0]


def test_open_chest_consumes_room_chest_reference():
    chest = _Chest()
    sim = SimpleNamespace(
        chest=chest,
        room=SimpleNamespace(chest=chest),
        player=SimpleNamespace(inventory=[]),
        data=SimpleNamespace(weapons={}),
        rng=_Rng(),
        items=[],
        stats={"items": 0},
        events=[],
    )
    sim.emit = lambda *args: sim.events.append(args)

    assert open_chest(sim) is True
    assert chest.is_open is True
    assert sim.chest is None
    assert sim.room.chest is None


def test_open_chest_without_room_reference_remains_compatible():
    chest = _Chest()
    sim = SimpleNamespace(
        chest=chest,
        room=SimpleNamespace(),
        player=SimpleNamespace(inventory=[]),
        data=SimpleNamespace(weapons={}),
        rng=_Rng(),
        items=[],
        stats={"items": 0},
        events=[],
    )
    sim.emit = lambda *args: sim.events.append(args)

    assert open_chest(sim) is True
    assert sim.chest is None
