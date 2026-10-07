from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_lower_wall_is_only_one_tile_high_and_other_wall_pieces_are_tall():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'target_size = (TILE, TILE) if piece_key == "paredinferior" else (TILE, TILE * 2)' in source


def test_indestructible_interior_pillars_use_column_sprite_and_depth_overlay():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert '("column_image", "columna.png", (TILE, TILE * 2))' in source
    assert "if tile in (PILLAR, TORCH_PILLAR):" in source
    assert "pillar_image = self.torch_column_image if tile == TORCH_PILLAR else self.column_image" in source
    assert "self._draw_architecture_foreground(screen, arena, sim, decor_lights, ox, oy)" in source
    assert "if player_y < base_y:" in source


def test_torch_columns_replace_decorative_lanterns_and_are_depth_sorted():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert '("torch_column_image", "columnaconantorcha.png", (TILE, TILE * 2))' in source
    assert 'if tile == TORCH_PILLAR:' in source
    assert '"kind": "torch_column"' in source
    assert "pillar_image.get_rect" in source


def test_generated_interior_obstacles_are_pillars_not_boundary_walls():
    import sys
    sys.path.insert(0, str(ROOT))
    from game.gen import generate_room

    for seed in range(20):
        grid = generate_room(seed)["grid"]
        # The room perimeter remains WALL (1), except for open doors (0).
        for x in range(len(grid[0])):
            assert grid[0][x] in (0, 1)
            assert grid[-1][x] in (0, 1)
        for y in range(len(grid)):
            assert grid[y][0] in (0, 1)
            assert grid[y][-1] in (0, 1)
        # Any solid tile away from the perimeter must be a PILLAR (2), not WALL.
        for y in range(1, len(grid) - 1):
            for x in range(1, len(grid[y]) - 1):
                assert grid[y][x] != 1


def test_architecture_sprites_load_from_walls_folder_and_align_collision_at_bottom():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'candidates = (wall_dir / filename, self.asset_root / "props" / filename)' in source
    # Tall artwork is bottom-aligned to its logical solid tile in both passes.
    assert source.count('dest = (tx * TILE, (ty + 1) * TILE - piece.get_height())') == 1
    assert 'dest_y = (ty + 1) * TILE - piece.get_height()' in source
    # The lower wall stays a single tile high; other wall pieces remain two tiles high.
    assert 'target_size = (TILE, TILE) if piece_key == "paredinferior" else (TILE, TILE * 2)' in source


def test_torch_pillars_are_solid_tiles_and_generated_pillars_are_structured():
    import sys
    sys.path.insert(0, str(ROOT))
    from game.gen import generate_room
    from game.world import Arena, PILLAR, TORCH_PILLAR

    data = generate_room(22, "combat")
    grid = data["grid"]
    pillars = {(x, y) for y, row in enumerate(grid) for x, tile in enumerate(row)
               if tile in (PILLAR, TORCH_PILLAR)}
    assert pillars == {(5, 4), (12, 4), (19, 4), (5, 12), (12, 12), (19, 12)}
    assert all(grid[y][x] == TORCH_PILLAR for x, y in ((5, 4), (12, 4), (19, 4)))
    arena = Arena(data)
    assert arena.solid_tile(5, 4)
    assert arena.solid_tile(12, 4)


def test_special_rooms_use_four_symmetric_support_pillars():
    import sys
    sys.path.insert(0, str(ROOT))
    from game.gen import generate_room
    from game.world import PILLAR, TORCH_PILLAR

    grid = generate_room(23, "treasure")["grid"]
    pillars = {(x, y) for y, row in enumerate(grid) for x, tile in enumerate(row)
               if tile in (PILLAR, TORCH_PILLAR)}
    assert pillars == {(6, 5), (18, 5), (6, 11), (18, 11)}

def test_atlas_wall_models_use_exact_grid_footprints_and_alpha_bounds():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'bbox = image.get_bounding_rect(min_alpha=8)' in source
    assert 'piece = fit_wall_exact(image, TILE, TILE * 2)' in source
    assert 'piece = fit_wall_exact(image, TILE, TILE)' in source
    assert 'piece = fit_wall_exact(image, TILE * 2, TILE * 2)' in source
    assert 'step = max(1, int(round(max(piece.get_width(), piece.get_height()) * 0.72)))' not in source
    assert 'for item in group:\n                draw_horizontal_cell(item, wall_models.get("front"))' in source
    assert 'for item in group:\n                draw_vertical_cell(item, image)' in source
