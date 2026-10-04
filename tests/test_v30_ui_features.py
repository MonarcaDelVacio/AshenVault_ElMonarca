from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RENDER = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
MAIN = (ROOT / "main.py").read_text(encoding="utf-8")
SAVE = (ROOT / "game" / "save.py").read_text(encoding="utf-8")


def test_ability_shield_overlay_is_scaled_to_character_size():
    assert "smoothscale(self.ability_shield_image, (52, 52))" in RENDER


def test_minimap_and_three_slot_weapon_hud_exist():
    assert "def draw_minimap(self, screen, sim, large=False):" in RENDER
    assert "self.draw_minimap(screen, sim, large=False)" in RENDER
    assert "for slot_index in range(3):" in RENDER
    assert "pygame.K_1, pygame.K_2, pygame.K_3" in MAIN


def test_floor_items_and_shop_offers_have_bobbing_animation():
    assert "math.sin(t * 4.5 + offer_index * 1.2) * 3" in RENDER
    assert "math.sin(t * 4.8 + item_index * 0.85) * 3" in RENDER
    assert "offer.name" in RENDER


def test_fullscreen_setting_is_persisted_and_has_window_toggle():
    assert '"fullscreen": False' in SAVE
    assert "def _apply_fullscreen(self, enabled):" in MAIN
    assert "set_fullscreen(desktop=True)" in MAIN
    assert '"Pantalla completa"' in MAIN
