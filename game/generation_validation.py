"""Validación independiente de invariantes de generación procedural."""
from collections import deque

_SPECIAL_NO_ENEMY = {"shop", "treasure", "event", "healing", "secret", "boss"}


def _neighbors(p, w=None, h=None):
    x, y = p
    values = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
    if w is None or h is None:
        return values
    return tuple(q for q in values if 0 <= q[0] < w and 0 <= q[1] < h)


def _walkable_tiles(room):
    grid = room["grid"]
    return {
        (x, y)
        for y, row in enumerate(grid)
        for x, value in enumerate(row)
        if value in (0, 2, 4)
    }


def _door_tiles(room):
    cols, rows = int(room["cols"]), int(room["rows"])
    result = set()
    for x, y in room.get("doors", ()):
        if x in (0, cols - 1):
            result.update(((x, y), (x, y - 1)))
        else:
            result.update(((x, y), (x - 1, y)))
    return result


def _reachable(room, start, blocked=()):
    walkable = _walkable_tiles(room)
    blocked = set(blocked)
    if start not in walkable or start in blocked:
        return set()
    seen = {start}
    q = deque([start])
    while q:
        p = q.popleft()
        for n in _neighbors(p):
            if n in walkable and n not in blocked and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def validate_layout(layout):
    rooms = {tuple(p) for p in layout["rooms"]}
    start = tuple(layout["start"])
    boss = tuple(layout["boss"])
    w, h = int(layout["width"]), int(layout["height"])
    errors = []
    if not (0 <= start[0] < w and 0 <= start[1] < h):
        errors.append("start fuera de límites")
    if not (0 <= boss[0] < w and 0 <= boss[1] < h):
        errors.append("boss fuera de límites")
    if start not in rooms:
        errors.append("start ausente")
    if boss not in rooms:
        errors.append("boss ausente")
    path = [tuple(p) for p in layout["path"]]
    if not path or path[0] != start or path[-1] != boss:
        errors.append("ruta principal no conecta start con boss")
    for a, b in zip(path, path[1:]):
        if abs(a[0] - b[0]) + abs(a[1] - b[1]) != 1:
            errors.append("ruta principal contiene salto no ortogonal")
            break
    if any(p not in rooms for p in path):
        errors.append("ruta principal contiene sala inexistente")
    seen = {start} if start in rooms else set()
    q = deque(seen)
    while q:
        x, y = q.popleft()
        for n in _neighbors((x, y), w, h):
            if n in rooms and n not in seen:
                seen.add(n)
                q.append(n)
    if seen != rooms:
        errors.append("dungeon desconectada")
    if len(rooms) != len(layout["rooms"]):
        errors.append("lista de rooms contiene duplicados")
    return errors


def validate_room(room_data):
    errors = []
    cols = int(room_data["cols"])
    rows = int(room_data["rows"])
    grid = room_data["grid"]
    if len(grid) != rows or any(len(row) != cols for row in grid):
        return ["dimensiones de grid inválidas"]

    doors = [tuple(d) for d in room_data.get("doors", ())]
    valid = {(cols // 2, 0), (cols // 2, rows - 1), (0, rows // 2), (cols - 1, rows // 2)}
    if len(doors) != len(set(doors)):
        errors.append("puertas duplicadas")
    for door in doors:
        if door not in valid:
            errors.append("ancla de puerta inválida")

    perimeter = set()
    for x in range(cols):
        if grid[0][x] in (0, 2, 4):
            perimeter.add((x, 0))
        if grid[rows - 1][x] in (0, 2, 4):
            perimeter.add((x, rows - 1))
    for y in range(rows):
        if grid[y][0] in (0, 2, 4):
            perimeter.add((0, y))
        if grid[y][cols - 1] in (0, 2, 4):
            perimeter.add((cols - 1, y))
    expected = _door_tiles(room_data)
    if perimeter != expected:
        errors.append("aberturas de perímetro no coinciden con las puertas")

    walkable = _walkable_tiles(room_data)
    spawn = tuple(room_data["player_spawn"])
    if spawn not in walkable:
        errors.append("spawn del jugador no está sobre suelo")

    enemy_spawns = [tuple(p) for p in room_data.get("enemy_spawns", ())]
    item_spawns = [tuple(p) for p in room_data.get("item_spawns", ())]
    if len(enemy_spawns) != len(set(enemy_spawns)):
        errors.append("spawns de enemigos duplicados")
    if len(item_spawns) != len(set(item_spawns)):
        errors.append("spawns de objetos duplicados")
    if any(p not in walkable for p in enemy_spawns):
        errors.append("spawn de enemigo fuera del suelo")
    if any(p not in walkable for p in item_spawns):
        errors.append("spawn de objeto fuera del suelo")

    # Cada puerta debe tener una ruta de suelo hasta el spawn del jugador.
    # Esto valida accesibilidad de la sala sin depender de Arena._ensure_door_access().
    for door in doors:
        if door[0] in (0, cols - 1):
            start = (door[0] + (1 if door[0] == 0 else -1), door[1])
        else:
            start = (door[0], door[1] + (1 if door[1] == 0 else -1))
        if spawn not in _reachable(room_data, start):
            errors.append(f"puerta {door} no tiene ruta al spawn")
    
    # Los spawns generados deben quedar separados del punto del jugador.
    # No imponemos distancia entre enemigos: la congestión se resuelve en IA.
    if spawn in set(enemy_spawns) or spawn in set(item_spawns):
        errors.append("spawn del jugador comparte casilla con otro spawn")

    if not room_data.get("floor_surface"):
        errors.append("sala sin floor_surface")
    if not room_data.get("room_type"):
        errors.append("sala sin room_type")
    return errors


def validate_dungeon(dungeon):
    """Audita invariantes de la Dungeon ya construida, incluyendo espaciado."""
    errors = []
    layout_errors = validate_layout(dungeon.layout)
    errors.extend(f"layout: {error}" for error in layout_errors)

    rooms = dungeon.rooms
    start = tuple(dungeon.layout["start"])
    boss = tuple(dungeon.layout["boss"])
    if start not in rooms or boss not in rooms:
        return errors + ["Dungeon sin room de start/boss"]

    if rooms[start].room_type != "start":
        errors.append("la sala inicial no es start")
    if rooms[boss].room_type != "boss":
        errors.append("la sala final no es boss")

    boss_rooms = [r for r in rooms.values() if r.room_type == "boss"]
    if len(boss_rooms) != 6:
        errors.append(f"cantidad de bosses inesperada: {len(boss_rooms)}")

    for rid, room in rooms.items():
        if validate_room(room.data):
            errors.append(f"sala {rid} inválida")
            break

    for rid, room in rooms.items():
        x, y = rid
        if room.room_type not in _SPECIAL_NO_ENEMY and room.room_type != "miniboss":
            continue
        for other in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if other not in rooms or other <= rid:
                continue
            other_type = rooms[other].room_type
            if other_type in _SPECIAL_NO_ENEMY or other_type == "miniboss":
                errors.append(f"salas especiales adyacentes: {rid} y {other}")
    return errors
