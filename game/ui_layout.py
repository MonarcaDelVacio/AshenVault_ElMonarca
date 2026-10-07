"""Pure logical UI layout helpers.

Coordinates are expressed in the game's fixed 960x540 logical canvas.
No pygame dependency is used here; callers may wrap returned tuples in
pygame.Rect when needed.
"""

VIEW_W, VIEW_H = 960, 540


def menu_rects(state, menu_count):
    if state == "menu":
        return [(VIEW_W // 2 - 92, 220 + n * 57, 184, 42) for n in range(menu_count)]
    if state == "pause":
        return [(VIEW_W // 2 - 105, 190 + n * 62, 210, 52) for n in range(menu_count)]
    return []


def settings_volume_rect(index):
    y = 157 + int(index) * 57
    return (126, y, 266, 45), (244, y + 17, 120, 8)


def settings_sensitivity_rect():
    return (126, 257, 266, 74), (145, 307, 228, 8)


def settings_binding_rect(offset):
    return (438, 153 + int(offset) * 29, 392, 26)


def settings_fullscreen_rect():
    return (126, 338, 266, 32)


def settings_reset_rect():
    return (126, 383, 266, 32)


def settings_back_rect():
    return (VIEW_W // 2 - 82, 462, 164, 29)
