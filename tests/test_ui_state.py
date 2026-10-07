"""Regression tests for the pure application UI-state definitions."""

from game.ui_state import (
    HUB_ITEMS,
    INTRO, MENU, PLAY, PAUSE, MAP, DEAD, VICTORY, SCORE, SETTINGS, CHAR_SELECT, HUB, STATUE,
    MENU_ITEMS, PAUSE_ITEMS, SETTINGS_ITEMS, SETTING_KEYS,
)


def test_ui_state_identifiers_are_unique():
    states = [INTRO, MENU, PLAY, PAUSE, MAP, DEAD, VICTORY, SCORE, SETTINGS, CHAR_SELECT, HUB, STATUE]
    assert len(states) == len(set(states))


def test_settings_actions_have_stable_key_mapping():
    assert SETTING_KEYS["Mover arriba"] == "up"
    assert SETTING_KEYS["Mover derecha"] == "right"
    assert SETTING_KEYS["Habilidad"] == "ability"
    assert SETTING_KEYS["Minimapa"] == "map"
    assert "Pantalla completa" in SETTINGS_ITEMS


def test_core_menu_contract_is_preserved():
    assert MENU_ITEMS == ["Jugar", "Configuracion", "Salir"]
    assert PAUSE_ITEMS[0] == "Continuar"
    assert "Reiniciar run" in PAUSE_ITEMS
    assert HUB_ITEMS[-1] == "Volver al menu"
