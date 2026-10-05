"""Mundo de Fase 2: mazmorra global, salas, puertas dinámicas y flow-field local."""
import math
import random
from bisect import bisect_left
from collections import deque
from .gen import generate_layout, generate_room

TILE=32
FLOOR,WALL,PILLAR,SECRET,TORCH_PILLAR=0,1,2,3,4
INF=10**6
_NEIGH=((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1))

def bonfire_positions(arena):
    """Devuelve las posiciones deterministas de las hogueras de una arena.

    La misma función es usada por simulación y render para que una hoguera
    nunca pueda verse en una posición distinta de su hitbox.
    """
    key=(getattr(arena, "room_id", None), arena.cols, arena.rows, arena.biome, str(arena.grid))
    rng=random.Random(sum(ord(c) for c in str(key)))
    candidates=[]
    for ty in range(2, arena.rows-2):
        for tx in range(2, arena.cols-2):
            if arena.grid[ty][tx] != FLOOR:
                continue
            if all(arena.grid[ty+dy][tx+dx] == FLOOR for dx,dy in ((0,0),(1,0),(-1,0),(0,1),(0,-1))):
                candidates.append((tx,ty))
    rng.shuffle(candidates)
    chosen=[]
    torch_positions=[]
    for ty,row in enumerate(arena.grid):
        for tx,tile in enumerate(row):
            if tile == TORCH_PILLAR:
                torch_positions.append(arena.tile_center(tx,ty))
    desired=min(len(candidates), rng.randint(1,2))
    for tx,ty in candidates:
        x,y=arena.tile_center(tx,ty)
        if any(math.hypot(x-xx,y-yy) < TILE*4 for xx,yy in chosen):
            continue
        if any(math.hypot(x-xx,y-yy) < TILE*2.5 for xx,yy in torch_positions):
            continue
        chosen.append((x,y))
        if len(chosen) >= desired:
            break
    return chosen


class Door:
    __slots__=("side","open","locked","x","y")
    def __init__(self,side,x,y): self.side=side; self.open=False; self.locked=False; self.x=x; self.y=y

