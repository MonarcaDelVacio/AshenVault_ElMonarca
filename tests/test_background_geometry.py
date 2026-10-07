import pygame

from game.rendering.background_geometry import trim_edge_background


def _surface(pixels):
    pygame.init()
    h = len(pixels)
    w = len(pixels[0])
    surface = pygame.Surface((w, h), pygame.SRCALPHA)
    for y, row in enumerate(pixels):
        for x, value in enumerate(row):
            surface.set_at((x, y), value)
    return surface


def test_trim_edge_background_removes_only_connected_white_background():
    surface = _surface([
        [(255, 255, 255, 255)] * 5,
        [(255, 255, 255, 255), (20, 30, 40, 255), (255, 255, 255, 255), (255, 255, 255, 255), (255, 255, 255, 255)],
        [(255, 255, 255, 255), (20, 30, 40, 255), (255, 255, 255, 255), (20, 30, 40, 255), (255, 255, 255, 255)],
        [(255, 255, 255, 255, 255), (255, 255, 255, 255), (255, 255, 255, 255), (20, 30, 40, 255), (255, 255, 255, 255)],
        [(255, 255, 255, 255, 255, 255)] * 5,
    ])
    trimmed = trim_edge_background(surface)
    assert trimmed.get_size() == (3, 3)
    assert trimmed.get_at((0, 0)).a == 255
    assert trimmed.get_at((2, 2)).a == 255


def test_trim_edge_background_preserves_internal_white_pixels():
    surface = _surface([
        [(255, 255, 255, 255)] * 5,
        [(255, 255, 255, 255), (30, 40, 50, 255), (30, 40, 50, 255), (30, 40, 50, 255), (255, 255, 255, 255)],
        [(255, 255, 255, 255), (30, 40, 50, 255), (255, 255, 255, 255), (30, 40, 50, 255), (255, 255, 255, 255, 255)],
        [(255, 255, 255, 255, 255), (30, 40, 50, 255), (30, 40, 50, 255), (30, 40, 255, 255), (255, 255, 255, 255)],
        [(255, 255, 255, 255, 255)] * 5,
    ])
    trimmed = trim_edge_background(surface)
    assert trimmed.get_size() == (3, 3)
    assert trimmed.get_at((1, 1)).a == 255
