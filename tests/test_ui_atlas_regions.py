from game.ui_atlas import UIAtlas


def test_hud_regions_match_current_1536x1128_atlas():
    regions = UIAtlas.REGIONS

    assert regions["hud_usar"] == (480, 505, 243, 63)
    assert regions["hud_recargar"] == (485, 577, 232, 45)
    assert regions["hud_interactuar"] == (485, 632, 232, 45)
    assert regions["hud_recoger"] == (486, 686, 231, 45)

    assert regions["icon_health"] == (1106, 510, 56, 48)
    assert regions["icon_shield"] == (1167, 509, 61, 48)
    assert regions["icon_energy"] == (1231, 510, 57, 48)

    assert regions["bar_health"] == (1106, 558, 225, 51)
    assert regions["bar_shield"] == (1107, 611, 224, 45)
    assert regions["bar_energy"] == (1108, 665, 224, 42)


def test_mana_is_not_part_of_the_hud_atlas():
    assert "bar_mana" not in UIAtlas.REGIONS
    assert "track_mana" not in UIAtlas.REGIONS