class Arena:
    def __init__(self, adata, room_id=(0,0)):
        self.room_id=room_id; self.cols=adata["cols"]; self.rows=adata["rows"]
        self.width,self.height=self.cols*TILE,self.rows*TILE
        self.biome=adata.get("biome","ruins"); self.name=adata.get("name",adata.get("room_type","Sala"))
        # Una sola superficie cubre toda la sala; nunca se mezclan PNG de suelo.
        self.floor_surface=adata.get("floor_surface")
        self.grid=[list(r) for r in adata["grid"]]
        self.decorations=list(adata.get("decorations", []))
        self.decoration_colliders=[]
        decoration_radii={
            "rock":18.0, "bush":16.0, "bench_small":22.0, "bench_large":28.0,
            "barrel_large":18.0, "signpost":13.0, "table":25.0, "counter":30.0,
            "crate_stack":28.0, "crate_pair":24.0, "wood_chest_decor":20.0,
            "fountain_active":32.0, "fountain_inactive":32.0, "fountain_small":23.0,
            "well_empty":31.0,
            # Las estatuas son grandes puntos físicos de interés.
            "statue_goddess":48.0, "statue_archer":48.0, "statue_assassin":48.0,
            "statue_knight":48.0, "statue_mage":48.0,
            # Cofres decorativos también bloquean el paso.
            "chest_gold_closed":22.0, "chest_gold_open":22.0,
            "chest_green_closed":22.0, "chest_green_open":22.0,
            "chest_purple_closed":22.0, "chest_purple_open":22.0,
            "chest_red_closed":22.0, "chest_red_open":22.0,
        }
        self._decoration_radii = decoration_radii
        for deco in self.decorations:
            kind=deco.get("kind")
            if kind in decoration_radii:
                self.decoration_colliders.append((
                    float(deco.get("x",0))*TILE+TILE/2,
                    float(deco.get("y",0))*TILE+TILE/2,
                    decoration_radii[kind], kind,
                ))
        # Las hogueras se generan como luces, pero también son objetos físicos.
        for bx,by in bonfire_positions(self):
            self.decoration_colliders.append((bx,by,16.0,"bonfire"))
        self.player_spawn=self.tile_center(*adata.get("player_spawn",(self.cols//2,self.rows//2)))
        self.enemy_spawns=[self.tile_center(*p) for p in adata.get("enemy_spawns",[])]
        self.item_spawns=[self.tile_center(*p) for p in adata.get("item_spawns",[])]
        self.room_type=adata.get("room_type","combat")
        self.doors={}
        for x,y in adata.get("doors",[]):
            side="N" if y==0 else "S" if y==self.rows-1 else "W" if x==0 else "E"
            self.doors[side]=Door(side,x,y)
        self._ensure_door_access()
        self.secrets=[]
        for x,y in adata.get("secrets",[]):
            self.grid[y][x]=SECRET; self.secrets.append((x,y))
    def _ensure_door_access(self):
        """Garantiza al menos un camino físico hacia cada puerta abierta.
        
        Las paredes de la sala ya deben ser navegables por diseño. Si una decoración
        indestructible tapa el único corredor, se elimina esa decoración del escenario
        en lugar de dejar al jugador sin salida.
        """
        if not self.doors:
            return

        def deco_blocked_tiles(decorations):
            blocked=set()
            for deco in decorations:
                kind=deco.get("kind")
                radius=float(self._decoration_radii.get(kind,0))
                if radius <= 0:
                    continue
                cx=float(deco.get("x",0))*TILE+TILE/2
                cy=float(deco.get("y",0))*TILE+TILE/2
                tx,ty=int(cx//TILE),int(cy//TILE)
                reach=max(0,int(math.ceil((radius+14)/TILE)))
                for yy in range(max(0,ty-reach),min(self.rows,ty+reach+1)):
                    for xx in range(max(0,tx-reach),min(self.cols,tx+reach+1)):
                        if math.hypot(xx*TILE+TILE/2-cx,yy*TILE+TILE/2-cy) <= radius+14:
                            blocked.add((xx,yy))
            return blocked

        def path_exists(door, blocked):
            start=(door.x,door.y)
            if door.side=="N": start=(door.x,1)
            elif door.side=="S": start=(door.x,self.rows-2)
            elif door.side=="W": start=(1,door.y)
            elif door.side=="E": start=(self.cols-2,door.y)
            goal=(int(self.player_spawn[0]//TILE),int(self.player_spawn[1]//TILE))
            q=deque([start]); seen={start}
            while q:
                x,y=q.popleft()
                if (x,y)==goal:
                    return True
                for dx,dy in _NEIGH:
                    nx,ny=x+dx,y+dy
                    if not (0<=nx<self.cols and 0<=ny<self.rows):
                        continue
                    if (nx,ny) in seen or (nx,ny) in blocked:
                        continue
                    if (nx,ny)==(door.x,door.y):
                        pass
                    elif self.solid_tile(nx,ny):
                        continue
                    if dx and dy and (self.solid_tile(x+dx,y) or self.solid_tile(x,y+dy)):
                        continue
                    seen.add((nx,ny)); q.append((nx,ny))
            return False

        # If the room's walls themselves make the door unreachable, do not destroy
        # scenery to hide a generation problem.
        for door in self.doors.values():
            if path_exists(door,set()):
                blocked=deco_blocked_tiles(self.decorations)
                if not path_exists(door,blocked):
                    candidates=[d for d in self.decorations if d.get("kind") in self._decoration_radii]
                    candidates.sort(key=lambda d: math.hypot(
                        float(d.get("x",0))*TILE+TILE/2-(door.x*TILE+TILE/2),
                        float(d.get("y",0))*TILE+TILE/2-(door.y*TILE+TILE/2)))
                    while candidates and not path_exists(door,blocked):
                        doomed=candidates.pop(0)
                        self.decorations.remove(doomed)
                        blocked=deco_blocked_tiles(self.decorations)

        # Rebuild physical decoration colliders after any safety removal.
        self.decoration_colliders=[]
        for deco in self.decorations:
            kind=deco.get("kind")
            if kind in self._decoration_radii:
                self.decoration_colliders.append((
                    float(deco.get("x",0))*TILE+TILE/2,
                    float(deco.get("y",0))*TILE+TILE/2,
                    self._decoration_radii[kind], kind,
                ))
        for bx,by in bonfire_positions(self):
            self.decoration_colliders.append((bx,by,16.0,"bonfire"))

    def solid_tile(self,tx,ty):
        if tx<0 or ty<0 or tx>=self.cols or ty>=self.rows:return True
        v=self.grid[ty][tx]
        if v==SECRET:return True
        for d in self.doors.values():
            if d.x==tx and d.y==ty:return not d.open
        return v!=FLOOR
    def point_solid(self,x,y): return self.solid_tile(int(math.floor(x/TILE)),int(math.floor(y/TILE)))
    def decoration_hits(self,x,y,radius):
        """Colisión circular contra decoración física del escenario."""
        for dx,dy,dr,_kind in self.decoration_colliders:
            ddx,ddy=x-dx,y-dy
            rr=float(radius)+dr
            if ddx*ddx+ddy*ddy < rr*rr:
                return (dx,dy,dr)
        return None
    def box_hits(self,x,y,h):
        x0,x1=int((x-h)//TILE),int((x+h)//TILE); y0,y1=int((y-h)//TILE),int((y+h)//TILE)
        return any(self.solid_tile(tx,ty) for ty in range(y0,y1+1) for tx in range(x0,x1+1))
    def move(self,x,y,dx,dy,r):
        h=r*.85; x+=dx
        if dx and self.box_hits(x,y,h):
            x=(int((x+h)//TILE)*TILE-h-.001) if dx>0 else ((int((x-h)//TILE)+1)*TILE+h+.001)
        y+=dy
        if dy and self.box_hits(x,y,h):
            y=(int((y+h)//TILE)*TILE-h-.001) if dy>0 else ((int((y-h)//TILE)+1)*TILE+h+.001)
        # Las decoraciones tienen volumen: expulsamos al actor suavemente hasta
        # quedar fuera de su huella, manteniendo el movimiento fluido.
        for _ in range(3):
            hit=self.decoration_hits(x,y,r*.86)
            if not hit: break
            cx,cy,cr=hit
            vx,vy=x-cx,y-cy
            dist=math.hypot(vx,vy)
            if dist < 0.001:
                vx,vy=1.0,0.0; dist=1.0
            push=(cr+r*.86-dist)+0.5
            x += vx/dist*push
            y += vy/dist*push
            if self.box_hits(x,y,h):
                # Si el empujón cae contra una pared, conserva la coordenada que
                # no estaba bloqueada para evitar atascar al jugador.
                tx,ty=x,y
                if self.box_hits(tx,y,h): tx=x-dx
                if self.box_hits(x,ty,h): ty=y-dy
                x,y=tx,ty
        return x,y
    def line_of_sight(self,x0,y0,x1,y1):
        d=math.hypot(x1-x0,y1-y0); n=int(d//8)+1
        return not any(self.point_solid(x0+(x1-x0)*i/n,y0+(y1-y0)*i/n) for i in range(1,n))
    def tile_of(self,x,y):return int(x//TILE),int(y//TILE)
    def tile_center(self,tx,ty):return tx*TILE+TILE/2,ty*TILE+TILE/2
    def open_doors(self):
        for d in self.doors.values(): d.open=True
    def close_doors(self):
        for d in self.doors.values(): d.open=False
    def break_secret(self,tx,ty):
        if 0<=tx<self.cols and 0<=ty<self.rows and self.grid[ty][tx]==SECRET:
            self.grid[ty][tx]=FLOOR
            # Carve a small 3x5 alcove only after the hidden wall is destroyed.
            if tx <= self.cols // 2:
                xs=range(1,3)
            else:
                xs=range(self.cols-3,self.cols-1)
            for xx in xs:
                for yy in range(max(1,ty-2),min(self.rows-1,ty+3)):
                    if self.grid[yy][xx] == WALL:
                        self.grid[yy][xx]=FLOOR
            return True
        return False
    def _can_step(self,x,y,dx,dy):
        nx,ny=x+dx,y+dy
        if self.solid_tile(nx,ny):return False
        return not (dx and dy and (self.solid_tile(x+dx,y) or self.solid_tile(x,y+dy)))
    def flow_field(self,tx,ty):
        dist=[[INF]*self.cols for _ in range(self.rows)]
        if self.solid_tile(tx,ty):return dist
        dist[ty][tx]=0;q=deque([(tx,ty)])
        while q:
            x,y=q.popleft(); nd=dist[y][x]+1
            for dx,dy in _NEIGH:
                if self._can_step(x,y,dx,dy) and dist[y+dy][x+dx]>nd:
                    dist[y+dy][x+dx]=nd;q.append((x+dx,y+dy))
        return dist
    def best_step(self,field,x,y):
        tx,ty=self.tile_of(x,y)
        if self.solid_tile(tx,ty):return None
        bd=field[ty][tx];best=None
        for dx,dy in _NEIGH:
            if self._can_step(tx,ty,dx,dy) and field[ty+dy][tx+dx]<bd:
                bd=field[ty+dy][tx+dx];best=(tx+dx,ty+dy)
        return self.tile_center(*best) if best else None

class Room:
    def __init__(self,rid,adata):
        self.id=tuple(rid); self.data=adata; self.room_type=adata.get("room_type","combat")
        self.items=[]; self.pickups=[]; self.decorations=list(adata.get("decorations", [])); self.cleared=self.room_type not in ("start","combat","elite","boss","challenge","miniboss"); self.entered=False
        self.special_resolved=False
        self.enemies_spawned=False; self.doors_locked=False
        self.arena=Arena(adata,self.id)

class Dungeon:
    BIOME_ORDER=("ruins","forest","dungeon","laboratory","volcanic","final")
    def __init__(self,seed=None,biome=None,difficulty=1):
        self.seed=seed if seed is not None else 0
        self.difficulty=max(1,int(difficulty))
        # Una dungeon completa usa un único bioma. El seed elige la temática al
        # comenzar la run; todas las salas, enemigos y decoraciones heredan esta
        # elección hasta el jefe final.
        if biome in self.BIOME_ORDER:
            self.biome=biome
        else:
            self.biome=self.BIOME_ORDER[abs(int(self.seed)) % len(self.BIOME_ORDER)]
        self.name={
            "ruins":"Ruinas Antiguas","forest":"Bosque Umbrío","dungeon":"Mazmorra Profunda",
            "laboratory":"Laboratorio Helix","volcanic":"Falla Ígnea","final":"Núcleo del Vacío"
        }.get(self.biome,self.biome.title())
        self.layout=generate_layout(self.seed)
        self.rooms={}
        path_set={tuple(x) for x in self.layout["path"]}; rng=random.Random(self.seed+7919)
        biome_order=[self.biome] * 6
        path_index={tuple(r):i for i,r in enumerate(self.layout["path"])}
        branch_types=["combat","combat","combat","elite","treasure","event","healing","challenge","secret","miniboss"]
        # Los jefes se espacian deliberadamente: nunca hay un jefe en la segunda sala
        # y cada zona dispone de varias salas antes de su jefe.
        path_len=len(self.layout["path"])
        zone_end_indices=[]
        prev=-1
        # Mantener seis zonas, pero variar ligeramente dónde termina cada una.
        # Así dos runs no repiten la misma secuencia de jefes aunque tengan
        # la misma cantidad total de zonas. La primera zona siempre tiene
        # al menos tres salas antes de su jefe y cada zona siguiente al menos dos.
        for zi in range(5):
            target=round((zi+1)*(path_len-1)/6)
            low=max(prev+2, 3 if zi==0 else prev+2)
            high=(path_len-1)-2*(5-zi)
            candidates=[i for i in range(low, high+1) if abs(i-target)<=1]
            if not candidates: candidates=[i for i in range(low, high+1)]
            end=rng.choice(candidates)
            zone_end_indices.append(end); prev=end
        zone_end_indices.append(path_len-1)
        boss_path_rooms={tuple(self.layout["path"][i]) for i in zone_end_indices}
        for rid in self.layout["rooms"]:
            tr=tuple(rid)
            if tr in boss_path_rooms: typ="boss"
            elif tr==tuple(self.layout["start"]): typ="start"
            elif tr in path_set:
                # La ruta principal también varía: no todas las salas previas al jefe son combate.
                idx=path_index[tr]
                zone=bisect_left(zone_end_indices, idx)
                local=idx-(zone_end_indices[zone-1] if zone else -1)
                if local==1 and rng.random()<0.18: typ="shop"
                elif local==2 and rng.random()<0.22: typ=rng.choice(("event","healing","treasure"))
                else: typ=rng.choices(("combat","elite","challenge"),(70,20,10))[0]
            else: typ=rng.choice(branch_types)
            idx=path_index.get(tr, min(path_index.get(n,0) for n in path_index if abs(n[0]-tr[0])+abs(n[1]-tr[1])<=2)) if path_index else 0
            zone=bisect_left(zone_end_indices, idx)
            room_biome=self.biome
            sides=[]
            for side,nrid in {"N":(rid[0],rid[1]-1),"S":(rid[0],rid[1]+1),"W":(rid[0]-1,rid[1]),"E":(rid[0]+1,rid[1])}.items():
                if nrid in self.rooms or nrid in [tuple(x) for x in self.layout["rooms"]]: sides.append(side)
            rs=generate_room(self.seed*1009+rid[0]*97+rid[1]*193,typ,room_biome,sides)
            rs["zone_index"]=zone
            self.rooms[tuple(rid)]=Room(rid,rs)
            self.rooms[tuple(rid)].portal_room = (typ == "boss" and zone == 5)
        # Regla de espaciado: salas especiales sin enemigos no pueden quedar juntas.
        # Los jefes y minibosses también deben tener al menos una sala intermedia.
        special_no_enemy={"shop","treasure","event","healing","secret","boss"}
        def adjacent(rid):
            x,y=rid
            return [q for q in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)) if q in self.rooms]

        def rebuild_type(rid,new_type):
            old=self.rooms[rid]
            sides=[side for side,nrid in {"N":(rid[0],rid[1]-1),"S":(rid[0],rid[1]+1),"W":(rid[0]-1,rid[1]),"E":(rid[0]+1,rid[1])}.items() if nrid in self.rooms]
            biome=old.arena.biome
            rs=generate_room(self.seed*1009+rid[0]*97+rid[1]*193,new_type,biome,sides)
            rs["zone_index"]=old.data.get("zone_index",0)
            room=Room(rid,rs)
            room.portal_room=getattr(old,"portal_room",False) and new_type=="boss"
            self.rooms[rid]=room

        for _ in range(3):
            changed=False
            for rid,room in list(self.rooms.items()):
                if rid==tuple(self.layout["start"]): continue
                typ=room.room_type
                if typ not in special_no_enemy and typ!="miniboss": continue
                for nrid in adjacent(rid):
                    other=self.rooms[nrid]
                    if nrid==tuple(self.layout["start"]): continue
                    if other.room_type not in special_no_enemy and other.room_type!="miniboss": continue
                    # Nunca se convierte un boss; se reemplaza la sala especial contigua.
                    if typ=="boss" and other.room_type!="boss":
                        rebuild_type(nrid,"combat")
                    elif other.room_type=="boss" and typ!="boss":
                        rebuild_type(rid,"combat")
                    elif typ!="boss":
                        rebuild_type(rid,"combat")
                    else:
                        continue
                    changed=True
                    break
                if changed: break
            if not changed: break

        # Fase 3: cada dungeon ofrece al menos una tienda accesible; se coloca en una rama existente.
        if not any(r.room_type == "shop" for r in self.rooms.values()):
            branch=[rid for rid in self.rooms if rid not in path_set and rid not in (tuple(self.layout["start"]),tuple(self.layout["boss"])) and all(self.rooms[n].room_type not in special_no_enemy and self.rooms[n].room_type!="miniboss" for n in adjacent(rid))]
            if branch:
                rid=rng.choice(branch); room=self.rooms[rid]
                sides=[]
                for side,nrid in {"N":(rid[0],rid[1]-1),"S":(rid[0],rid[1]+1),"W":(rid[0]-1,rid[1]),"E":(rid[0]+1,rid[1])}.items():
                    if nrid in self.rooms: sides.append(side)
                rs=generate_room(self.seed*1009+rid[0]*97+rid[1]*193,"shop",room.arena.biome,sides)
                room2=Room(rid,rs); self.rooms[rid]=room2
                room2.portal_room=False
        self.current=tuple(self.layout["start"]); self.rooms[self.current].entered=True
    @property
    def room(self):return self.rooms[self.current]
    def neighbor(self,rid,side):
        x,y=rid; return {"N":(x,y-1),"S":(x,y+1),"W":(x-1,y),"E":(x+1,y)}[side]
    def transition(self,side):
        nxt=self.neighbor(self.current,side)
        if nxt not in self.rooms or not self.room.arena.doors.get(side,Door(side,0,0)).open:return False
        self.current=nxt; return True
