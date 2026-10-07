from game.rendering.animation_geometry import animation_frame_index


def test_animation_frame_index_clamps_non_looping_animation():
    assert animation_frame_index(-1, 4, 1.0) == 0
    assert animation_frame_index(0.24, 4, 1.0) == 0
    assert animation_frame_index(0.26, 4, 1.0) == 1
    assert animation_frame_index(2.0, 4, 1.0) == 3


def test_animation_frame_index_wraps_looping_animation():
    assert animation_frame_index(1.0, 4, 1.0, loop=True) == 0
    assert animation_frame_index(1.26, 4, 1.0, loop=True) == 1


def test_animation_frame_index_handles_empty_and_invalid_duration():
    assert animation_frame_index(0.5, 0, 1.0) == 0
    assert animation_frame_index(0.5, 2, 0, loop=True) == 0
