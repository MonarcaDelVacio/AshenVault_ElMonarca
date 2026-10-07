from types import SimpleNamespace

from game.systems import combat


class Pool:
    def __init__(self):
        self.calls = []

    def spawn(self, *args):
        self.calls.append(args)
        return "projectile"


def test_spawn_projectile_keeps_pool_contract():
    sim = SimpleNamespace(pool=Pool())
    assert combat.spawn_projectile(sim, 0, 1, 2, 3) == "projectile"
    assert sim.pool.calls == [(0, 1, 2, 3)]


def test_melee_attack_hits_only_inside_arc():
    player = SimpleNamespace(
        x=100.0, y=100.0, radius=10.0, aim=0.0,
        damage_mult=1.0, weapon=SimpleNamespace(damage_mult=1.0),
        statue_melee_mult=1.0,
    )
    target = SimpleNamespace(
        alive=True, x=125.0, y=100.0, max_hp=100.0, hp=100.0,
        radius=10.0, is_boss=False, is_miniboss=False,
        kx=0.0, ky=0.0, d=SimpleNamespace(
            range=35.0, melee_arc=1.8, damage=10.0,
            melee_level=1, damage_type="physical", color=(1, 2, 3),
        ),
        hurt=lambda damage, angle: setattr(target, "hp", target.hp - damage),
    )
    sim = SimpleNamespace(
        player=player, enemies=[target], props=[], rng=SimpleNamespace(random=lambda: 1.0),
        events=[], _damage_shield=lambda *args: False,
        _break_prop=lambda *args: None,
        emit=lambda *event: sim.events.append(event),
    )

    combat.perform_melee_attack(sim, player, target.d)

    assert target.hp < 100.0
    assert sim.events[-1][0] == "melee_hit"


def test_projectile_hit_consumes_non_piercing_projectile():
    projectile = SimpleNamespace(
        active=True, hit_ids=set(), x=100.0, y=100.0, radius=3.0,
        damage=12.0, vx=100.0, vy=0.0, explosive=False,
        status_chance=0.0, dtype="physical", pierce=0, stick_on_hit=False,
        crit=False,
    )
    target = SimpleNamespace(
        id=1, alive=True, spawn_delay=0.0, x=101.0, y=100.0,
        radius=10.0, hp=40.0, max_hp=40.0, is_boss=False,
        hurt=lambda damage, angle: setattr(target, "hp", target.hp - damage),
    )
    sim = SimpleNamespace(
        enemies=[target], rng=SimpleNamespace(random=lambda: 1.0),
        events=[], _damage_shield=lambda *args: False,
        emit=lambda *event: sim.events.append(event),
    )

    assert combat._hit_enemies(sim, projectile) is True
    assert projectile.active is False
    assert target.hp == 28.0
    assert projectile.hit_ids == {1}


def test_player_laser_drains_energy_and_creates_beam_state():
    weapon = SimpleNamespace(
        d=SimpleNamespace(
            laser_energy_per_second=20.0,
            color=(10, 20, 30),
            laser_damage=15.0,
            laser_width=2.0,
            laser_max_width=14.0,
            laser_range=700.0,
            laser_explosion_radius=20.0,
        ),
        laser_active=True,
    )
    player = SimpleNamespace(
        weapon=weapon, energy=100.0, damage_mult=1.0, aim=0.0,
        since_shot=99.0, x=50.0, y=50.0,
    )
    sim = SimpleNamespace(
        player=player, lasers=[], events=[],
        stop_player_laser=lambda: None,
        emit=lambda *event: sim.events.append(event),
    )

    combat.update_player_laser(sim, 2.0, 0.5)

    assert player.energy == 90.0
    assert player.since_shot == 0.0
    assert len(sim.lasers) == 1
    assert sim.lasers[0]["charge"] == 2.0
    assert sim.lasers[0]["damage"] == 15.0
