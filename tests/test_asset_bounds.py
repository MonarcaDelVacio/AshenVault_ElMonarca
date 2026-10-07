from game.assets.bounds import DECORATION_MAX_SIZE, decoration_max_size


def test_decoration_size_has_single_source():
    assert decoration_max_size("statue_goddess") == 510
    assert decoration_max_size("fountain_active") == 104
    assert decoration_max_size("unknown") == 56
    assert set(DECORATION_MAX_SIZE) >= {
        "statue_goddess", "statue_archer", "statue_assassin",
        "statue_knight", "statue_mage",
    }
