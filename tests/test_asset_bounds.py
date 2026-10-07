from game.assets.bounds import DECORATION_MAX_SIZE, DECORATION_COLLISION_RADII, decoration_max_size, decoration_collision_radius


def test_decoration_size_has_single_source():
    assert decoration_max_size("statue_goddess") == 510
    assert decoration_max_size("fountain_active") == 104
    assert decoration_max_size("unknown") == 56
    assert set(DECORATION_MAX_SIZE) >= {
        "statue_goddess", "statue_archer", "statue_assassin",
        "statue_knight", "statue_mage",
    }


def test_legacy_collision_radius_is_centralized():
    assert decoration_collision_radius("rock") == 18.0
    assert decoration_collision_radius("statue_goddess") is None
    assert set(DECORATION_COLLISION_RADII) >= {"rock", "bush", "biome_shared_rock"}
