from game.rendering.atlas_geometry import alpha_runs


def test_alpha_runs_returns_inclusive_ranges():
    assert alpha_runs([False, True, True, False, True]) == [(1, 2), (4, 4)]


def test_alpha_runs_handles_empty_and_all_transparent():
    assert alpha_runs([]) == []
    assert alpha_runs([False, False]) == []


def test_alpha_runs_handles_all_opaque():
    assert alpha_runs([True, True, True]) == [(0, 2)]
