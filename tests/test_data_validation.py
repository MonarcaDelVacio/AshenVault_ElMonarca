"""Cross-file JSON data graph regression tests."""

import json
from pathlib import Path

from game.data_validation import validate_data_graph


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def load_json(name):
    return json.loads((DATA / f"{name}.json").read_text(encoding="utf-8"))


def test_runtime_data_graph_has_no_broken_references():
    graph = {
        "weapons": load_json("weapons"),
        "enemies": load_json("enemies"),
        "characters": load_json("characters"),
        "bosses": load_json("bosses"),
        "biomes": load_json("biomes"),
        "biome_bosses": {
            "ruins": "warden",
            "forest": "thorn_matron",
            "dungeon": "iron_judge",
            "laboratory": "null_archon",
            "volcanic": "pyre_colossus",
            "final": "ashen_regent",
            "desert": "warden",
            "swamp": "thorn_matron",
        },
    }
    assert validate_data_graph(graph) == []


def test_data_graph_rejects_unknown_character_weapon():
    graph = {
        "weapons": {"pistol": {"class": "pistol", "projectile_sprite": "x", "magazine": 1}},
        "enemies": {},
        "characters": {"hero": {"start_weapon": "missing"}},
        "bosses": {},
        "biomes": {},
        "biome_bosses": {},
    }
    errors = validate_data_graph(graph)
    assert any("start_weapon=missing" in error for error in errors)


def test_data_graph_rejects_unknown_boss_summon():
    graph = {
        "weapons": {"pistol": {"class": "pistol", "projectile_sprite": "x", "magazine": 1}},
        "enemies": {},
        "characters": {},
        "bosses": {
            "boss": {
                "sprite_set": "boss",
                "summon_ids": ["missing"],
                "phases": [{"summon_ids": ["missing_phase"]}],
            }
        },
        "biomes": {},
        "biome_bosses": {},
    }
    errors = validate_data_graph(graph)
    assert any("summon_ids=missing" in error for error in errors)
    assert any("summon_ids=missing_phase" in error for error in errors)


def test_data_graph_rejects_invalid_weapon_contract():
    graph = {
        "weapons": {"broken": {"class": "pistol", "magazine": 0, "fire_interval": -1}},
        "enemies": {},
        "characters": {},
        "bosses": {},
        "biomes": {},
        "biome_bosses": {},
    }
    errors = validate_data_graph(graph)
    assert any("magazine inválido" in error for error in errors)
    assert any("fire_interval inválido" in error for error in errors)


def test_data_graph_rejects_invalid_enemy_sprite_set():
    graph = {
        "weapons": {},
        "enemies": {"bad": {"sprite_set": 123}},
        "characters": {},
        "bosses": {},
        "biomes": {},
        "biome_bosses": {},
    }
    errors = validate_data_graph(graph)
    assert any("sprite_set inválido" in error for error in errors)

def test_data_graph_rejects_enemy_without_sprite_set():
    graph = {
        "weapons": {},
        "enemies": {"bad": {}},
        "characters": {},
        "bosses": {},
        "biomes": {},
        "biome_bosses": {},
    }
    errors = validate_data_graph(graph)
    assert any("falta sprite_set" in error for error in errors)


def test_data_graph_rejects_unknown_synergy_requirement():
    graph = {
        "weapons": {"pistol": {"class": "pistol", "projectile_sprite": "x", "magazine": 1}},
        "enemies": {}, "characters": {}, "bosses": {}, "biomes": {}, "biome_bosses": {},
        "arenas": {}, "rooms": {}, "chests": {}, "items": {"known": {"effects": {}}},
        "modifiers": {}, "synergies": {"bad": {"requires": ["missing"]}},
        "shops": {},
    }
    errors = validate_data_graph(graph)
    assert any("requisito desconocido requires=missing" in error for error in errors)


def test_data_graph_rejects_invalid_shop_items():
    graph = {
        "weapons": {"pistol": {"class": "pistol", "projectile_sprite": "x", "magazine": 1}},
        "enemies": {}, "characters": {}, "bosses": {}, "biomes": {}, "biome_bosses": {},
        "arenas": {}, "rooms": {}, "chests": {}, "items": {}, "modifiers": {}, "synergies": {},
        "shops": {"items": [{"kind": "heal", "price": -1, "amount": 2}]},
    }
    errors = validate_data_graph(graph)
    assert any("shop 0: price inválido" in error for error in errors)


def test_data_graph_rejects_unknown_arena_biome():
    graph = {
        "weapons": {"pistol": {"class": "pistol", "projectile_sprite": "x", "magazine": 1}},
        "enemies": {}, "characters": {}, "bosses": {},
        "biomes": {}, "biome_bosses": {}, "arenas": {"arena": {"biome": "missing"}},
        "rooms": {}, "chests": {}, "items": {}, "modifiers": {}, "synergies": {}, "shops": {},
    }
    errors = validate_data_graph(graph)
    assert any("arena arena: bioma desconocido missing" in error for error in errors)


def test_data_graph_rejects_duplicate_enemy_variant_ids():
    graph = {
        "weapons": {}, "enemies": {}, "characters": {}, "bosses": {}, "biomes": {}, "biome_bosses": {},
        "arenas": {}, "rooms": {}, "chests": {}, "items": {}, "modifiers": {}, "synergies": {}, "shops": {},
        "enemy_variants": {"families": {"goblin": [{"id": "same"}, {"id": "same"}]}},
    }
    errors = validate_data_graph(graph)
    assert any("id duplicado same" in error for error in errors)


def test_data_graph_rejects_invalid_enemy_variant_asset_field():
    graph = {
        "weapons": {}, "enemies": {}, "characters": {}, "bosses": {}, "biomes": {}, "biome_bosses": {},
        "arenas": {}, "rooms": {}, "chests": {}, "items": {}, "modifiers": {}, "synergies": {}, "shops": {},
        "enemy_variants": {"families": {"golem": [{"id": "bomb", "projectile_asset_sheet": 123}]}},
    }
    errors = validate_data_graph(graph)
    assert any("projectile_asset_sheet inválido" in error for error in errors)
