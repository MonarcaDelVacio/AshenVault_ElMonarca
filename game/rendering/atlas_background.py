"""Helpers for removing known flat backgrounds from texture atlases."""


def make_background_transparent(surface, background_rgb, tolerance=4):
    """Copy a surface and key out pixels near a known RGB background."""
    keyed = surface.copy()
    br, bg, bb = background_rgb
    tolerance = max(0, int(tolerance))
    for yy in range(keyed.get_height()):
        for xx in range(keyed.get_width()):
            rr, gg, bl, aa = keyed.get_at((xx, yy))
            if (abs(rr - br) <= tolerance and
                    abs(gg - bg) <= tolerance and
                    abs(bl - bb) <= tolerance):
                keyed.set_at((xx, yy), (rr, gg, bl, 0))
    return keyed
