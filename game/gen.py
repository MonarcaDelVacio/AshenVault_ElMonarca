"""Generación procedural determinista de la cuadrícula de habitaciones y diseños internos."""
import random
from collections import deque

DIRS = ((1,0),(-1,0),(0,1),(0,-1))
ROOM_W, ROOM_H = 29, 21
DOOR_TILES = {(x,0) for x in (ROOM_W//2-1,ROOM_W//2,ROOM_W//2+1)} | {(x,ROOM_H-1) for x in (ROOM_W//2-1,ROOM_W//2,ROOM_W//2+1)} | {(0,y) for y in (ROOM_H//2-1,ROOM_H//2,ROOM_H//2+1)} | {(ROOM_W-1,y) for y in (ROOM_H//2-1,ROOM_H//2,ROOM_H//2+1)}


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
        "ruins": ("suelodeladrillosdepiedra", "sueloderocas", "sueloderocas2", "sueloderocasyfuegoazul"),
        "forest": ("suelodehierbas", "suelodehierbas2", "suelodehierbas3", "suelodehierbaytierra", "suelodehierbaocura", "sueloderocasyhierba", "sueloderocasyhierba2", "sueloderocasypasto", "suelodepasto"),
        "dungeon": ("sueloderocaoscura2", "sueloderocas", "sueloderocas2", "suelodeladrillosdepiedra"),
        "laboratory": ("sueloderocasyfuegoazul", "sueloderocasypasto", "sueloderocasyhierba", "sueloderocasyhierba2"),
        "volcanic": ("suelodelava", "sueloderocaylava", "suelodelavarosa", "tierracalienteazul", "tierracalientegris", "tierracalienterojiza", "tierracalientemorada"),
        "desert": ("arena", "suelodearena", "suelodearena2", "suelodearenadedecierto", "tierracalientemarron", "tierracalienterojiza"),
        "swamp": ("suelodepantano", "suelodehierbaytierra", "sueloderocasyhierba", "sueloderocasypasto", "suelodepasto", "tierracalienteverde", "tierracalientegris"),
        "final": ("sueloderocaoscura2", "sueloderocaylava", "tierracalientemorada", "sueloderocasyfuegoazul", "suelodelavarosa"),
    }
    # El tipo de sala ya no cambia el bioma visual. Todas las habitaciones de
    # una misma dungeon comparten la familia de suelo de su temática.
    options = families.get(biome, ("roca",))
    value = int(seed or 0) * 1664525 + 1013904223 + sum(ord(c) for c in str(room_type)) * 97 + sum(ord(c) for c in str(biome))
    return options[abs(value) % len(options)]


def _generate_decorations(rng, room_type, biome, floor, reserved, seed_value=0):
    """Genera decoración temática con posición física y anclaje de profundidad.

    La decoración no es pintura plana: cada objeto ocupa espacio y se evita en
    spawns, puertas, objetivos centrales y otras decoraciones. Las estatuas son
    piezas especiales y, cuando aparecen, ocupan siempre el centro de la sala.
    """
    floor_set = set(floor)
    # El centro del sprite necesita suelo alrededor, no solo su casilla lógica.
    # Esto evita que rocas/bushes altos atraviesen paredes o esquinas de salas.
    candidates = []
    for p in floor_set:
        if p in reserved or not (3 <= p[0] < ROOM_W-3 and 3 <= p[1] < ROOM_H-3):
            continue
        px, py = p
        footprint = {(x, y) for y in range(py-2, py+3) for x in range(px-2, px+3)}
        if footprint <= floor_set:
            candidates.append(p)
    rng.shuffle(candidates)
    result = []

    # Radio visual conservador en bloques. Se basa en el tamaño máximo con que
    # Renderer dibuja cada familia de decoración, no solo en la casilla central.
    # Así una fuente grande no puede quedar detrás de una hoguera, roca o banco.
    decor_radius_tiles = {
        "fountain_active": 1.75, "fountain_inactive": 1.75, "fountain_small": 1.15,
        "well_empty": 1.75,
        "statue_goddess": 1.75, "statue_archer": 1.75, "statue_assassin": 1.75,
        "statue_knight": 1.75, "statue_mage": 1.75,
        "bench_large": 1.25, "bench_small": 1.05, "barrel_large": 0.95,
        "signpost": 1.05, "table": 1.15, "counter": 1.35,
        "crate_stack": 1.20, "crate_pair": 1.10, "wood_chest_decor": 1.10,
        "rock": 0.95, "bush": 0.95, "biome_red_bush": 1.35,
        "biome_lava_rock": 1.40, "biome_lava_rock_purple": 1.30,
        "biome_shared_rock": 1.40,
    }

    def take(kind, count, min_center=4):
        picked=0
        candidate_radius=decor_radius_tiles.get(kind, 1.0)
        for tx,ty in candidates:
            if picked >= count: break
            if abs(tx-ROOM_W//2)+abs(ty-ROOM_H//2) < min_center: continue
            # Comprobación de distancia real entre huellas, no solo de casillas.
            # El pequeño margen evita que dos PNG anti-aliasados se toquen.
            clear=True
            for existing in result:
                ex,ey=int(existing["x"]),int(existing["y"])
                er=decor_radius_tiles.get(existing["kind"],1.0)
                if ((tx-ex)**2 + (ty-ey)**2) ** 0.5 < candidate_radius + er + 0.25:
                    clear=False
                    break
            if not clear:
                continue
            variant = rng.random() if kind.startswith("biome_") else rng.randrange(6)
            result.append({"kind":kind,"x":tx,"y":ty,"variant":variant})
            picked+=1

    # Salas especiales: la estatua representa un punto de interés, no relleno.
    # Nunca se usan estatuas como decoración aleatoria en combate o jefes.
    if room_type == "secret":
        statue_types=("statue_goddess","statue_assassin","statue_archer","statue_knight","statue_mage")
        statue_kind = statue_types[(int(seed_value or 0)) % len(statue_types)]
        result.append({"kind":statue_kind,"x":ROOM_W//2,"y":ROOM_H//2,"variant":0})
    elif biome == "forest":
        take("bush", rng.randint(3,5), 6)
        take("rock", rng.randint(2,3), 6)
        if rng.random() < 0.65: take("biome_red_bush", 1, 7)
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
            # El bioma volcánico usa exclusivamente sus formaciones de roca
            # específicas; nunca mezcla las rocas genéricas del escenario.
            take("biome_lava_rock", rng.randint(3,5), 6)
            if rng.random() < 0.55:
                take("biome_lava_rock_purple", 1, 8)
        elif biome == "desert":
            take("biome_shared_rock", rng.randint(2,4), 6)
        elif biome == "swamp":
            take("biome_shared_rock", rng.randint(2,4), 6)
            if rng.random() < 0.65: take("biome_red_bush", 1, 7)
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

    # Los accesos activos forman un corredor de 3 bloques de ancho hasta
    # el centro. No basta con que exista una ruta de una sola casilla: el
    # personaje tiene radio físico y necesita margen para atravesar la puerta.
    for side in door_sides:
        if side == "N":
            for y in range(0, cy + 1):
                for x in range(cx - 1, cx + 2):
                    if 0 <= x < ROOM_W: mask.add((x, y))
        elif side == "S":
            for y in range(cy, ROOM_H):
                for x in range(cx - 1, cx + 2):
                    if 0 <= x < ROOM_W: mask.add((x, y))
        elif side == "W":
            for x in range(0, cx + 1):
                for y in range(cy - 1, cy + 2):
                    if 0 <= y < ROOM_H: mask.add((x, y))
        elif side == "E":
            for x in range(cx, ROOM_W):
                for y in range(cy - 1, cy + 2):
                    if 0 <= y < ROOM_H: mask.add((x, y))

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

    # Las salas tienen dimensiones impares; una abertura de 3 bloques permite
    # que la puerta quede geométricamente centrada sin desplazar el eje de la sala.
    cx,cy=ROOM_W//2,ROOM_H//2
    all_doors={"N":(cx,0),"S":(cx,ROOM_H-1),"W":(0,cy),"E":(ROOM_W-1,cy)}
    doors=[all_doors[k] for k in ("N","S","W","E") if k in active]
    for x,y in doors:
        if x==0:
            opening=tuple((x,yy) for yy in (y-1,y,y+1))
            inward=(1,y)
        elif x==ROOM_W-1:
            opening=tuple((x,yy) for yy in (y-1,y,y+1))
            inward=(ROOM_W-2,y)
        elif y==0:
            opening=tuple((xx,y) for xx in (x-1,x,x+1))
            inward=(x,1)
        else:
            opening=tuple((xx,y) for xx in (x-1,x,x+1))
            inward=(x,ROOM_H-2)
        for ox,oy in opening:
            if 0<=ox<ROOM_W and 0<=oy<ROOM_H: g[oy][ox]=0
        ix,iy=inward; g[iy][ix]=0

    # El perímetro nunca puede quedar abierto por más de los dos bloques de
    # una puerta. Los corredores de acceso se tallan hacia dentro, no sobre el
    # borde exterior de la sala.
    active_openings=set()
    for x,y in doors:
        if x in (0,ROOM_W-1):
            active_openings.update((x,yy) for yy in (y-1,y,y+1))
        else:
            active_openings.update((xx,y) for xx in (x-1,x,x+1))
    for bx in range(ROOM_W):
        for by in (0,ROOM_H-1):
            if (bx,by) not in active_openings:
                g[by][bx]=1
    for by in range(ROOM_H):
        for bx in (0,ROOM_W-1):
            if (bx,by) not in active_openings:
                g[by][bx]=1

    cx,cy=ROOM_W//2,ROOM_H//2
    door_tiles=set(doors)
    for x,y in doors:
        if x in (0,ROOM_W-1):
            door_tiles.update((x,yy) for yy in (y-1,y+1))
        else:
            door_tiles.update((xx,y) for xx in (x-1,x+1))
    reserved={(x,y) for y in range(cy-2,cy+3) for x in range(cx-2,cx+3)}
    reserved.update(door_tiles)
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
    decoration_reserved=set(reserved) | set(door_tiles) | {(cx,cy)} | set(spawns[:10]) | set(items[:8])
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
