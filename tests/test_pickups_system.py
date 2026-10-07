from game.systems.pickups import update_pickups


class Player:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
        self.radius = 10.0
        self.coin_radius = 0
        self.coins = 0


class SimStub:
    def __init__(self):
        self.player = Player()
        self.pickups = []
        self.stats = {"coins": 0}
        self.events = []

    def emit(self, *event):
        self.events.append(event)


def test_coin_outside_magnet_range_does_not_move():
    sim = SimStub()
    sim.pickups = [{"kind": "coin", "x": 100.0, "y": 0.0, "radius": 7.0}]
    update_pickups(sim, 0.1)
    assert sim.pickups[0]["x"] == 100.0
    assert sim.player.coins == 0


def test_coin_is_attracted_within_two_block_range():
    sim = SimStub()
    sim.pickups = [{"kind": "coin", "x": 60.0, "y": 0.0, "radius": 7.0}]
    update_pickups(sim, 0.05)
    assert sim.pickups[0]["x"] < 60.0
    assert sim.player.coins == 0


def test_coin_is_collected_when_it_reaches_player():
    sim = SimStub()
    sim.pickups = [{"kind": "coin", "x": 12.0, "y": 0.0, "radius": 7.0}]
    update_pickups(sim, 0.1)
    assert sim.pickups == []
    assert sim.player.coins == 1
    assert sim.stats["coins"] == 1
    assert sim.events == [("coin_pickup", 12.0, 0.0, 1)]


def test_coin_radius_upgrade_extends_magnet_range():
    sim = SimStub()
    sim.player.coin_radius = 40
    sim.pickups = [{"kind": "coin", "x": 90.0, "y": 0.0, "radius": 7.0}]
    update_pickups(sim, 0.05)
    assert sim.pickups[0]["x"] < 90.0
