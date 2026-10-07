"""Regression tests for pure logical UI layout helpers."""

from game.ui_layout import (
    menu_rects,
    settings_volume_rect,
    settings_sensitivity_rect,
    settings_binding_rect,
    settings_fullscreen_rect,
    settings_reset_rect,
    settings_back_rect,
)


def test_menu_layout_contract():
    assert menu_rects("menu", 3) == [
        (388, 220, 184, 42),
        (388, 277, 184, 42),
        (388, 334, 184, 42),
    ]
    assert menu_rects("pause", 4)[0] == (375, 190, 210, 52)
    assert menu_rects("other", 2) == []


def test_settings_layout_contract():
    row, bar = settings_volume_rect(1)
    assert row == (126, 214, 266, 45)
    assert bar == (244, 231, 120, 8)
    assert settings_sensitivity_rect() == ((126, 257, 266, 74), (145, 307, 228, 8))
    assert settings_binding_rect(2) == (438, 211, 392, 26)
    assert settings_fullscreen_rect() == (126, 338, 266, 32)
    assert settings_reset_rect() == (126, 383, 266, 32)
    assert settings_back_rect() == (398, 462, 164, 29)
