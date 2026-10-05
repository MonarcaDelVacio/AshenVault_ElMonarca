import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_all_weapon_definitions_have_valid_weapon_sprites():
    weapons = json.loads((ROOT / "data" / "weapons.json").read_text(encoding="utf-8"))
    assert len(weapons) >= 64
    sheet_assets = {
        "ranged": ROOT / "assets" / "weapons" / "new" / "modelosarmas.png",
        "melee": ROOT / "assets" / "weapons" / "new" / "modelosarmasmelee.png",
    }
    for weapon_id, definition in weapons.items():
        sprite = definition.get("weapon_sprite")
        sheet = definition.get("weapon_sprite_sheet")
        if sprite:
            assert (ROOT / sprite).is_file(), f"{weapon_id} references missing sprite: {sprite}"
        else:
            assert sheet in sheet_assets, f"{weapon_id} has no valid weapon sprite source"
            assert isinstance(definition.get("weapon_sprite_index"), int)
            assert definition["weapon_sprite_index"] >= 0
            assert sheet_assets[sheet].is_file(), f"{weapon_id} references missing sprite sheet: {sheet}"


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
