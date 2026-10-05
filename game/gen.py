"""Generación procedural determinista de la cuadrícula de habitaciones y diseños internos."""
import random
from collections import deque

DIRS = ((1,0),(-1,0),(0,1),(0,-1))
ROOM_W, ROOM_H = 29, 21
DOOR_TILES = {(ROOM_W//2,0),(ROOM_W//2,ROOM_H-1),(0,ROOM_H//2),(ROOM_W-1,ROOM_H//2)}


def _neighbors(p, w, h):
    x,y=p
    for dx,dy in DIRS:
        q=(x+dx,y+dy)
        if 0<=q[0]<w and 0<=q[1]<h:
            yield q


def _auto_path(rng, w=7, h=7):
    """Self-avoiding monotone path: guaranteed from (0,0) to (w-1,h-1)."""
    x=y=0; path=[(0,0)]; seen={(0,0)}
    while (x,y)!=(w-1,h-1):
        opts=[]
        if x<w-1: opts.append((x+1,y))
        if y<h-1: opts.append((x,y+1))
        # Avoid making the remainder impossible by always retaining monotone progress.
        rng.shuffle(opts)
        x,y=opts[0]; path.append((x,y)); seen.add((x,y))
    return path


def generate_layout(seed=None, w=9, h=9, branch_chance=.34):
    rng=random.Random(seed)
    path=_auto_path(rng,w,h)
    rooms=set(path)
    candidates=[]
    boss=(w-1,h-1)
    for p in path[:-1]:
        for q in _neighbors(p,w,h):
            if q not in rooms and q != boss and not (q in list(_neighbors(boss,w,h))): candidates.append(q)
    rng.shuffle(candidates)
    for q in candidates:
        if rng.random()>branch_chance: continue
        # attach only to an existing room, never to the boss tile.
        if any(n in rooms for n in _neighbors(q,w,h)):
            rooms.add(q)
    # A few branches can extend one extra step, but never from boss.
    frontier=list(rooms-{(w-1,h-1)}); rng.shuffle(frontier)
    for p in frontier[:max(0,len(frontier)//3)]:
        if rng.random()<.22:
            opts=[q for q in _neighbors(p,w,h) if q not in rooms and q!=(w-1,h-1) and q not in _neighbors((w-1,h-1),w,h)]
            if opts: rooms.add(rng.choice(opts))
    start=(0,0); boss=(w-1,h-1)
    assert start in rooms and boss in rooms
    # connectivity invariant
    seen={start}; q=deque([start])
    while q:
        p=q.popleft()
        for n in _neighbors(p,w,h):
            if n in rooms and n not in seen: seen.add(n); q.append(n)
    if seen != rooms: raise AssertionError("generated dungeon disconnected")
    return {"width":w,"height":h,"rooms":sorted(rooms),"path":path,"start":start,"boss":boss}


def _flood(grid, start):
    h=len(grid); w=len(grid[0]); seen={start}; q=deque([start])
    while q:
        x,y=q.popleft()
        for dx,dy in DIRS:
            nx,ny=x+dx,y+dy
            if 0<=nx<w and 0<=ny<h and grid[ny][nx]==0 and (nx,ny) not in seen:
                seen.add((nx,ny)); q.append((nx,ny))
    return seen




def _choose_floor_surface(seed, room_type, biome):
    """Elige una única superficie para toda la sala. Nunca mezcla texturas nuevas."""
    families = {
        "ruins": ("ladrillosdepiedra", "roca"),
        "forest": ("hierba", "madera", "roca"),
        "dungeon": ("roca", "rocanegra", "ladrillosdepiedra"),
        "laboratory": ("ladrillos", "roca"),
        "volcanic": ("rocanegra", "roca"),
        "final": ("rocanegra", "ladrillosdepiedra"),
    }
    special = {
        "shop": ("madera", "ladrillos"),
        "treasure": ("ladrillosdepiedra", "ladrillos"),
        "healing": ("hierba", "roca"),
        "event": ("arena", "hierba"),
        "secret": ("roca", "rocanegra"),
        "challenge": ("roca", "ladrillosdepiedra"),
        "boss": ("rocanegra", "roca"),
    }
    options = special.get(room_type) or families.get(biome, ("roca",))
    value = int(seed or 0) * 1664525 + 1013904223 + sum(ord(c) for c in str(room_type)) * 97 + sum(ord(c) for c in str(biome))
    return options[abs(value) % len(options)]


def _generate_decorations(rng, room_type, biome, floor, reserved, seed_value=0):
    """Genera decoración temática con posición física y anclaje de profundidad.

    La decoración no es pintura plana: cada objeto ocupa espacio y se evita en
    spawns, puertas, objetivos centrales y otras decoraciones. Las estatuas son
    piezas especiales y, cuando aparecen, ocupan siempre el centro de la sala.
    """
    floor_set = set(floor)
    candidates = [p for p in floor_set if p not in reserved and 2 <= p[0] < ROOM_W-2 and 2 <= p[1] < ROOM_H-2]
    rng.shuffle(candidates)
    result = []

    def take(kind, count, min_center=4):
        used={(int(d["x"]),int(d["y"])) for d in result}
        picked=0
        for tx,ty in candidates:
            if picked >= count: break
            if (tx,ty) in used: continue
            if abs(tx-ROOM_W//2)+abs(ty-ROOM_H//2) < min_center: continue
            if any(abs(tx-x)<=1 and abs(ty-y)<=1 for x,y in used): continue
            result.append({"kind":kind,"x":tx,"y":ty,"variant":rng.randrange(6)})
            used.add((tx,ty)); picked+=1

    # Salas especiales: la estatua representa un punto de interés, no relleno.
    # Nunca se usan estatuas como decoración aleatoria en combate o jefes.
    if room_type == "secret":
        statue_types=("statue_goddess","statue_assassin","statue_archer","statue_knight","statue_mage")
        statue_kind = statue_types[(int(seed_value or 0)) % len(statue_types)]
        result.append({"kind":statue_kind,"x":ROOM_W//2,"y":ROOM_H//2,"variant":0})
    elif biome == "forest":
        take("bush", rng.randint(3,5), 6)
        take("rock", rng.randint(2,3), 6)
    elif room_type == "shop":
        take("bench_small", 2, 5)
        take("barrel_large", 1, 6)
        take("signpost", 1, 6)
        take("table", 1, 6)
    elif room_type == "healing":
        result.append({"kind":"fountain_active","x":ROOM_W//2,"y":ROOM_H//2,"variant":0})
        take("bush", 2, 7) if biome == "forest" else take("rock", 2, 7)
    elif room_type == "event":
        result.append({"kind":"well_empty","x":ROOM_W//2,"y":ROOM_H//2,"variant":0})
        take("signpost", 1, 7)
        take("rock", 2, 6)
    elif room_type == "treasure":
        # El cofre ocupa el centro; no se coloca una estatua aquí.
        take("bench_small", 1, 7)
        take("rock", 2, 7)
    else:
        if biome in ("ruins", "dungeon"):
            take("rock", rng.randint(2,4), 6)
            if room_type in ("combat","elite") and rng.random()<0.35:
                take("bench_small", 1, 7)
        elif biome == "laboratory":
            take("rock", rng.randint(1,2), 6)
            if rng.random()<0.20: take("signpost", 1, 8)
        elif biome == "volcanic":
            take("rock", rng.randint(3,5), 6)
        elif biome == "final":
            take("rock", rng.randint(2,4), 6)
    return result



def _shape_floor_mask(rng, room_type, door_sides):
    """Genera siluetas de sala variadas manteniendo todos los accesos conectados."""
    # Las salas normales conservan el rectángulo clásico con pequeñas variaciones.
    # Las formas más pronunciadas siguen dejando libres los cuatro puntos de puerta.
    choices = ["rectangle", "octagon", "chamfer", "cross", "diamond"]
    if room_type == "boss":
        choices = ["rectangle", "octagon"]
    elif room_type == "miniboss":
        choices = ["rectangle", "octagon", "chamfer"]
    shape = rng.choice(choices)

    cx, cy = ROOM_W // 2, ROOM_H // 2
    mask = set()

    for y in range(1, ROOM_H - 1):
        for x in range(1, ROOM_W - 1):
            dx, dy = abs(x - cx), abs(y - cy)
            inside = False
            if shape == "rectangle":
                inside = True
            elif shape == "octagon":
                inside = dx <= cx - 1 and dy <= cy - 1 and (dx + dy) <= max(cx, cy) + 1
            elif shape == "chamfer":
                inside = dx <= cx - 1 and dy <= cy - 1 and not (dx + dy >= max(cx, cy) + 2)
            elif shape == "cross":
                inside = (abs(x - cx) <= 4) or (abs(y - cy) <= 3)
            elif shape == "diamond":
                inside = (dx / max(1, cx - 1) + dy / max(1, cy - 1)) <= 1.0
            if inside:
                mask.add((x, y))

    # Los accesos activos siempre forman un pequeño pasillo recto hacia la sala.
    # Esto permite usar cualquier silueta sin romper la conectividad del dungeon.
    for side in door_sides:
        if side == "N":
            for y in range(0, cy + 1):
                mask.add((cx, y))
        elif side == "S":
            for y in range(cy, ROOM_H):
                mask.add((cx, y))
        elif side == "W":
            for x in range(0, cx + 1):
                mask.add((x, cy))
        elif side == "E":
            for x in range(cx, ROOM_W):
                mask.add((x, cy))

    # La zona central siempre existe para que spawn, enemigos y objetivos tengan
    # un área continua aun en las formas más estrechas.
    for y in range(cy - 2, cy + 3):
        for x in range(cx - 3, cx + 4):
            if 0 <= x < ROOM_W and 0 <= y < ROOM_H:
                mask.add((x, y))
    return shape, mask

def generate_room(seed=None, room_type="combat", biome="ruins", door_sides=None):
    rng=random.Random(seed)
    active=set(door_sides) if door_sides is not None else set(("N","S","W","E"))
    shape_name, floor_mask = _shape_floor_mask(rng, room_type, active)
    g=[[0 if (x,y) in floor_mask else 1 for x in range(ROOM_W)] for y in range(ROOM_H)]

    all_doors={"N":(ROOM_W//2,0),"S":(ROOM_W//2,ROOM_H-1),"W":(0,ROOM_H//2),"E":(ROOM_W-1,ROOM_H//2)}
    doors=[all_doors[k] for k in ("N","S","W","E") if k in active]
    for x,y in doors:
        g[y][x]=0
        if x==0:g[y][1]=0
        elif x==ROOM_W-1:g[y][ROOM_W-2]=0
        elif y==0:g[1][x]=0
        else:g[ROOM_H-2][x]=0
    cx,cy=ROOM_W//2,ROOM_H//2
    reserved={(x,y) for y in range(cy-2,cy+3) for x in range(cx-2,cx+3)}
    reserved.update(doors)
    # Zona de seguridad de puertas: ningún obstáculo indestructible puede aparecer a menos de 2 bloques de una entrada.
    door_safe = set()
    for dx, dy in doors:
        for ty in range(max(0, dy-2), min(ROOM_H, dy+3)):
            for tx in range(max(0, dx-2), min(ROOM_W, dx+3)):
                if abs(tx-dx) + abs(ty-dy) <= 2:
                    door_safe.add((tx, ty))
    reserved.update(door_safe)
    reserved.update({(x,y) for x,y in [(ROOM_W//2,1),(ROOM_W//2,ROOM_H-2),(1,ROOM_H//2),(ROOM_W-2,ROOM_H//2)]})
    # Los pilares son soportes del techo, no obstáculos aleatorios. Se colocan
    # en patrones arquitectónicos simétricos y con una huella de una sola casilla.
    # Las salas de combate usan una retícula de seis soportes; las salas especiales
    # conservan cuatro soportes laterales para dejar espacio al objetivo central.
    if room_type in ("combat", "elite", "challenge", "miniboss", "boss"):
        pillar_positions = [
            (cx-8, cy-5), (cx, cy-5), (cx+8, cy-5),
            (cx-8, cy+5), (cx, cy+5), (cx+8, cy+5)
        ]
    else:
        pillar_positions = [(cx-7, cy-5), (cx+7, cy-5), (cx-7, cy+5), (cx+7, cy+5)]

    # Una fila completa de antorchas alterna entre la fila superior e inferior
    # según la semilla de la sala; así se ve planificado, pero no idéntico en todas.
    torch_row = cy-5 if (seed or 0) % 2 == 0 else cy+5
    for x, y in pillar_positions:
        # Un pilar solo puede ocupar una casilla que ya pertenece al suelo de
        # la silueta generada. Esto evita que sobresalga de paredes en salas
        # octogonales, diagonales o con chaflán.
        if (x, y) in reserved or (x, y) not in floor_mask:
            continue
        g[y][x] = 4 if y == torch_row and room_type in ("combat", "elite", "challenge", "miniboss", "boss") else 2

    # En salas especiales, dos soportes opuestos llevan antorchas.
    if room_type not in ("combat", "elite", "challenge", "miniboss", "boss"):
        torch_positions = {(cx-7, cy-5), (cx+7, cy+5)} if (seed or 0) % 2 == 0 else {(cx+7, cy-5), (cx-7, cy+5)}
        for x, y in torch_positions:
            if g[y][x] == 2:
                g[y][x] = 4
    floor=list(_flood(g,(cx,cy)))
    if len(floor) != sum(row.count(0) for row in g):
        # Respaldo conservador: conserva cuatro soportes simétricos si un patrón
        # llegara a desconectar una sala, en lugar de borrar todos los pilares.
        for y in range(1, ROOM_H - 1):
            for x in range(1, ROOM_W - 1):
                if g[y][x] in (2, 4):
                    g[y][x] = 0
        fallback = [(6, 5), (18, 5), (6, 11), (18, 11)]
        for x, y in fallback:
            g[y][x] = 4 if (x, y) in ((6, 5), (18, 11)) else 2
        floor=list(_flood(g,(cx,cy)))
    # Las paredes secretas destructibles se retiraron: el loot de salas proviene
    # de cajas, cofres y recompensas de combate, no de paredes adicionales.
    secrets=[]
    floor=list(_flood(g,(cx,cy)))
    if len(floor) != sum(row.count(0) for row in g):
        # Revalidar manteniendo los secretos intactos.
        for y in range(1,ROOM_H-1):
            for x in range(1,ROOM_W-1):
                if (x,y) not in reserved and (x,y) not in secrets:g[y][x]=0
        floor=list(_flood(g,(cx,cy)))
    spawns=[p for p in floor if 2<p[0]<ROOM_W-3 and 2<p[1]<ROOM_H-3 and abs(p[0]-cx)+abs(p[1]-cy)>5]
    rng.shuffle(spawns)
    items=[p for p in floor if abs(p[0]-cx)+abs(p[1]-cy)>3]
    rng.shuffle(items)
    decoration_reserved=set(reserved) | set(doors) | {(cx,cy)} | set(spawns[:10]) | set(items[:8])
    floor_surface=_choose_floor_surface(seed, room_type, biome)
    decorations=_generate_decorations(rng, room_type, biome, floor, decoration_reserved, seed)
    # Los puntos de interés centrales son físicos; nunca hacemos aparecer al
    # jugador dentro de una fuente, pozo o estatua.
    player_spawn=(cx,cy)
    floor_set=set(floor)
    if room_type in ("healing","event","secret"):
        for candidate in ((cx,cy+3),(cx,cy-3),(cx+3,cy),(cx-3,cy)):
            if candidate in floor_set and candidate not in decoration_reserved:
                player_spawn=candidate
                break
    return {"cols":ROOM_W,"rows":ROOM_H,"grid":g,"doors":doors,"player_spawn":player_spawn,"enemy_spawns":spawns[:10],"item_spawns":items[:8],"room_type":room_type,"biome":biome,"floor_surface":floor_surface,"secrets":secrets,"decorations":decorations,"shape":shape_name}


def validate_layout(layout):
    rooms=set(map(tuple,layout["rooms"])); start=tuple(layout["start"]); boss=tuple(layout["boss"])
    q=deque([start]); seen={start}
    while q:
        p=q.popleft()
        for n in _neighbors(p,layout["width"],layout["height"]):
            if n in rooms and n not in seen: seen.add(n); q.append(n)
    return boss in seen and seen==rooms and all(tuple(p) in rooms for p in layout["path"])
