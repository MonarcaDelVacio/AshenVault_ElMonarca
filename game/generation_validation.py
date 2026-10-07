"""Validación independiente de invariantes de generación procedural."""
from collections import deque

def validate_layout(layout):
    rooms={tuple(p) for p in layout["rooms"]}; start=tuple(layout["start"]); boss=tuple(layout["boss"])
    w,h=int(layout["width"]),int(layout["height"]); errors=[]
    if not (0<=start[0]<w and 0<=start[1]<h): errors.append("start fuera de límites")
    if not (0<=boss[0]<w and 0<=boss[1]<h): errors.append("boss fuera de límites")
    if start not in rooms: errors.append("start ausente")
    if boss not in rooms: errors.append("boss ausente")
    path=[tuple(p) for p in layout["path"]]
    if not path or path[0]!=start or path[-1]!=boss: errors.append("ruta principal no conecta start con boss")
    for a,b in zip(path,path[1:]):
        if abs(a[0]-b[0])+abs(a[1]-b[1])!=1: errors.append("ruta principal contiene salto no ortogonal"); break
    if any(p not in rooms for p in path): errors.append("ruta principal contiene sala inexistente")
    seen={start} if start in rooms else set(); q=deque(seen)
    while q:
        x,y=q.popleft()
        for n in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
            if n in rooms and n not in seen: seen.add(n); q.append(n)
    if seen!=rooms: errors.append("dungeon desconectada")
    if len(rooms)!=len(layout["rooms"]): errors.append("lista de rooms contiene duplicados")
    return errors

def validate_room(room_data):
    errors=[]; cols=int(room_data["cols"]); rows=int(room_data["rows"]); grid=room_data["grid"]
    if len(grid)!=rows or any(len(row)!=cols for row in grid): return ["dimensiones de grid inválidas"]
    doors=list(room_data.get("doors",()))
    valid={(cols//2,0),(cols//2,rows-1),(0,rows//2),(cols-1,rows//2)}
    for door in doors:
        if tuple(door) not in valid: errors.append("ancla de puerta inválida")
    perimeter=[]
    for x in range(cols):
        if grid[0][x]==0: perimeter.append((x,0))
        if grid[rows-1][x]==0: perimeter.append((x,rows-1))
    for y in range(rows):
        if grid[y][0]==0: perimeter.append((0,y))
        if grid[y][cols-1]==0: perimeter.append((cols-1,y))
    expected=set()
    for x,y in doors:
        expected.update(((x,y),(x,y-1)) if x in (0,cols-1) else ((x,y),(x-1,y)))
    if set(perimeter)!=expected: errors.append("aberturas de perímetro no coinciden con las puertas")
    floor={(x,y) for y,row in enumerate(grid) for x,value in enumerate(row) if value in (0,2,4)}
    if tuple(room_data["player_spawn"]) not in floor: errors.append("spawn del jugador no está sobre suelo")
    if not room_data.get("floor_surface"): errors.append("sala sin floor_surface")
    if not room_data.get("room_type"): errors.append("sala sin room_type")
    return errors
