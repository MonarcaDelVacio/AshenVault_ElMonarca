import json
from pathlib import Path
import math

from game.data import GameData
from game.sim import Sim
from game.bosses import Boss

ROOT = Path(__file__).resolve().parents[1]


def test_asset_backed_enemy_types_are_in_biome_pools_and_do_not_need_weapon_ids():
    data = GameData()
    enemies = json.loads((ROOT / "data" / "enemies.json").read_text(encoding="utf-8"))
    asset_ids = {"arcane_acolyte", "gargoyle", "stone_golem", "undead_swordsman", "undead_knight", "ice_monkey", "ogre", "giant_minotaur"}
    assert asset_ids <= set(enemies)
    assert all(enemies[e].get("sprite_set") for e in asset_ids)
    assert all(not enemies[e].get("weapon_id") for e in asset_ids)
    assert all(enemies[e].get("visual_has_weapon") for e in asset_ids)
    pools = [set(b.get("enemy_pool", [])) for b in data.biomes.values()]
    assert all(any(e in pool for pool in pools) for e in asset_ids)


def test_boss_phase_two_launches_homing_fire_projectile():
    data = GameData()
    sim = Sim(data, "soldier", seed=44)
    sim.wave_delay = 99
    boss = Boss(data.bosses["warden"], sim.player.x + 180, sim.player.y, sim.rng)
    boss.phase = 2
    boss.special_counter = 2
    boss.state = "windup"
    boss.timer = 0
    sim.enemies = [boss]
    boss._attack(sim, 180)
    projectiles = [p for p in sim.pool.items if p.active and p.homing > 0]
    assert projectiles
    assert all(p.team == 1 and p.dtype == "fire" for p in projectiles)
    assert all(p.visual_scale > 1.0 for p in projectiles)


def test_heavy_asset_backed_melee_enemies_use_melee_fx_and_explosion():
    data = GameData()
    sim = Sim(data, "soldier", seed=45)
    sim.wave_delay = 99
    enemy = sim._new_enemy(data.enemies["giant_minotaur"], sim.player.x + 20, sim.player.y)
    enemy.spawn_delay = 0
    enemy.state = "windup"
    enemy.timer = 0
    sim.enemies = [enemy]
    enemy._attack(sim, 20)
    kinds = [event[0] for event in sim.events]
    assert "melee_swing" in kinds
    assert "explosion" in kinds


def test_new_entity_models_and_projectile_sheets_are_backed_by_files():
    data = GameData()
    root = ROOT / "assets" / "enemies"
    expected = {
        "skeleton": ("walk.png", "attack.png", "death.png"),
        "ghost": ("walk.png", "attack.png", "death.png", "projectile.png"),
        "goblin": ("walk.png", "attack.png", "death.png"),
        "orc": ("walk.png", "attack.png", "death.png"),
        "demon": ("walk.png", "attack.png", "death.png", "projectile.png"),
        "slime": ("walk.png", "attack.png", "death.png", "projectile.png"),
        "small_demon_assassin": ("walk.png", "attack.png", "death.png"),
        "small_demon_ranged": ("walk.png", "attack.png", "death.png", "projectile.png"),
        "small_demon_melee": ("walk.png", "attack.png", "death.png"),
        "mage2": ("idle.png",),
    }
    for sprite_set, files in expected.items():
        assert all((root / sprite_set / filename).is_file() for filename in files)
    for enemy in data.enemies.values():
        asset = getattr(enemy, "projectile_asset_sheet", None)
        if asset and asset != "minigolem_rock":
            assert (ROOT / asset).is_file()


def test_room_decoration_is_thematic_and_keeps_player_center_clear():
    data = GameData()
    sim = Sim(data, "soldier", seed=77)
    for room in sim.dungeon.rooms.values():
        for deco in room.arena.decorations:
            if deco["kind"] in {"fountain_active", "well_empty", "statue_assassin", "statue_goddess", "statue_archer", "statue_knight", "statue_mage"}:
                assert (deco["x"], deco["y"]) == (room.arena.cols // 2, room.arena.rows // 2)
            else:
                assert abs(deco["x"] - room.arena.cols // 2) + abs(deco["y"] - room.arena.rows // 2) >= 4
