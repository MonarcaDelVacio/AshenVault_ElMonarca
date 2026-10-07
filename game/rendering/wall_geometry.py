"""Pure wall-piece classification used by the world renderer."""


def wall_piece_key(arena, tx, ty, floor_value):
    """Identify outer wall edges/corners from neighboring floor cells."""
    def is_floor(x, y):
        return 0 <= x < arena.cols and 0 <= y < arena.rows and arena.grid[y][x] == floor_value

    north, east = is_floor(tx, ty - 1), is_floor(tx + 1, ty)
    south, west = is_floor(tx, ty + 1), is_floor(tx - 1, ty)
    nw, ne = is_floor(tx - 1, ty - 1), is_floor(tx + 1, ty - 1)
    sw, se = is_floor(tx - 1, ty + 1), is_floor(tx + 1, ty + 1)

    if not (north or east or south or west):
        if se:
            return "esquinasuperiorizquierda"
        if sw:
            return "esquinasuperiorderecha"
        if ne:
            return "esquinainferiorizquierda"
        if nw:
            return "esquinainferiorderecha"
    if south:
        return "paredsuperior"
    if north:
        return "paredinferior"
    if east:
        return "paredlateralizquierda"
    if west:
        return "paredlateralderecha"
    return None
