from types import SimpleNamespace

from game.systems.hazards import update_hazards


class Player:
    def __init__(self, x=0.0, y=0.0):
        self.x = x
        self.y = y
        self.damage_taken = 0.0
        self.statuses = []

    def take_damage(self, damage, direction):
        self.damage_taken += damage
        return True

    def set_status(self, status, duration):
        self.statuses.append((status, duration))


class Enemy:
    def __init__(self, enemy_id=1, x=20.0, y=0.0):
        self.id = enemy_id
        self.x = x
        self.y = y
        self.radius = 10.0
        self.alive = True
        self.damage_taken = 0.0
        self.stunned = 0.0
        self.confused = 0.0

    def hurt(self, damage, direction):
        self.damage_taken += damage


class Arena:
    def tile_of(self, x, y):
        return (int(x // 32), int(y // 32))


class SimStub:
    def __init__(self):
        self.player = Player()
        self.enemies = []
        self.drones = []
        self.props = []
        self.hazards = []
        self.wave_attacks = []
        self.rng = __import__("random").Random(1)
        self.arena = Arena()
        self.events = []
        self.dots = []
        self.freezes = []
        self.drone_damage = []

    def _apply_dot(self, target, kind, duration, damage):
        self.dots.append((target, kind, duration, damage))

    def _apply_freeze(self, target, duration):
        self.freezes.append((target, duration))

    def _wave_clear_to(self, *args):
        return True

    def damage_drone(self, drone, damage, x, y):
        self.drone_damage.append((drone, damage, x, y))

    def on_player_hit(self, x, y, damage):
        self.events.append(("player_hit", x, y, damage))

    def emit(self, *event):
        self.events.append(event)


def test_fire_hazard_damages_player_and_applies_dot():
    sim = SimStub()
    sim.player.x = 5.0
    sim.hazards = [{"life": 1.0, "tick": 0.0, "particle_timer": 99.0,
                    "dtype": "fire", "x": 0.0, "y": 0.0, "radius": 20.0, "damage": 3.0}]
    update_hazards(sim, 0.1)
    assert sim.player.damage_taken == 3.0
    assert sim.dots == [(sim.player, "fire", 4.0, 3.0)]
    assert sim.events[-1] == ("player_hit", 0.0, 0.0, 3.0)


def test_electric_hazard_damages_drone():
    sim = SimStub()
    drone = {"x": 4.0, "y": 0.0}
    sim.drones = [drone]
    sim.hazards = [{"life": 1.0, "tick": 0.0, "particle_timer": 99.0,
                    "dtype": "electric", "x": 0.0, "y": 0.0, "radius": 10.0, "damage": 2.0}]
    update_hazards(sim, 0.1)
    assert sim.drone_damage == [(drone, 2.0, 0.0, 0.0)]


def test_expanding_enemy_wave_hits_enemy_once_and_tracks_hit_id():
    sim = SimStub()
    enemy = Enemy()
    sim.enemies = [enemy]
    wave = {"life": 1.0, "x": 0.0, "y": 0.0, "radius": 0.0, "speed": 200.0,
            "damage": 5.0, "team": 0}
    sim.wave_attacks = [wave]
    update_hazards(sim, 0.1)
    assert enemy.damage_taken == 5.0
    assert enemy.id in wave["hit_ids"]
    update_hazards(sim, 0.01)
    assert enemy.damage_taken == 5.0


def test_freeze_wave_uses_freeze_effect_without_damage():
    sim = SimStub()
    enemy = Enemy(x=10.0)
    sim.enemies = [enemy]
    wave = {"life": 1.0, "x": 0.0, "y": 0.0, "radius": 0.0, "speed": 100.0,
            "damage": 99.0, "team": 0, "effect": "freeze", "freeze_duration": 2.5}
    sim.wave_attacks = [wave]
    update_hazards(sim, 0.1)
    assert enemy.damage_taken == 0.0
    assert sim.freezes == [(enemy, 2.5)]
