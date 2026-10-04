from game.data import GameData
from game.enemies import Enemy
from game.sim import Input, Sim


def test_breaking_crate_has_low_total_loot_probability():
    sim = Sim(GameData(), "soldier", seed=101)
    crate = {"kind": "crate", "x": sim.player.x + 80, "y": sim.player.y,
             "hp": 1, "max_hp": 1, "broken": False, "fade": 0.0, "radius": 15}
    sim.props = [crate]
    sim.rng.random = lambda: 0.99
    sim._break_prop(crate)
    assert sim.items == []
    assert sim.pickups == []


def test_normal_enemy_can_die_without_coin_drop():
    data = GameData()
    sim = Sim(data, "soldier", seed=102)
    enemy = Enemy(data.enemies["grunt"], sim.player.x + 80, sim.player.y, sim.rng)
    enemy.alive = False
    sim.enemies = [enemy]
    sim.pickups.clear()
    sim.rng.random = lambda: 0.99
    sim.update(Input(), 1 / 60)
    assert sim.pickups == []


def test_boss_always_drops_its_coin_reward():
    data = GameData()
    sim = Sim(data, "soldier", seed=103)
    boss = Enemy(data.enemies["grunt"], sim.player.x + 80, sim.player.y, sim.rng)
    boss.is_boss = True
    boss.alive = False
    sim.enemies = [boss]
    sim.pickups.clear()
    sim.update(Input(), 1 / 60)
    assert len(sim.pickups) == boss.d.coins
