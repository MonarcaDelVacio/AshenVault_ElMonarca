from game.rendering.atlas_geometry import alpha_runs, split_grid_frames


def test_alpha_runs_returns_inclusive_ranges():
    assert alpha_runs([False, True, True, False, True]) == [(1, 2), (4, 4)]


def test_alpha_runs_handles_empty_and_all_transparent():
    assert alpha_runs([]) == []
    assert alpha_runs([False, False]) == []


def test_alpha_runs_handles_all_opaque():
    assert alpha_runs([True, True, True]) == [(0, 2)]


class _FakeRect:
    def __init__(self, width, height):
        self.width = width
        self.height = height


class _FakeCell:
    def __init__(self, bbox):
        self.bbox = bbox

    def copy(self):
        return self

    def get_bounding_rect(self, min_alpha=8):
        return self.bbox

    def subsurface(self, rect):
        return self


class _FakeSurface:
    def __init__(self, width, height, boxes):
        self.width = width
        self.height = height
        self.boxes = boxes

    def get_width(self):
        return self.width

    def get_height(self):
        return self.height

    def subsurface(self, rect):
        x, y, width, height = rect
        col = x // 10
        row = y // 10
        return _FakeCell(self.boxes[row][col])


def test_split_grid_frames_preserves_row_major_order_and_source_rects():
    boxes = [
        [_FakeRect(4, 5), _FakeRect(0, 0)],
        [_FakeRect(3, 2), _FakeRect(6, 1)],
    ]
    surface = _FakeSurface(20, 20, boxes)

    frames = split_grid_frames(surface, 2, 2)

    assert [item[0] for item in frames] == [0, 2, 3]
    assert [item[1] for item in frames] == [
        (0, 0, 10, 10),
        (0, 10, 10, 10),
        (10, 10, 10, 10),
    ]


def test_split_grid_frames_rejects_invalid_dimensions():
    surface = _FakeSurface(21, 20, [[_FakeRect(1, 1)]])
    assert split_grid_frames(surface, 2, 2) == []
    assert split_grid_frames(surface, 0, 2) == []
