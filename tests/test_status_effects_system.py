from game.systems.status_effects import freeze_duration, apply_dot, update_dot_effects


class Target:
    def __init__(self):
        self.x = 10.0
        self.y = 20.0
        self.alive = True
        self.dot_effects = {}
        self.statuses = []
        self.hp = 20.0

    def set_status(self, kind, duration):
        self.statuses.append((kind, duration))

    def hurt(self, amount, angle):
        self.hp -= amount


class Player(Target):
    def take_damage(self, amount, angle):
        self.hp -= amount
        return True


class SimStub:
    def __init__(self):
        self.player = Player()
        self.enemies = []
        self.events = []

    def emit(self, *event):
        self.events.append(event)

    def on_player_hit(self, *args):
        self.events.append(("player_hit",) + args)


def test_freeze_duration_preserves_established_limits():
    assert freeze_duration(0) == 0.45
    assert freeze_duration(18) == 1.45
    assert freeze_duration(1000) == 3.5


def test_dot_refreshes_duration_and_preserves_stronger_damage():
    sim = SimStub()
    target = Target()
    apply_dot(sim, target, "fire", 4.0, 10.0)
    first = dict(target.dot_effects["fire"])
    apply_dot(sim, target, "fire", 2.0, 20.0)
    current = target.dot_effects["fire"]
    assert current["time"] == first["time"]
    assert current["damage"] == 0.4
    assert target.statuses[-1][0] == "burn"


def test_dot_update_damages_enemy_and_expires():
    sim = SimStub()
    enemy = Target()
    sim.enemies = [enemy]
    apply_dot(sim, enemy, "poison", 0.7, 4.0)
    update_dot_effects(sim, 0.3)
    assert enemy.hp < 20.0
    update_dot_effects(sim, 0.5)
    assert "poison" not in enemy.dot_effects
