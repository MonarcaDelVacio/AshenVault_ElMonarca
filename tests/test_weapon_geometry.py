from game.rendering.weapon_geometry import melee_grip_anchor, weapon_max_dimension


def test_melee_grip_anchor_uses_known_weapon_families():
    assert melee_grip_anchor("assets/weapons/guadana.png") == (0.20, 0.82)
    assert melee_grip_anchor("assets/weapons/espada_larga.png") == (0.18, 0.79)
    assert melee_grip_anchor("unknown_weapon.png") == (0.18, 0.78)


def test_weapon_max_dimension_preserves_existing_policy():
    assert weapon_max_dimension("pistol") == 29
    assert weapon_max_dimension("precision") == 42
    assert weapon_max_dimension("melee") == 37
    assert weapon_max_dimension("unknown") == 32
