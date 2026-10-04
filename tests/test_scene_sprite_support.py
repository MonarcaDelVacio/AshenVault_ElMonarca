from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_main_menu_routes_play_through_character_select_and_hides_character_option():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'MENU_ITEMS = ["Jugar", "Mejoras", "Configuracion", "Salir"]' in source
    assert 'self.back_state = "start_run"' in source
    assert "self.confirm_character_selection()" in source
    assert 'if self.back_state == "start_run":' in source


def test_floor_sprite_loader_supports_all_eleven_tiles_and_tile_sizing():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'self.asset_root / "floors"' in source
    assert 'range(1, 12)' in source
    assert 'f"suelo{number}.png"' in source
    assert 'pygame.transform.scale(image, (TILE, TILE))' in source


def test_wall_sprite_loader_uses_both_supplied_wall_pngs():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'wall_dir / "wall2.png"' in source
    assert 'wall_dir / "cobbles2.png"' in source
    assert "self.wall_top_images" in source
    assert "self.wall_fill_images" in source


def test_readme_documents_manual_scene_asset_locations():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/floors/" in readme
    assert "assets/walls/" in readme
    assert "suelo11.png" in readme


def test_individual_wall_segments_and_corners_are_loaded_from_assets_walls():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    for filename in (
        "paredinferior.png", "paredsuperior.png",
        "paredlateralizquierda.png", "paredlateralderecha.png",
        "esquinainferiorderecha.png", "esquinainferiorizquierda.png",
        "esquinasuperiorderecha.png", "esquinasuperiorizquierda.png",
    ):
        assert filename in source
    assert "self._wall_piece_key(arena, tx, ty)" in source
    assert "self.wall_piece_images.get(piece_key)" in source


def test_column_sprites_replace_pillars_and_decorative_lanterns():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert '"columna.png"' in source
    assert '"columnaconantorcha.png"' in source
    assert 'tile == TORCH_PILLAR' in source
    assert '"kind": "torch_column"' in source
    assert 'bonfire_positions(arena)' in source
    assert "self.torch_column_image" in source


def test_wall_and_column_sprites_use_two_tile_height_with_one_tile_footprint():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert "pygame.transform.smoothscale(image, (TILE, TILE * 2))" in source
    assert '("column_image", "columna.png", (TILE, TILE * 2))' in source
    assert '("torch_column_image", "columnaconantorcha.png", (TILE, TILE * 2))' in source
    assert "Dibuja las paredes altas en una segunda pasada" in source
    assert 'candidates = (wall_dir / filename, self.asset_root / "props" / filename)' in source
    assert 'dest = (tx * TILE, (ty + 1) * TILE - piece.get_height())' in source
    assert 'piece_key in ("paredsuperior", "esquinasuperiorizquierda", "esquinasuperiorderecha")' not in source
