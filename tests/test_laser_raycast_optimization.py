from game.systems.combat import _ray_circle_hit_distance


def test_ray_circle_hit_distance_returns_first_intersection():
    # Ray starts at the origin and points along +X. A radius-5 target centered
    # at x=20 is first touched at x=15.
    assert _ray_circle_hit_distance(0.0, 0.0, 1.0, 0.0, 20.0, 0.0, 5.0) == 15.0


def test_ray_circle_hit_distance_rejects_targets_behind_or_outside():
    assert _ray_circle_hit_distance(0.0, 0.0, 1.0, 0.0, -20.0, 0.0, 5.0) is None
    assert _ray_circle_hit_distance(0.0, 0.0, 1.0, 0.0, 20.0, 6.0, 5.0) is None


def test_ray_circle_hit_distance_handles_tangent():
    assert _ray_circle_hit_distance(0.0, 0.0, 1.0, 0.0, 20.0, 5.0, 5.0) == 20.0
