import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_fast_weapons_are_lower_damage_than_slow_heavy_weapons():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    assert weapons["volt_smg"]["damage"] < 5
    assert weapons["arc_minigun"]["damage"] < 11
    assert weapons["needle_rifle"]["damage"] > weapons["volt_smg"]["damage"]


def test_shotguns_have_deliberate_cadence_and_multiple_pellets():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    for weapon in weapons.values():
        if weapon.get("class") == "shotgun":
            assert weapon["fire_interval"] >= 0.72
            assert weapon.get("auto") is False
            assert weapon.get("pellets", 1) >= 5


def test_all_lances_and_bows_are_chargeable_and_stick_on_impact():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    launchables = [w for w in weapons.values() if w.get("name", "").lower().startswith(("lanza ", "arco "))]
    assert launchables
    for weapon in launchables:
        assert weapon.get("charged_projectile") is True
        assert weapon.get("stick_on_hit") is True
        assert weapon.get("charge_max") == 3.0
        assert weapon.get("projectile_sprite")
    assert weapons["longbow_lumen"]["projectile_sprite"] == "assets/projectiles/projectile_05.png"


def test_ranged_enemy_weapon_assignments_are_valid_and_varied():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    enemies = json.loads((ROOT / "data" / "enemies.json").read_text(encoding="utf-8"))
    assigned = [e.get("weapon_id") for e in enemies.values() if e.get("weapon_id")]
    assert len(assigned) >= 7
    assert len(set(assigned)) >= 5
    assert all(weapon_id in weapons for weapon_id in assigned)
