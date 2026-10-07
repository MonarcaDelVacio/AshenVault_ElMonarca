from types import SimpleNamespace

from game.rendering.wall_geometry import wall_piece_key


def arena(rows):
    return SimpleNamespace(grid=rows, rows=len(rows), cols=len(rows[0]))


def test_wall_piece_key_classifies_outer_edges():
    a = arena([[1, 1, 1], [1, 0, 1], [1, 1, 1]])
    assert wall_piece_key(a, 1, 0, 0) == "paredsuperior"
    assert wall_piece_key(a, 0, 1, 0) == "paredlateralizquierda"
    assert wall_piece_key(a, 2, 1, 0) == "paredlateralderecha"
    assert wall_piece_key(a, 1, 2, 0) == "paredinferior"


def test_wall_piece_key_classifies_diagonal_corners():
    a = arena([[1, 1], [1, 0]])
    assert wall_piece_key(a, 0, 0, 0) == "esquinasuperiorizquierda"


def test_wall_piece_key_returns_none_for_unconnected_wall():
    a = arena([[1, 1], [1, 1]])
    assert wall_piece_key(a, 0, 0, 0) is None
