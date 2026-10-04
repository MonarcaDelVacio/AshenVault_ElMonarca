import math
import random
from types import SimpleNamespace

from game.data import GameData
from game.enemies import Enemy
from game.bosses import Boss
from game.sim import Input, Sim


def make_sim(seed=417):
    data = GameData()
    return data, Sim(data, next(iter(data.characters)), seed=seed)


def test_summoned_minions_do_not_drop_coins_or_loot():
    data, sim = make_sim()
    minion = Enemy(data.enemies["grunt"], sim.player.x + 70, sim.player.y, sim.rng)
    minion.is_summoned = True
    minion.alive = False
    sim.enemies = [minion]
    sim.pickups.clear()
    sim.items.clear()

    sim.update(Input(), 1 / 60)

    assert sim.pickups == []
    assert sim.items == []


def test_summons_spawn_in_walkable_space_near_a_wall():
    data, sim = make_sim()
    sim.enemies.clear()
    source = SimpleNamespace(x=44.0, y=sim.arena.height / 2, radius=32)

    assert sim.spawn_summons(source, ["grunt", "runner"], 3)
    summoned = [e for e in sim.enemies if e.is_summoned]
    assert summoned
    for enemy in summoned:
        assert enemy.radius < enemy.x < sim.arena.width - enemy.radius
        assert enemy.radius < enemy.y < sim.arena.height - enemy.radius
        assert not sim.arena.box_hits(enemy.x, enemy.y, enemy.radius * 0.85)
        assert not sim._crate_collision(enemy.x, enemy.y, enemy.radius * 0.85)
        assert math.hypot(enemy.x - source.x, enemy.y - source.y) >= source.radius + enemy.radius + 7


def test_projectile_and_melee_hits_deplete_front_shield_before_health():
    data, sim = make_sim()
    enemy = Enemy(data.enemies["shield_guard"], sim.player.x + 100, sim.player.y, random.Random(1))
    enemy.facing = 0.0
    start_hp = enemy.hp
    start_shield = enemy.shield_integrity

    assert sim._damage_shield(enemy, 8, 0.0, "projectile")
    assert enemy.shield_integrity < start_shield
    assert enemy.hp == start_hp

    enemy.shield_integrity = 1.0
    assert sim._damage_shield(enemy, 8, 0.0, "melee")
    assert enemy.shield_integrity == 0
    assert not sim._damage_shield(enemy, 8, 0.0, "projectile")

    enemy.hurt(8, 0.0)
    assert enemy.hp == start_hp - 8


def test_boss_styles_have_distinct_spacing_and_only_specialists_summon():
    data, sim = make_sim()
    expected_spacing = {
        "warden": 245,
        "thorn_matron": 285,
        "iron_judge": 105,
        "null_archon": 355,
        "pyre_colossus": 135,
        "ashen_regent": 175,
    }
    assert len(set(expected_spacing.values())) == len(expected_spacing)

    commander = Boss(data.bosses["warden"], sim.player.x + 120, sim.player.y, sim.rng)
    commander.spawn_delay = 0
    sim.enemies = [commander]
    sim.update(Input(), 1 / 60)
    assert sim.count_summoned() == 0

    summoner = Boss(data.bosses["thorn_matron"], sim.player.x + 180, sim.player.y, sim.rng)
    summoner.spawn_delay = 0
    summoner.summon_timer = 0
    sim.enemies = [summoner]
    sim.update(Input(), 1 / 60)
    assert sim.count_summoned() > 0


def test_colossus_stomp_windup_emits_real_shockwave_and_visual_event():
    data = GameData()
    sim = Sim(data, "soldier", seed=81)
    boss = Boss(data.bosses["pyre_colossus"], sim.player.x + 220, sim.player.y, sim.rng)
    boss.phase = 2
    boss.state = "windup"
    boss._special_windup = "stomp"
    sim.enemies = [boss]
    boss._attack(sim, 220)
    assert sim.wave_attacks
    assert sim.wave_attacks[-1]["damage"] > 0
    assert any(event[0] == "boss_stomp" for event in sim.events)
