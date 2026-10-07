"""Helpers for removing connected background pixels from sprites."""


def trim_edge_background(image, white_threshold=248):
    """Elimina solo el fondo claro conectado a los bordes del PNG.

    Opera sobre la interfaz mínima de una Surface de pygame, manteniendo la
    operación fuera del Renderer para que pueda probarse de forma aislada.
    """
    image = image.copy().convert_alpha()
    w, h = image.get_size()
    if w <= 0 or h <= 0:
        return image

    seen = set()
    stack = []
    for x in range(w):
        stack.append((x, 0))
        stack.append((x, h - 1))
    for y in range(h):
        stack.append((0, y))
        stack.append((w - 1, y))

    while stack:
        x, y = stack.pop()
        if (x, y) in seen or x < 0 or y < 0 or x >= w or y >= h:
            continue
        seen.add((x, y))
        c = image.get_at((x, y))
        if c.a < 8:
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen:
                    stack.append((nx, ny))
            continue
        if c.r >= white_threshold and c.g >= white_threshold and c.b >= white_threshold:
            image.set_at((x, y), (c.r, c.g, c.b, 0))
            for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if (nx, ny) not in seen:
                    stack.append((nx, ny))

    bbox = image.get_bounding_rect(min_alpha=8)
    return image.subsurface(bbox).copy() if bbox.width and bbox.height else image
