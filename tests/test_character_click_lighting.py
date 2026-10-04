from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_clicking_character_card_confirms_selection_immediately():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    handler = source[source.index("def handle_menu_mouse"):source.index("# ---------- teclas configurables ----------")]
    assert 'self.char_id = self.char_ids[n]' in handler
    assert 'self.confirm_character_selection()' in handler
    assert 'self.audio.play("ui", self.t)' in handler


def test_scene_has_ambient_tone_and_dynamic_radial_lights():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'ambient.fill((6, 9, 20, 66))' in source
    assert 'def add_light(target, world_x, world_y, radius, color, strength=1.0):' in source
    assert 'player_light = pygame.Surface((VIEW_W, VIEW_H))' in source
    assert source.index('screen.blit(lights, (0, 0), special_flags=pygame.BLEND_RGB_ADD)') < source.index('screen.blit(player_light, (0, 0), special_flags=pygame.BLEND_RGB_ADD)')
    assert 'pygame.BLEND_RGB_ADD' in source
    assert 'tile_image.fill((224, 228, 238, 255)' in source


def test_dynamic_shadows_are_drawn_after_lighting():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert "def _draw_dynamic_shadows(self, screen, arena, sim, ox, oy):" in source
    assert "self._draw_dynamic_shadows(screen, arena, sim, ox, oy)" in source
    assert source.index("pygame.BLEND_RGB_ADD") < source.index("self._draw_dynamic_shadows(screen, arena, sim, ox, oy)")


def test_dynamic_shadows_cover_interior_pillars_chests_props_and_enemies_but_not_boundary_walls():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    shadow_code = source[source.index("def _draw_dynamic_shadows"):source.index("def draw_world")]
    assert "if tile not in (PILLAR, TORCH_PILLAR)" in shadow_code
    assert "tile in (WALL, PILLAR, TORCH_PILLAR, SECRET)" not in shadow_code
    assert 'sources.extend((light["x"], light["y"], light["radius"], 0.42) for light in decor_lights)' in shadow_code
    assert "getattr(sim, \"chest\", None)" in shadow_code
    assert "getattr(sim, \"props\", [])" in shadow_code
    assert "cast_shadow" in shadow_code


def test_optional_bonfire_sprite_sheet_is_loaded_and_animated():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'bonfire_path = prop_dir / "hoguera.png"' in source
    assert "self.bonfire_frames.append" in source
    assert "int(t * 9.0) % len(self.bonfire_frames)" in source
    assert "assets/props/hoguera.png" in source
