import math

from game.rendering.rotation_geometry import quantized_facing_flip, quantized_sprite_angle


def test_quantized_sprite_angle_preserves_eight_degree_buckets():
    assert quantized_sprite_angle(0.0) == 0
    assert quantized_sprite_angle(math.radians(8)) == -8
    assert quantized_sprite_angle(math.radians(-8)) == 8
    assert quantized_sprite_angle(math.radians(22)) == -24


def test_quantized_sprite_angle_supports_custom_step():
    assert quantized_sprite_angle(math.radians(13), 5) == -15


def test_quantized_facing_flip_uses_horizontal_direction():
    assert quantized_facing_flip(0.0) is False
    assert quantized_facing_flip(math.pi) is True
    assert quantized_facing_flip(math.pi / 2) is False
