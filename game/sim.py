"""Simulación pura de Fase 2. No importa pygame: mundo, generación, combate y loot son testeables."""
import math, random, copy
from .world import Dungeon, TILE, TORCH_PILLAR, bonfire_positions
from .player import Player
from .weapons import WeaponState
from .projectiles import ProjectilePool
from .enemies import Enemy
from .bosses import Boss
from .items import make_item, apply_item_bonuses
from .chests import Chest
from .statues import STATUE_BUFFS, statue_cost, statue_offer
from .systems.status_effects import damage_shield, apply_dot, update_dot_effects, apply_freeze, freeze_duration
from .systems.pickups import update_pickups
from .systems.hazards import update_hazards
from .systems.shop import setup_shop, buy_shop_offer
from .systems.rewards import spawn_chest, open_chest, drop_room_reward
from .systems.interaction import try_interact
from .systems.combat import _laser_hit_target, _update_lasers, start_enemy_laser, update_player_laser, stop_player_laser, _hit_enemies, _explode_projectile, _update_projectiles, perform_melee_attack, perform_fist_attack, _damage_props, spawn_projectile

class Input:
    def __init__(self):
        self.move_x=self.move_y=0.; self.aim_x=self.aim_y=0.; self.fire_held=self.fire_pressed=self.fire_released=False
        self.reload_pressed=self.dash_pressed=self.interact_pressed=self.switch_weapon_pressed=self.ability_pressed=False
    def clear_edges(self):
        self.fire_pressed=self.fire_released=self.reload_pressed=self.dash_pressed=self.interact_pressed=self.switch_weapon_pressed=self.ability_pressed=False

