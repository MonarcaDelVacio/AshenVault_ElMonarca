import pygame

from game.rendering.atlas_background import make_background_transparent


def test_make_background_transparent_keys_only_matching_pixels():
    pygame.init()
    surface = pygame.Surface((3, 2), pygame.SRCALPHA)
    surface.fill((184, 184, 184, 255))
    surface.set_at((1, 0), (180, 182, 185, 255))
    surface.set_at((2, 1), (50, 60, 70, 255))

    keyed = make_background_transparent(surface, (184, 184, 184), tolerance=5)

    assert keyed.get_at((0, 0)).a == 0
    assert keyed.get_at((1, 0)).a == 0
    assert keyed.get_at((2, 1)).a == 255


def test_make_background_transparent_does_not_mutate_source():
    pygame.init()
    surface = pygame.Surface((1, 1), pygame.SRCALPHA)
    surface.fill((166, 166, 166, 255))
    keyed = make_background_transparent(surface, (166, 166, 166))
    assert surface.get_at((0, 0)).a == 255
    assert keyed.get_at((0, 0)).a == 0
