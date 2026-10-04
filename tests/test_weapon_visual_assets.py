import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_weapon_definitions_have_valid_weapon_sprites():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    assert len(weapons) == 58
    for weapon_id, definition in weapons.items():
        sprite = definition.get("weapon_sprite")
        assert sprite, f"{weapon_id} has no weapon sprite"
        assert (ROOT / sprite).is_file(), f"{weapon_id} references missing sprite: {sprite}"


def test_every_ranged_weapon_has_a_projectile_sprite_and_melee_does_not():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    for weapon_id, definition in weapons.items():
        projectile = definition.get("projectile_sprite")
        if definition.get("class") == "melee":
            assert not projectile, f"{weapon_id} is melee but has a projectile sprite"
        else:
            assert projectile, f"{weapon_id} has no projectile sprite"
            assert (ROOT / projectile).is_file(), f"{weapon_id} references missing projectile: {projectile}"


def test_healing_and_energy_sprites_exist():
    assert (ROOT / "assets" / "misc" / "healing.png").is_file()
    assert (ROOT / "assets" / "misc" / "energy.png").is_file()
