from pathlib import Path

def test_fullscreen_uses_pygame_window_desktop_api():
    root = Path(__file__).resolve().parents[1]
    main = (root / "main.py").read_text(encoding="utf-8")
    assert "pygame.Window.from_display_module()" in main
    assert "set_fullscreen(desktop=True)" in main
    assert "set_windowed()" in main

def test_fullscreen_desktop_constant_is_not_used():
    root = Path(__file__).resolve().parents[1]
    for path in root.rglob("*.py"):
        if "tests" in path.parts:
            continue
        text = path.read_text(encoding="utf-8")
        assert "pygame.FULLSCREEN_DESKTOP" not in text


def test_fullscreen_is_enabled_by_default_for_new_settings():
    root = Path(__file__).resolve().parents[1]
    save = (root / "game" / "save.py").read_text(encoding="utf-8")
    assert '"fullscreen": True' in save


def test_intro_to_menu_uses_crossfade_transition():
    root = Path(__file__).resolve().parents[1]
    main = (root / "main.py").read_text(encoding="utf-8")
    assert "self._intro_transition_surface = self.screen.copy()" in main
    assert "self._intro_transition_duration = 0.85" in main
    assert "overlay.set_alpha(alpha)" in main