class Sim:
    def __init__(self,data,char_id,arena_id="ruins_plaza",seed=None,meta_upgrades=None,character_progress=None,difficulty=1):
        self.data=data; self.seed=seed if seed is not None else random.SystemRandom().randrange(1,2**31); self.rng=random.Random(self.seed)
        self.difficulty=max(1,int(difficulty)); self.dungeon=Dungeon(self.seed,None,self.difficulty); self.room=self.dungeon.room; self.arena=self.room.arena
        c=data.characters[char_id]; self.meta_upgrades=meta_upgrades or {}
        self.player=Player(c,data.weapons[c.start_weapon],self.arena.player_spawn,self.meta_upgrades,character_progress)
        self.player.inventory=[self.player.weapon]; self.player.items=[]; self.player.bonus_pierce=0; self.player.bonus_projectiles=0; self.player.attack_speed_mult=1.0; self.player.coin_radius=0
        self.pool=ProjectilePool(); self.enemies=[]; self.enemy_pool=[]; self.items=[]; self.pickups=[]; self.keys=0; self.events=[]; self.chest=None
        self.props=[]; self.hazards=[]; self.wave_attacks=[]; self.lasers=[]; self.drones=[]; self.allies=[]
        self.decoration_collider_provider=None
        self.time=0.; self.wave=0; self.wave_delay=0.5; self.over=False; self.victory=False; self.portal=False; self.portal_position=(self.arena.width/2,self.arena.height/2)
        self.stats={"kills":0,"shots":0,"damage_taken":0,"waves":0,"coins":0,"rooms":1,"items":0,"purchases":0,"abilities":0,"bosses_defeated":0,"xp":0,"weapon_usage":{}}
        self._flow_tile=self.arena.tile_of(self.player.x,self.player.y); self._flow_refresh=0.; self.flow=self.arena.flow_field(*self._flow_tile)
        self.shop_offers=[]; self.revealed_secrets=set()
        self.merchant_variant_by_room={}
        self.statue_menu=None
        self.statue_buffs=[]
        self.statue_used=set()
        self._enter_room(self.room,initial=True)
    def _obstacle_clear_to(self, x0, y0, x1, y1, radius=0.0):
        """Checks walls, props and physical decorations along a segment."""
        if not self.arena.line_of_sight(x0, y0, x1, y1):
            return False
        steps=max(1,int(math.hypot(x1-x0,y1-y0)//7))
        for i in range(1,steps+1):
            t=i/steps; x=x0+(x1-x0)*t; y=y0+(y1-y0)*t
            if self._decoration_collision(x,y,radius):
                return False
            for prop in self.props:
                if prop.get("broken"): continue
                rr=float(prop.get("radius",0))+radius
                if rr>0 and math.hypot(x-prop["x"],y-prop["y"])<=rr:
                    return False
        return True

    def _wave_clear_to(self, x0, y0, x1, y1):
        """LOS para ondas: paredes, props y decoraciones bloquean la propagación."""
        # _obstacle_clear_to ya comprueba paredes, decoraciones y props a lo largo
        # del segmento; no repetir esa misma pasada aquí.
        return self._obstacle_clear_to(x0,y0,x1,y1)

    def emit(self,kind,*args):
        if len(self.events)<250:self.events.append((kind,)+args)
    def select_weapon_slot(self, slot):
        p=self.player
        p.selected_slot=max(0,min(2,int(slot)))
        p.weapon=p.inventory[p.selected_slot] if p.selected_slot < len(p.inventory) else None
        # An empty slot is a valid selection: the player fights with fists.
        # Stop any laser state from the previously equipped weapon before
        # switching to the empty slot.
        if p.weapon is None:
            self.lasers=[l for l in self.lasers if l.get("owner") is not p]
        self.emit("weapon_switch",p.x,p.y)

    def _target_line_clear(self, x0, y0, x1, y1):
        """Target visibility including physical decorations and props."""
        if hasattr(self, "_obstacle_clear_to"):
            return self._obstacle_clear_to(x0, y0, x1, y1)
        return self.arena.line_of_sight(x0, y0, x1, y1)

    def enemy_target(self, enemy):
        """Selecciona jugador o dron, manteniendo el objetivo durante un breve lock."""
        p=self.player
        candidates=[{"x":p.x,"y":p.y,"kind":"player","obj":p}]
        for d in self.drones:
            if d.get("hp",0)>0:
                candidates.append({"x":d["x"],"y":d["y"],"kind":"drone","obj":d})

        # No se cambia de objetivo cada frame. Esto es especialmente importante
        # cuando Mira despliega varios drones: evita que los NPC hagan flicker
        # entre objetivos y parezca que están apuntando a todos a la vez.
        locked=getattr(enemy,"target",None)
        if locked is not None and getattr(enemy,"target_lock_timer",0.0)>0:
            obj=locked.get("obj")
            alive=(obj is p and p.alive) or (obj in self.drones and obj.get("hp",0)>0)
            if alive:
                locked["x"]=obj.x if hasattr(obj,"x") else obj.get("x",locked["x"])
                locked["y"]=obj.y if hasattr(obj,"y") else obj.get("y",locked["y"])
                dist=math.hypot(locked["x"]-enemy.x,locked["y"]-enemy.y)
                if (dist <= float(getattr(enemy.d,"detect_range",700))
                        and self._target_line_clear(enemy.x,enemy.y,locked["x"],locked["y"])):
                    return locked

        visible=[]
        for target in candidates:
            dist=math.hypot(target["x"]-enemy.x,target["y"]-enemy.y)
            if (dist <= float(getattr(enemy.d,"detect_range",700))
                    and self._target_line_clear(enemy.x,enemy.y,target["x"],target["y"])):
                visible.append((dist,target))
        if not visible:
            chosen=candidates[0]
        else:
            visible.sort(key=lambda q:q[0])
            # Drones remain attractive targets, but selection happens only when
            # the previous lock expires or becomes invalid.
            drones=[q for q in visible if q[1]["kind"]=="drone"]
            if drones and self.rng.random()<0.30:
                chosen=min(drones,key=lambda q:q[0])[1]
            else:
                chosen=visible[0][1]
        enemy.target=chosen
        enemy.target_lock_timer=1.15
        return chosen

    def spawn_drone(self, angle=0.0):
        from .systems.drones import spawn_drone
        return spawn_drone(self, angle)

    def _drone_collision(self, x, y, radius):
        from .systems.drones import drone_collision
        return drone_collision(self, x, y, radius)

    def _safe_drone_position(self, x, y, radius, avoid_player=True):
        from .systems.drones import safe_drone_position
        return safe_drone_position(self, x, y, radius, avoid_player)

    def _drone_path_clear(self, x0, y0, x1, y1, radius):
        from .systems.drones import drone_path_clear
        return drone_path_clear(self, x0, y0, x1, y1, radius)

    def _drone_move(self, drone, dx, dy):
        from .systems.drones import drone_move
        return drone_move(self, drone, dx, dy)

    def _update_drones(self, dt):
        from .systems.drones import update_drones
        return update_drones(self, dt)

    def damage_drone(self, drone, amount, sx=0.0, sy=0.0):
        from .systems.drones import damage_drone
        return damage_drone(self, drone, amount, sx, sy)

    def spawn_projectile(self, *a):
        return spawn_projectile(self, *a)
    def _new_enemy(self, edef, x, y, summoned=False):
        scaled_def=copy.copy(edef)
        variants=getattr(self.data, "enemy_variants", {})
        chance=float(variants.get("chance", 0.0)) if isinstance(variants, dict) else 0.0
        if not summoned and self.wave >= int(variants.get("min_wave", 2)) and self.rng.random() < chance:
            families=variants.get("families", {}) if isinstance(variants, dict) else {}
            sprite_set=getattr(edef, "sprite_set", None)
            candidates=families.get(sprite_set) or families.get("*") or []
            if candidates:
                theme_ids={
                    "volcanic":{"crimson","ember","golem_ember","golem_bomb","ash"},
                    "forest":{"venom","frost"},
                    "laboratory":{"void"},
                    "final":{"void","ash","crimson","ember"},
                    "dungeon":{"ash","void"},
                    "ruins":{"ash","venom","frost"},
                }.get(self.arena.biome,set())
                if theme_ids:
                    themed=[v for v in candidates if v.get("id") in theme_ids or
                            (self.arena.biome=="volcanic" and v.get("damage_type") in ("fire","explosive")) or
                            (self.arena.biome=="forest" and v.get("damage_type") in ("poison","ice")) or
                            (self.arena.biome=="laboratory" and v.get("damage_type") in ("electric","energy"))]
                    if themed and self.rng.random()<0.72:
                        candidates=themed
                variant=self.rng.choice(candidates)
                for key,value in variant.items():
                    if key in ("id","name_suffix","tint","projectile_color","hue_shift","saturation","lightness"):
                        continue
                    if key.endswith("_mult"):
                        base=float(getattr(scaled_def, key[:-5], 1.0))
                        setattr(scaled_def, key[:-5], base*float(value))
                    else:
                        setattr(scaled_def, key, value)
                scaled_def.variant_id=variant.get("id")
                scaled_def.variant_name_suffix=variant.get("name_suffix","")
                scaled_def.variant_tint=tuple(variant.get("tint", getattr(edef, "color", (200,80,80))))
                scaled_def.projectile_color=tuple(variant.get("projectile_color", scaled_def.variant_tint))
                scaled_def.variant_hue_shift=float(variant.get("hue_shift", 0.0))
                scaled_def.variant_saturation=float(variant.get("saturation", 0.0))
                scaled_def.variant_lightness=float(variant.get("lightness", 0.0))
        scale=1.0 + 0.12*(self.difficulty-1)
        scaled_def.hp=float(scaled_def.hp)*scale
        scaled_def.damage=float(scaled_def.damage)*scale
        scaled_def.speed=float(scaled_def.speed)*(1.0 + 0.035*(self.difficulty-1))
        # Si el enemigo tiene un proyectil visual propio (bola de fuego, roca, etc.),
        # su arquetipo debe ser a distancia aunque un dato antiguo lo haya marcado
        # como melee. Esto evita que el comportamiento contradiga la animación.
        if getattr(edef, "projectile_asset_sheet", None):
            scaled_def.ai = "ranged"
        else:
            weapon_id = getattr(edef, "weapon_id", None)
            weapon_def = self.data.weapons.get(weapon_id) if weapon_id else None
            if weapon_def is not None and getattr(weapon_def, "projectile_sprite", None) and getattr(weapon_def, "class", "") != "melee":
                scaled_def.ai = "ranged"
        if self.enemy_pool:
            e=self.enemy_pool.pop()
            e.reset(scaled_def,x,y,self.rng)
        else:
            e=Enemy(scaled_def,x,y,self.rng)
        e.is_summoned=summoned
        return e

    def count_summoned(self):
        return sum(1 for e in self.enemies if getattr(e, "is_summoned", False) and e.alive)

    def spawn_summons(self, source, ids, count=1):
        """Invoca esbirros en puntos transitables, con un bloque de margen."""
        pool=[self.data.enemies[i] for i in ids if i in self.data.enemies]
        if not pool:
            return False
        spawned=0
        for _ in range(max(1,int(count))):
            if self.count_summoned() >= 7:
                break
            d=self.rng.choice(pool)
            min_sep=source.radius+d.radius+7
            candidates=[]
            for ty in range(1,self.arena.rows-1):
                for tx in range(1,self.arena.cols-1):
                    px,py=self.arena.tile_center(tx,ty)
                    dist=math.hypot(px-source.x,py-source.y)
                    if dist < min_sep or dist > TILE*5.5:
                        continue
                    candidates.append((dist+self.rng.random()*7,px,py))
            candidates.sort(key=lambda q:q[0])
            chosen=None
            for _,px,py in candidates:
                safe=self._safe_npc_position(px,py,float(d.radius))
                if safe is not None:
                    chosen=safe; break
            if chosen is None:
                for ty in range(1,self.arena.rows-1):
                    for tx in range(1,self.arena.cols-1):
                        px,py=self.arena.tile_center(tx,ty)
                        safe=self._safe_npc_position(px,py,float(d.radius))
                        if safe is not None:
                            chosen=safe; break
                    if chosen is not None:
                        break
            if chosen is None:
                continue
            px,py=chosen
            e=self._new_enemy(d,px,py,summoned=True)
            e.spawn_delay=0.8
            self.enemies.append(e)
            spawned+=1
        return spawned > 0

    def break_secret(self, tx, ty):
        """Las paredes especiales ya no son destructibles ni entregan loot; usa cajas para eso."""
        return False

    def on_player_hit(self,sx,sy,dmg):
        self.stats["damage_taken"]+=dmg; self.emit("player_hit",self.player.x,self.player.y,math.atan2(self.player.y-sy,self.player.x-sx))
    def _room_should_combat(self):return self.room.room_type in ("start","combat","elite","challenge","miniboss")
    def _enter_room(self,room,initial=False):
        self.room=room; self.arena=room.arena
        # Loot y monedas pertenecen a la sala actual; nunca se comparten entre habitaciones.
        self.items=room.items
        self.pickups=room.pickups
        self.chest=getattr(room, "chest", None)
        # Las transiciones solo ocurren con la sala anterior resuelta; cualquier
        # entidad viva residual debe quedar fuera del nuevo contexto de sala.
        self.enemies=[]
        self.hazards=[]; self.wave_attacks=[]; self.lasers=[]
        # Mira mantiene sus drones entre salas; solo se reposicionan alrededor del jugador.
        if not getattr(room, "props_spawned", False):
            self._spawn_room_props(room); room.props_spawned=True
        self.props=getattr(room, "props", [])
        if self.drones:
            for idx, drone in enumerate(self.drones):
                angle = float(drone.get("orbit", 0.0)) + idx * (math.tau / max(1, len(self.drones)))
                # Reentrada lateral amplia y validada contra las hitboxes reales.
                desired_x = self.player.x + math.cos(angle) * 68.0
                desired_y = self.player.y + math.sin(angle) * 52.0
                drone["x"], drone["y"] = self._safe_drone_position(
                    desired_x, desired_y, float(drone.get("radius",10.0))
                )
                drone["orbit"] = angle
                drone["vx"] = drone["vy"] = 0.0
                drone["shot_cd"] = min(float(drone.get("shot_cd", 1.0)), 0.25)
            self.player.drones = self.drones
        self._flow_tile=self.arena.tile_of(self.player.x,self.player.y); self._flow_refresh=0.; self.flow=self.arena.flow_field(*self._flow_tile)
        if room.room_type=="boss" and not room.cleared:
            self.chest=None
            room.chest=None
            self.arena.close_doors(); self._spawn_boss(); room.enemies_spawned=True; room.doors_locked=True
        elif self._room_should_combat() and not room.cleared:
            self.chest=None
            room.chest=None
            self.arena.close_doors();
            if room.room_type=="miniboss": self._spawn_miniboss()
            else: self._spawn_room_enemies()
            room.enemies_spawned=True; room.doors_locked=True
        else:
            self.arena.open_doors()
            self.chest=getattr(room, "chest", None)
            if not room.special_resolved and not initial: self._resolve_special_room(room)
        if room.room_type == "shop":
            room_key = tuple(getattr(room, "id", getattr(self.arena, "room_id", (0, 0))))
            if room_key not in self.merchant_variant_by_room:
                self.merchant_variant_by_room[room_key] = self.rng.randrange(3)
            if not getattr(room, "shop_initialized", False):
                self._setup_shop()
                room.shop_offers = self.shop_offers
                room.shop_initialized = True
            else:
                self.shop_offers = room.shop_offers
        else:
            # Las ofertas pertenecen exclusivamente a la tienda actual.
            self.shop_offers=[]
        self.emit("room_enter",room.id,room.room_type)
        room.entered=True

    def _spawn_room_props(self, room):
        """Genera grupos de cajas destructibles y algunos barriles elementales.

        Las cajas se colocan en pequeñas pilas de suelo (2-3 casillas contiguas),
        como obstáculos rompibles de una dungeon, dejando libres los accesos y
        las zonas de aparición de jugador/enemigos.
        """
        room.props=[]
        if room.room_type in ("start", "boss", "shop", "treasure", "healing"):
            room.props_spawned=True
            return
        occupied_tiles=set()
        protected=[self.arena.player_spawn, *self.arena.enemy_spawns]
        door_lanes=[]
        for d in self.arena.doors.values():
            door_lanes.append((d.x, d.y))
            if d.side == "N": door_lanes.extend((d.x, yy) for yy in (1,2,3))
            elif d.side == "S": door_lanes.extend((d.x, yy) for yy in (self.arena.rows-2,self.arena.rows-3,self.arena.rows-4))
            elif d.side == "W": door_lanes.extend((xx, d.y) for xx in (1,2,3))
            elif d.side == "E": door_lanes.extend((xx, d.y) for xx in (self.arena.cols-2,self.arena.cols-3,self.arena.cols-4))
        protected_tiles=set(door_lanes)
        protected_tiles.update(self.arena.tile_of(x,y) for x,y in protected)
        # La decoración también ocupa espacio físico: cajas/barriles no pueden
        # aparecer dentro de rocas, bancos, fuentes, estatuas, etc.
        protected_tiles.update((int(d.get("x",0)), int(d.get("y",0))) for d in self.arena.decorations)

        def valid_tile(tx, ty):
            if not (2 <= tx < self.arena.cols-2 and 2 <= ty < self.arena.rows-2):
                return False
            if (tx,ty) in occupied_tiles or (tx,ty) in protected_tiles:
                return False
            if self.arena.solid_tile(tx,ty):
                return False
            x,y=self.arena.tile_center(tx,ty)
            if any(math.hypot(x-a,y-b)<56 for a,b in protected):
                return False
            return True

        def add_prop(kind, tx, ty):
            x,y=self.arena.tile_center(tx,ty)
            hp=2 if kind=="crate" else 1
            room.props.append({"kind":kind,"x":x,"y":y,"hp":hp,"max_hp":hp,
                               "broken":False,"fade":0.0,"radius":15 if kind=="crate" else 24})
            occupied_tiles.add((tx,ty))

        # 2-4 grupos por sala; cada grupo comparte una línea de cajas de 2 o 3.
        group_count=self.rng.randint(2,4)
        for _ in range(group_count*8):
            if sum(1 for p in room.props if p["kind"]=="crate") >= 10:
                break
            tx=self.rng.randint(3,self.arena.cols-4)
            ty=self.rng.randint(3,self.arena.rows-4)
            length=self.rng.choice((2,2,3))
            horizontal=self.rng.random()<0.65
            cells=[(tx+i,ty) for i in range(length)] if horizontal else [(tx,ty+i) for i in range(length)]
            if all(valid_tile(x,y) for x,y in cells):
                for x,y in cells:
                    add_prop("crate",x,y)
                if sum(1 for p in room.props if p["kind"]=="crate") >= 6 and self.rng.random()<0.65:
                    break

        # Unos pocos barriles elementales acompañan las cajas, sin saturar la sala.
        barrel_count=self.rng.randint(1,3)
        for _ in range(barrel_count*10):
            if sum(1 for p in room.props if p["kind"]!="crate") >= barrel_count:
                break
            tx=self.rng.randint(2,self.arena.cols-3); ty=self.rng.randint(2,self.arena.rows-3)
            if not valid_tile(tx,ty):
                continue
            kind=self.rng.choices(["fire","poison","electric"],[0.34,0.34,0.32])[0]
            add_prop(kind,tx,ty)
        room.props_spawned=True

    def _safe_drop_position(self, x, y, radius=8.0):
        """Devuelve una posición de loot dentro de la sala y fuera de sólidos.

        Los actores pueden morir muy cerca de paredes o puertas. Un drop basado
        directamente en su posición podía quedar parcialmente fuera del mapa.
        Primero se limita al área física de la sala y, si esa zona está ocupada,
        se busca la casilla transitable más cercana.
        """
        margin=max(2.0, float(radius))
        x=max(margin, min(self.arena.width-margin, float(x)))
        y=max(margin, min(self.arena.height-margin, float(y)))
        if not self.arena.box_hits(x, y, margin):
            return x, y
        tx,ty=self.arena.tile_of(x,y)
        max_r=max(self.arena.cols,self.arena.rows)
        for r in range(1,max_r+1):
            for oy in range(-r,r+1):
                for ox in range(-r,r+1):
                    if max(abs(ox),abs(oy)) != r: continue
                    qx,qy=tx+ox,ty+oy
                    if qx<0 or qy<0 or qx>=self.arena.cols or qy>=self.arena.rows: continue
                    if self.arena.solid_tile(qx,qy): continue
                    px,py=self.arena.tile_center(qx,qy)
                    if not self.arena.box_hits(px,py,margin):
                        return px,py
        # Todas las casillas cercanas están ocupadas; usa el spawn como último recurso.
        sx,sy=self.arena.player_spawn
        return max(margin,min(self.arena.width-margin,sx)), max(margin,min(self.arena.height-margin,sy))

    def _crate_collision(self, x, y, radius):
        """Comprueba la huella visible de las cajas, con fallback a una casilla."""
        provider=getattr(self, "decoration_collider_provider", None)
        for prop in self.props:
            if prop.get("broken") or prop.get("kind")!="crate": continue
            if provider is not None:
                shape=provider.prop_collider(prop) if hasattr(provider,"prop_collider") else None
                if shape:
                    cx,cy,rx,ry=shape
                    dx=(x-cx)/max(1.0,rx+radius); dy=(y-cy)/max(1.0,ry+radius)
                    if dx*dx+dy*dy<1.0: return True
                    continue
            half=TILE*0.5
            if abs(x-prop["x"]) < half+radius and abs(y-prop["y"]) < half+radius: return True
        return False

    def _decoration_collision(self, x, y, radius):
        """Colisión basada en la silueta visible cuando el renderer la conoce.

        El proveedor visual usa el alpha real del PNG; la simulación conserva el
        radio clásico como fallback para tests/headless.
        """
        provider=getattr(self, "decoration_collider_provider", None)
        if provider is not None:
            for deco in getattr(self.arena, "decorations", []):
                if hasattr(provider, "decoration_overlap"):
                    if provider.decoration_overlap(deco, x, y, radius):
                        return (x, y, radius)
                    continue
                shape=provider.decoration_collider(deco) if hasattr(provider,"decoration_collider") else provider(deco)
                if not shape: continue
                cx,cy,rx,ry=shape
                dx=(x-cx)/max(1.0,rx+radius)
                dy=(y-cy)/max(1.0,ry+radius)
                if dx*dx+dy*dy < 1.0:
                    return (cx,cy,max(rx,ry))
            # Las hogueras siguen usando la colisión física del mapa.
            for bx,by,br,kind in getattr(self.arena, "decoration_colliders", []):
                if kind=="bonfire" and math.hypot(x-bx,y-by) < br+radius:
                    return (bx,by,br)
            return None
        return self.arena.decoration_hits(x, y, radius)

    def _chest_collision(self, x, y, radius):
        chest=self.chest
        if chest is None:
            return False
        provider=getattr(self,"decoration_collider_provider",None)
        if provider is not None and hasattr(provider,"chest_collider"):
            shape=provider.chest_collider(chest)
            if shape:
                cx,cy,rx,ry=shape
                dx=(x-cx)/max(1.0,rx+radius); dy=(y-cy)/max(1.0,ry+radius)
                return dx*dx+dy*dy<1.0
        half=TILE*0.5
        return abs(x-float(chest.x)) < half+radius and abs(y-float(chest.y)) < half+radius

    def _world_collision(self, x, y, radius):
        # Solo los objetos que tienen una huella física real pueden bloquear al actor.
        # Los cofres NO son obstáculos: su interacción se resuelve por distancia.
        # Esto evita una hitbox invisible alrededor del cofre cuando su sprite,
        # variante o collider visual no coincide con el estado de la sala.
        return (self._decoration_collision(x,y,radius) or
                self._crate_collision(x,y,radius))

    def move_actor(self, x, y, dx, dy, radius):
        """Movimiento contra paredes y objetos físicos, usando colisiones de PNG en gameplay."""
        # Arena conserva su collider circular legacy para consumidores headless,
        # pero durante gameplay Sim usa el alpha real de los modelos.
        nx,ny=self.arena.move(x,y,dx,dy,radius,include_decorations=False)
        if not self._world_collision(nx,ny,radius):
            return nx,ny
        xx,xy=self.arena.move(x,y,dx,0,radius,include_decorations=False)
        if self._world_collision(xx,xy,radius):
            xx,xy=x,y
        yx,yy=self.arena.move(xx,xy,0,dy,radius,include_decorations=False)
        if self._world_collision(yx,yy,radius):
            yx,yy=xx,xy
        return yx,yy

    def _break_prop(self, prop, source_color=None):
        if prop.get("broken"): return
        prop["broken"]=True; prop["fade"]=2.2
        x,y=prop["x"],prop["y"]
        kind=prop["kind"]
        if kind=="crate":
            x,y=self._safe_drop_position(x,y,8.0)
            self.emit("crate_break",x,y)
            # Las cajas deben ofrecer consumibles con una frecuencia útil sin convertir
            # cada caja en una curación garantizada. La poción de curación pasa al 12%.
            # Energía: 8%. Monedas: 5%.
            roll=self.rng.random()
            if roll<0.12: self.items.append(type("Loot",(),{"kind":"heal","x":x,"y":y})())
            elif roll<0.20: self.items.append(type("Loot",(),{"kind":"energy","x":x,"y":y})())
            elif roll<0.55:
                # 35% de probabilidad de que una caja entregue cargadores.
                self.items.append(type("AmmoLoot",(),{"kind":"ammo","x":x,"y":y,"magazines":self.rng.choice((1,1,2))})())
            # Las esferas amarillas fueron retiradas.
        else:
            dtype={"fire":"fire","poison":"poison","electric":"electric"}[kind]
            color={"fire":(245,70,45),"poison":(70,220,85),"electric":(175,70,255)}[dtype]
            self.hazards.append({"x":x,"y":y,"radius":TILE*2.5,"life":9.0,"max_life":9.0,"tick":0.0,"particle_timer":0.0,"particles":[],"dtype":dtype,"color":color,"damage":1.0})
            self.emit("barrel_burst",x,y,dtype)

    def _damage_props(self, x, y, damage, explosive=False, color=None):
        return _damage_props(self, x, y, damage, explosive, color)
    def _resolve_special_room(self,room):
        room.special_resolved=True
        cx,cy=self.arena.width/2,self.arena.height/2
        if room.room_type=="treasure":
            self._spawn_chest("common")
            room.chest=self.chest
        elif room.room_type=="healing":
            old=self.player.hp; self.player.hp=min(self.player.max_hp,self.player.hp+3)
            self.player.shield=min(self.player.max_shield,self.player.shield+2)
            old_energy=self.player.energy; self.player.energy=min(self.player.max_energy,self.player.energy+25)
            self.player.set_status("heal", 1.8); self.player.set_status("shield", 2.2)
            self.player.feedback_flash("heal",.26)
            if self.player.energy>old_energy:
                self.player.feedback_flash("energy",.26); self.emit("energy_pickup",cx,cy,self.player.energy-old_energy)
            self.emit("heal_pickup",cx,cy,self.player.hp-old); self.emit("heal_room",cx,cy,self.player.hp-old)
        elif room.room_type=="event":
            # Evento de riesgo/recompensa: ofrece moneda y un objeto, sin bloquear la run.
            gain=12+self.rng.randint(0,10); self.player.coins+=gain; self.stats["coins"]+=gain
            self._drop_room_reward(guaranteed=True,quality=1)
            self.emit("event_reward",cx,cy,gain)
        elif room.room_type=="secret":
            self._drop_room_reward(guaranteed=True,quality=3)
            self.keys+=1; self.emit("secret_reward",cx,cy)

    def _spawn_miniboss(self):
        pool=[e for e in self.data.enemies.values() if e.min_wave>=2 and getattr(e,"sprite_set",None)]
        e=self.rng.choice(pool or [x for x in self.data.enemies.values() if getattr(x,"sprite_set",None)])
        desired_x,desired_y=self.arena.tile_center(self.arena.cols//2,self.arena.rows//3)
        safe=self._safe_npc_position(desired_x,desired_y,float(e.radius),min_distance=120)
        if safe is None:
            return
        x,y=safe
        mini_def=copy.copy(e); mini_def.hp*=2.45; mini_def.damage*=1.25; mini_def.speed*=.94
        mini_def.radius*=1.16; mini_def.sprite_scale=float(getattr(e,"sprite_scale",3.5))*1.12
        mini_def.miniboss_pulse_interval=4.2
        mini=Enemy(mini_def,x,y,self.rng); mini.is_miniboss=True
        scale=1.0 + 0.14*(self.difficulty-1); mini.hp*=scale; mini.max_hp=mini.hp; mini.d.damage*=scale
        self.enemies.append(mini); self.emit("miniboss_spawn",x,y,e.name)
    def _safe_npc_position(self, desired_x, desired_y, radius, min_distance=0.0, occupied=()):
        """Busca un spawn con un bloque completo de margen respecto a paredes y decoraciones."""
        radius=float(radius)
        margin=radius + TILE
        occupied=tuple(occupied or ())

        def valid(x, y):
            if x < margin or y < margin or x > self.arena.width-margin or y > self.arena.height-margin:
                return False
            if self.arena.box_hits(x, y, margin):
                return False
            if self._decoration_collision(x, y, margin):
                return False
            if self._crate_collision(x, y, margin):
                return False
            if min_distance > 0 and math.hypot(x-self.player.x, y-self.player.y) < min_distance:
                return False
            for ox, oy, oradius in occupied:
                if math.hypot(x-ox, y-oy) < radius + float(oradius) + TILE:
                    return False
            for other in self.enemies:
                if not getattr(other, "alive", False):
                    continue
                if math.hypot(x-other.x, y-other.y) < radius + float(other.radius) + 8:
                    return False
            return True

        base_tx, base_ty=self.arena.tile_of(desired_x, desired_y)
        max_r=max(self.arena.cols, self.arena.rows)
        for ring in range(max_r):
            candidates=[]
            for dy in range(-ring, ring+1):
                for dx in range(-ring, ring+1):
                    if max(abs(dx),abs(dy)) != ring:
                        continue
                    tx,ty=base_tx+dx,base_ty+dy
                    if tx < 0 or ty < 0 or tx >= self.arena.cols or ty >= self.arena.rows:
                        continue
                    px,py=self.arena.tile_center(tx,ty)
                    if valid(px,py):
                        candidates.append((math.hypot(px-desired_x,py-desired_y),px,py))
            if candidates:
                candidates.sort(key=lambda q:q[0])
                return candidates[0][1],candidates[0][2]
        return None
    def _spawn_room_enemies(self):
        self.wave+=1; self.stats["waves"]=max(self.stats["waves"],self.wave)
        budget=self.data.rooms.get(self.room.room_type,{}).get("enemy_budget",5) or 5
        budget=min(12,budget+min(self.wave,3))
        biome_pool=self.data.biomes.get(self.arena.biome,{}).get("enemy_pool",[])
        pool=[self.data.enemies[eid] for eid in biome_pool if eid in self.data.enemies and self.data.enemies[eid].min_wave<=self.wave]
        if not pool: pool=[e for e in self.data.enemies.values() if e.min_wave<=self.wave]
        spots=list(self.arena.enemy_spawns) or [self.arena.player_spawn]; self.rng.shuffle(spots)
        weights=[e.weight for e in pool]
        for idx,e in enumerate(pool):
            wid=getattr(e,"weapon_id",None)
            wd=self.data.weapons.get(wid) if wid else None
            dtype=str(getattr(wd,"damage_type","")) if wd else ""
            if self.arena.biome=="volcanic":
                weights[idx] *= 3.2 if dtype in ("fire","explosive") else 0.48
            elif self.arena.biome=="forest":
                weights[idx] *= 1.8 if dtype in ("poison","ice") else 0.72
            elif self.arena.biome=="laboratory":
                weights[idx] *= 1.7 if dtype in ("energy","electric") else 0.8
            elif self.arena.biome=="final":
                weights[idx] *= 1.25 if dtype in ("void","energy","fire","ice") else 0.75
        used=[]
        for i in range(min(budget,len(spots))):
            e=self.rng.choices(pool,weights)[0]
            candidates=spots[i:]+spots[:i]
            chosen=None
            for sx,sy in candidates:
                pos=self._safe_npc_position(sx,sy,float(e.radius),min_distance=120,occupied=used)
                if pos is not None:
                    chosen=pos; break
            if chosen is None:
                for _ in range(80):
                    sx=self.rng.uniform(TILE,self.arena.width-TILE)
                    sy=self.rng.uniform(TILE,self.arena.height-TILE)
                    pos=self._safe_npc_position(sx,sy,float(e.radius),min_distance=120,occupied=used)
                    if pos is not None:
                        chosen=pos; break
            if chosen is not None:
                sx,sy=chosen
                used.append((sx,sy,float(e.radius)))
                self.enemies.append(self._new_enemy(e,sx,sy)); self.emit("spawn",sx,sy)

    def _setup_shop(self):
        """Compatibility facade for the extracted shop system."""
        return setup_shop(self)
    def _buy_shop_offer(self, offer):
        """Compatibility facade for the extracted shop purchase system."""
        return buy_shop_offer(self, offer)
    def _spawn_boss(self):
        biome=self.arena.biome
        boss_id=self.data.biome_bosses.get(biome) if hasattr(self.data,"biome_bosses") else None
        b=self.data.bosses.get(boss_id) if boss_id else None
        b=b or next(iter(self.data.bosses.values()))
        desired_x,desired_y=self.arena.tile_center(self.arena.cols//2,self.arena.rows//3)
        safe=self._safe_npc_position(desired_x,desired_y,float(getattr(b,"radius",28)),min_distance=120)
        if safe is None:
            return
        x,y=safe
        boss=Boss(b,x,y,self.rng, difficulty=self.difficulty)
        self.enemies.append(boss); self.emit("boss_spawn",x,y,b.name)
        biome_pool=self.data.biomes.get(biome,{}).get("enemy_pool",[])
        guard_pool=[self.data.enemies[eid] for eid in biome_pool if eid in self.data.enemies and self.data.enemies[eid].min_wave <= max(1,self.wave) and self.data.enemies[eid].radius <= 16 and getattr(self.data.enemies[eid],"sprite_set",None)]
        if not guard_pool:
            guard_pool=[e for e in self.data.enemies.values() if e.min_wave <= max(2,self.wave) and e.radius <= 16 and getattr(e,"sprite_set",None)]
        guard_count=min(4,max(2,len(self.arena.enemy_spawns)//4))
        candidates=list(self.arena.enemy_spawns) or [(x+TILE*3,y),(x-TILE*3,y),(x,y+TILE*3),(x,y-TILE*3)]
        candidates.sort(key=lambda pos:math.hypot(pos[0]-x,pos[1]-y))
        spawned=0
        for sx,sy in candidates:
            if spawned>=guard_count or math.hypot(sx-x,sy-y)<TILE*1.8: continue
            edef=self.rng.choice(guard_pool)
            safe=self._safe_npc_position(sx,sy,float(edef.radius),min_distance=120)
            if safe is None: continue
            sx,sy=safe
            guard=self._new_enemy(edef,sx,sy); guard.is_boss_guard=True; guard.spawn_delay=.45
            self.enemies.append(guard); self.emit("boss_guard_spawn",sx,sy,edef.name); spawned+=1
    def _complete_room(self):
        if self.room.cleared:return
        self.room.cleared=True; self.room.doors_locked=False; self.arena.open_doors(); self.emit("room_clear",self.room.id)
        self.room.chest=None
        chest_type = self._chest_type_for_room(self.room.room_type)
        if chest_type:
            self._spawn_chest(chest_type)
            self.room.chest=self.chest
            if self.chest is not None:
                if math.hypot(self.chest.x-self.player.x,self.chest.y-self.player.y) < TILE*1.35:
                    for ox,oy in ((TILE*2,0),(-TILE*2,0),(0,TILE*2),(0,-TILE*2)):
                        qx,qy=self._safe_drop_position(self.chest.x+ox,self.chest.y+oy,14.0)
                        if math.hypot(qx-self.player.x,qy-self.player.y) >= TILE*1.35:
                            self.chest.x,self.chest.y=qx,qy; break
        if self.room.room_type=="boss":
            usable=any((getattr(w.d,"class","")=="melee" and getattr(w,"durability",0)>0) or
                       (getattr(w.d,"class","")!="melee" and (getattr(w,"ammo",0)>0 or getattr(w,"reserve_magazines",0)>0))
                       for w in self.player.inventory)
            if not usable:
                choices=list(self.data.weapons)
                if choices:
                    wid=self.rng.choice(choices)
                    wx,wy=self._safe_drop_position(self.player.x+54,self.player.y,10.0)
                    it=type("WeaponEmergencyPickup",(),{"id":wid,"name":self.data.weapons[wid].name,"kind":"weapon","weapon_id":wid,"x":wx,"y":wy})()
                    self.items.append(it); self.stats["items"]+=1
                    self.emit("weapon_emergency",wx,wy,wid)
        if self.room.room_type=="boss" and self.room.arena.biome=="final":
            # El portal y el cofre final comparten la sala, pero nunca el mismo punto.
            cx,cy=self.arena.width/2,self.arena.height/2
            if self.chest is not None:
                self.chest.x,self.chest.y=cx-78,cy
            self.portal=True; self.portal_position=(cx+78,cy); self.emit("victory_portal",*self.portal_position)
    def _chest_type_for_room(self, room_type):
        return {
            "combat": "common",
            "elite": "rare",
            "challenge": "rare",
            "miniboss": "legendary",
            "boss": "legendary",
            "treasure": "common",
        }.get(room_type)

    def _spawn_chest(self, chest_type="common"):
        """Compatibility facade for the extracted reward/chest system."""
        return spawn_chest(self, chest_type)
    def _open_chest(self):
        """Compatibility facade for the extracted chest opening system."""
        return open_chest(self)
    def _drop_room_reward(self, guaranteed=False, quality=0, position=None):
        """Compatibility facade for the extracted room reward system."""
        return drop_room_reward(self, guaranteed, quality, position)
    def _active_statue(self):
        for deco in getattr(self.arena, "decorations", []):
            kind=deco.get("kind")
            statue_key=(tuple(self.room.id), int(deco.get("x",0)), int(deco.get("y",0)))
            if kind not in STATUE_BUFFS or statue_key in self.statue_used:
                continue
            x=float(deco.get("x",0))*TILE+TILE/2
            y=float(deco.get("y",0))*TILE+TILE/2+TILE
            if math.hypot(self.player.x-x,self.player.y-y) < 76:
                return deco, kind, x, y
        return None

    def _open_statue_menu(self):
        found=self._active_statue()
        if not found:
            return False
        deco,kind,x,y=found
        self.statue_menu=statue_offer(kind,self.difficulty)
        self.statue_menu["x"],self.statue_menu["y"]=x,y
        self.statue_menu["statue_key"]=(tuple(self.room.id), int(deco.get("x",0)), int(deco.get("y",0)))
        self.emit("statue_open",x,y,kind,self.statue_menu["cost"])
        return True

    def accept_statue_buff(self):
        offer=self.statue_menu
        if not offer:
            return False
        if self.player.coins < offer["cost"]:
            return False
        kind=offer["kind"]
        self.player.coins -= offer["cost"]
        self.statue_buffs.append(dict(offer))
        self.statue_used.add(tuple(offer.get("statue_key", (tuple(self.room.id), 0, 0))))
        self._apply_statue_buff(kind, offer["value"])
        self.statue_menu=None
        self.emit("statue_buff", self.player.x,self.player.y,kind,offer["value"])
        return True

    def close_statue_menu(self):
        self.statue_menu=None

    def _apply_statue_buff(self, kind, value):
        p=self.player
        if kind == "defense":
            p.statue_damage_taken_mult *= max(0.35, 1.0-value)
        elif kind == "melee":
            p.statue_melee_mult *= 1.0+value
        elif kind == "ranged":
            p.statue_ranged_mult *= 1.0+value
        elif kind == "ability":
            p.statue_ability_mult *= 1.0+value
        elif kind == "critical":
            p.crit_chance += value
            p.statue_crit_damage_mult *= 1.0 + value*1.8

    def break_weapon(self, player, weapon):
        old_index=player.inventory.index(weapon) if weapon in player.inventory else 0
        if weapon in player.inventory:
            player.inventory.remove(weapon)
        if player.weapon is weapon:
            if player.inventory:
                player.selected_slot=min(old_index,len(player.inventory)-1)
                player.weapon=player.inventory[player.selected_slot]
            else:
                from types import SimpleNamespace
                fist=SimpleNamespace(name="Puños",class_="melee")
                fist.__dict__.update({"id":"fists","class":"melee","rarity":"common","damage":1.5,
                    "fire_interval":0.42,"auto":False,"magazine":999999,"reload_time":0,
                    "projectile_speed":0,"spread":0,"recoil":0,"damage_type":"physical",
                    "energy_cost":0,"pellets":1,"range":30,"pierce":0,"bounces":0,
                    "projectile_radius":1,"color":(205,180,150),"weapon_sprite":None,
                    "projectile_sprite":None,"melee_arc":1.8,"durability":999999})
                player.weapon=WeaponState(fist)
                player.inventory=[]
        self.emit("weapon_break",player.x,player.y)
        return True

    def _try_interact(self):
        """Compatibility facade for the extracted interaction system."""
        return try_interact(self)
    def _enter_next_dungeon(self):
        """Usa el portal de la sala final y encadena otra dungeon mas dificil."""
        self.room.items=self.items; self.room.pickups=self.pickups
        self.difficulty += 1
        seed=self.rng.randrange(1,2**31)
        self.dungeon=Dungeon(seed,"ruins",self.difficulty)
        self.portal=False; self.portal_position=(0,0)
        self.enemies=[]; self.items=[]; self.pickups=[]; self.hazards=[]; self.wave_attacks=[]; self.lasers=[]
        self.chest=None; self.shop_offers=[]
        self.player.x,self.player.y=self.dungeon.room.arena.player_spawn
        # Los buffs de estatua pertenecen a la partida completa, no a una dungeon individual.
        self.stats["dungeons"] = self.stats.get("dungeons",1)+1
        self.stats["rooms"] += 1; self.stats["xp"] += 10
        self._enter_room(self.dungeon.room,initial=True)
        self.emit("dungeon_enter",self.difficulty)

    def _try_transition(self):
        """Cruza automáticamente una puerta abierta al acercarse al umbral."""
        p=self.player
        for side,d in self.arena.doors.items():
            if not d.open:
                continue
            x,y=p.x,p.y
            near=(side=='N' and y<TILE*1.2) or (side=='S' and y>self.arena.height-TILE*1.2) or (side=='W' and x<TILE*1.2) or (side=='E' and x>self.arena.width-TILE*1.2)
            if near:
                # La sala conserva exactamente el loot/monedas que quedaron en su suelo.
                self.room.items=self.items
                self.room.pickups=self.pickups
            if near and self.dungeon.transition(side):
                # La transición se confirma primero en el grafo; _enter_room()
                # decide después si la sala destino debe cerrar sus puertas.
                new_arena=self.dungeon.room.arena
                opp={"N":"S","S":"N","W":"E","E":"W"}[side]
                d2=new_arena.doors.get(opp)
                if d2:
                    x2,y2=new_arena.tile_center(d2.x,d2.y); off=TILE*1.2
                    self.player.x,self.player.y=(x2,y2+off) if opp=="N" else (x2,y2-off) if opp=="S" else (x2+off,y2) if opp=="W" else (x2-off,y2)
                else:
                    self.player.x,self.player.y=new_arena.player_spawn
                self.stats["rooms"]+=1; self.stats["xp"] += 6
                self._enter_room(self.dungeon.room)
                return True
        return False
    def _entry_position(self,from_side):
        opp={'N':'S','S':'N','W':'E','E':'W'}[from_side]; d=self.arena.doors.get(opp)
        if not d:return self.arena.player_spawn
        x,y=self.arena.tile_center(d.x,d.y)
        off=TILE*1.2
        return (x,y+off) if opp=='N' else (x,y-off) if opp=='S' else (x+off,y) if opp=='W' else (x-off,y)
    def update(self,inp,dt):
        dt=min(dt,1/20)
        if self.over or self.statue_menu:return
        self.time+=dt; p=self.player
        if inp.switch_weapon_pressed:
            self.select_weapon_slot((getattr(p,"selected_slot",0)+1)%3)
        if inp.interact_pressed:self._try_interact()
        # Invariante de seguridad: una sala ya despejada nunca puede conservar
        # las puertas cerradas, incluso si un evento de jefe/estado ocurrió
        # entre dos frames. Esto evita quedar atrapado después de un jefe.
        if self.room.cleared and self.room.doors_locked:
            self.room.doors_locked=False
            self.arena.open_doors()
        tile=self.arena.tile_of(p.x,p.y); self._flow_refresh-=dt
        if tile!=self._flow_tile and self._flow_refresh<=0:
            self._flow_tile=tile; self._flow_refresh=0.12; self.flow=self.arena.flow_field(*tile)
        # Defensive AI needs only player projectiles. Build this list once per
        # frame instead of making every enemy scan the entire 600-slot pool.
        self._active_player_projectiles=[pr for pr in self.pool.items if pr.active and pr.team==0]
        p.update(self,inp,dt)
        for e in self.enemies:e.update(self,dt)
        self._update_lasers(dt)
        self._update_drones(dt)
        self._update_projectiles(dt); self._update_pickups(dt); self._update_hazards(dt); self._update_dot_effects(dt)
        dead=[e for e in self.enemies if not e.alive]
        for e in dead:
            self.stats["kills"]+=1; self.stats["xp"] += 3 + (20 if getattr(e,"is_boss",False) else 8 if getattr(e,"is_miniboss",False) else 0);
            if getattr(e,"is_boss",False) or getattr(e,"is_miniboss",False): self.stats["bosses_defeated"]+=1
            death_set = getattr(e.d, "sprite_set", None)
            death_size = max(48.0, float(getattr(e, "radius", 12)) * float(getattr(e.d, "sprite_scale", 2.5)) * 1.1)
            self.emit("enemy_die",e.x,e.y,e.d.color,death_set,death_size,getattr(e,"facing",0.0),getattr(e.d,"variant_id",None))
            # Los esbirros invocados sólo presionan al jugador: no dan monedas ni loot.
            # Los jefes siempre recompensan; los enemigos normales tienen una probabilidad
            # de botín que crece con su valor de monedas/dificultad, pero nunca es segura.
            if not getattr(e, "is_summoned", False):
                coin_value = max(1, int(getattr(e.d, "coins", 1)))
                is_boss = getattr(e, "is_boss", False) or getattr(e, "is_miniboss", False)
                drop_coins = is_boss or self.rng.random() < min(0.48, 0.08 + coin_value * 0.07)
                if drop_coins:
                    # Cada pickup de moneda vale exactamente 1. Los enemigos con
                    # mayor valor pueden soltar varias monedas físicas, nunca una
                    # moneda apilada con valor superior.
                    drop_count = coin_value if is_boss else 1
                    for _ in range(max(1, drop_count)):
                        cx, cy = self._safe_drop_position(e.x + self.rng.uniform(-10,10), e.y + self.rng.uniform(-10,10), 7.0)
                        self.pickups.append({"kind":"coin","x":cx,"y":cy,"amount":1,"phase":self.rng.random()*math.tau})
            # Los enemigos también pueden soltar munición. Los esbirros invocados
            # participan con una probabilidad menor, pero ya no quedan excluidos.
            ammo_chance = 0.075 if getattr(e, "is_summoned", False) else 0.11
            if getattr(e, "is_miniboss", False):
                ammo_chance = 0.16
            elif getattr(e, "is_boss", False):
                ammo_chance = 0.22
            if self.rng.random() < ammo_chance:
                ax, ay = self._safe_drop_position(e.x + self.rng.uniform(-10,10), e.y + self.rng.uniform(-10,10), 8.0)
                self.items.append(type("AmmoLoot",(),{"kind":"ammo","x":ax,"y":ay,"magazines":1})())

            if not getattr(e,"is_boss",False) and not getattr(e,"is_miniboss",False):
                self.enemy_pool.append(e)
        self.enemies=[e for e in self.enemies if e.alive]
        if not self.enemies and self.room.enemies_spawned and not self.room.cleared:self._complete_room()
        if not self.enemies and self._room_should_combat() and not self.room.enemies_spawned:
            self.wave_delay-=dt
            if self.wave_delay<=0:self._spawn_room_enemies(); self.room.enemies_spawned=True; self.wave_delay=99
        if not p.alive:self.over=True; self.emit("player_die",p.x,p.y)
        if not self.over:
            self._try_transition()
    def _damage_shield(self, enemy, damage, incoming_from_target, source="projectile"):
        return damage_shield(self, enemy, damage, incoming_from_target, source)

    def _apply_dot(self, target, kind, duration=4.0, base_damage=1.0):
        return apply_dot(self, target, kind, duration, base_damage)

    def _update_dot_effects(self, dt):
        return update_dot_effects(self, dt)

    @staticmethod
    def _freeze_duration(power):
        return freeze_duration(power)

    def _apply_freeze(self, target, power):
        return apply_freeze(self, target, power)

    def perform_fist_attack(self, p):
        return perform_fist_attack(self, p)
    def perform_melee_attack(self, p, d):
        return perform_melee_attack(self, p, d)
    def _update_projectiles(self, dt):
        return _update_projectiles(self, dt)
    def _explode_projectile(self, pr):
        return _explode_projectile(self, pr)
    def _hit_enemies(self, pr):
        return _hit_enemies(self, pr)
    def stop_player_laser(self, ):
        return stop_player_laser(self)
    def update_player_laser(self, charge_time, dt):
        return update_player_laser(self, charge_time, dt)
    def start_enemy_laser(self, owner, angle, duration=2.2, color=None, damage=14.0, width=2.0, max_width=12.0, range_=760.0, explosion_radius=24.0):
        return start_enemy_laser(self, owner, angle, duration, color, damage, width, max_width, range_, explosion_radius)
    def _laser_hit_target(self, pr, dt):
        return _laser_hit_target(self, pr, dt)
    def _update_lasers(self, dt):
        return _update_lasers(self, dt)
    def _update_hazards(self, dt):
        return update_hazards(self, dt)
    def _update_pickups(self, dt):
        """Compatibility facade for the extracted pickup system."""
        return update_pickups(self, dt)

