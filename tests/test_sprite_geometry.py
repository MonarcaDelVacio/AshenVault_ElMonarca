from game.rendering.sprite_geometry import fit_dimensions


def test_fit_dimensions_preserves_aspect_ratio():
    assert fit_dimensions(200, 100, 50) == (50, 25)


def test_fit_dimensions_does_not_upscale():
    assert fit_dimensions(20, 10, 50) == (20, 10)


def test_fit_dimensions_handles_zero_or_negative_inputs():
    assert fit_dimensions(0, 100, 50) == (1, 50)
    assert fit_dimensions(100, 0, 50) == (50, 1)
    assert fit_dimensions(-10, -20, 50) == (25, 50)
