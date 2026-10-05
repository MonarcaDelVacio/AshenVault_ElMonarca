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

class Input:
    def __init__(self):
        self.move_x=self.move_y=0.; self.aim_x=self.aim_y=0.; self.fire_held=self.fire_pressed=self.fire_released=False
        self.reload_pressed=self.dash_pressed=self.interact_pressed=self.switch_weapon_pressed=self.ability_pressed=False
    def clear_edges(self):
        self.fire_pressed=self.fire_released=self.reload_pressed=self.dash_pressed=self.interact_pressed=self.switch_weapon_pressed=self.ability_pressed=False

class Sim:
    def __init__(self,data,char_id,arena_id="ruins_plaza",seed=None,meta_upgrades=None,character_progress=None,difficulty=1):
        self.data=data; self.seed=seed if seed is not None else random.SystemRandom().randrange(1,2**31); self.rng=random.Random(self.seed)
        self.difficulty=max(1,int(difficulty)); self.dungeon=Dungeon(self.seed,"ruins",self.difficulty); self.room=self.dungeon.room; self.arena=self.room.arena
        c=data.characters[char_id]; self.meta_upgrades=meta_upgrades or {}
        self.player=Player(c,data.weapons[c.start_weapon],self.arena.player_spawn,self.meta_upgrades,character_progress)
        self.player.inventory=[self.player.weapon]; self.player.items=[]; self.player.bonus_pierce=0; self.player.bonus_projectiles=0; self.player.attack_speed_mult=1.0; self.player.coin_radius=0
        self.pool=ProjectilePool(); self.enemies=[]; self.enemy_pool=[]; self.items=[]; self.pickups=[]; self.keys=0; self.events=[]; self.chest=None
        self.props=[]; self.hazards=[]; self.wave_attacks=[]
        self.time=0.; self.wave=0; self.wave_delay=0.5; self.over=False; self.victory=False; self.portal=False; self.portal_position=(self.arena.width/2,self.arena.height/2)
        self.stats={"kills":0,"shots":0,"damage_taken":0,"waves":0,"coins":0,"rooms":1,"items":0,"purchases":0,"abilities":0,"bosses_defeated":0,"xp":0}
        self._flow_tile=self.arena.tile_of(self.player.x,self.player.y); self._flow_refresh=0.; self.flow=self.arena.flow_field(*self._flow_tile)
        self.shop_offers=[]; self.revealed_secrets=set()
        self.statue_menu=None
        self.statue_buffs=[]
        self.statue_used=set()
        self._enter_room(self.room,initial=True)
    def emit(self,kind,*args):
        if len(self.events)<250:self.events.append((kind,)+args)
    def spawn_projectile(self,*a):return self.pool.spawn(*a)

    def _new_enemy(self, edef, x, y, summoned=False):
        scaled_def=copy.copy(edef)
        variants=getattr(self.data, "enemy_variants", {})
        chance=float(variants.get("chance", 0.0)) if isinstance(variants, dict) else 0.0
        if not summoned and self.wave >= int(variants.get("min_wave", 2)) and self.rng.random() < chance:
            families=variants.get("families", {}) if isinstance(variants, dict) else {}
            sprite_set=getattr(edef, "sprite_set", None)
            candidates=families.get(sprite_set) or families.get("*") or []
            if candidates:
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
        """Invoca esbirros en casillas transitables, nunca dentro de muros/cajas/actores."""
        pool = [self.data.enemies[i] for i in ids if i in self.data.enemies]
        if not pool:
            return False
        spawned = 0
        for _ in range(max(1, int(count))):
            if self.count_summoned() >= 7:
                break
            d = self.rng.choice(pool)
            min_sep = source.radius + d.radius + 7
            candidates = []
            for ty in range(1, self.arena.rows - 1):
                for tx in range(1, self.arena.cols - 1):
                    x, y = self.arena.tile_center(tx, ty)
                    dist = math.hypot(x - source.x, y - source.y)
                    if dist < min_sep or dist > TILE * 5.5:
                        continue
                    if self.arena.box_hits(x, y, d.radius * .85) or self._crate_collision(x, y, d.radius * .85):
                        continue
                    if any(other.alive and math.hypot(x - other.x, y - other.y) < d.radius + other.radius + 5
                           for other in self.enemies):
                        continue
                    candidates.append((dist + self.rng.random() * 7, x, y))
            if not candidates:
                # Si la zona inmediata está bloqueada, se busca en cualquier punto libre de la sala.
                for ty in range(1, self.arena.rows - 1):
                    for tx in range(1, self.arena.cols - 1):
                        x, y = self.arena.tile_center(tx, ty)
                        if self.arena.box_hits(x, y, d.radius * .85) or self._crate_collision(x, y, d.radius * .85):
                            continue
                        if any(other.alive and math.hypot(x - other.x, y - other.y) < d.radius + other.radius + 5
                               for other in self.enemies):
                            continue
                        candidates.append((math.hypot(x - source.x, y - source.y) + self.rng.random() * 7, x, y))
            if not candidates:
                continue
            _, x, y = min(candidates, key=lambda item: item[0])
            e = self._new_enemy(d, x, y, summoned=True)
            e.spawn_delay = 0.8
            self.enemies.append(e)
            spawned += 1
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
        self.hazards=[]; self.wave_attacks=[]; self.lasers=[]
        if not getattr(room, "props_spawned", False):
            self._spawn_room_props(room); room.props_spawned=True
        self.props=getattr(room, "props", [])
        self._flow_tile=self.arena.tile_of(self.player.x,self.player.y); self._flow_refresh=0.; self.flow=self.arena.flow_field(*self._flow_tile)
        if room.room_type=="boss" and not room.cleared:
            self.chest=None
            self.arena.close_doors(); self._spawn_boss(); room.enemies_spawned=True; room.doors_locked=True
        elif self._room_should_combat() and not room.cleared:
            self.chest=None
            self.arena.close_doors();
            if room.room_type=="miniboss": self._spawn_miniboss()
            else: self._spawn_room_enemies()
            room.enemies_spawned=True; room.doors_locked=True
        else:
            self.arena.open_doors()
            self.chest=None
            if not room.special_resolved and not initial: self._resolve_special_room(room)
        if room.room_type == "shop":
            self._setup_shop()
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
        """Comprueba colisión AABB del actor contra cajas intactas de una casilla."""
        half=TILE*0.5
        for prop in self.props:
            if prop.get("broken") or prop.get("kind")!="crate":
                continue
            if abs(x-prop["x"]) < half+radius and abs(y-prop["y"]) < half+radius:
                return True
        return False

    def _decoration_collision(self, x, y, radius):
        """Colisión basada en la silueta visible cuando el renderer la conoce.

        El proveedor visual usa el alpha real del PNG; la simulación conserva el
        radio clásico como fallback para tests/headless.
        """
        provider=getattr(self, "decoration_collider_provider", None)
        if provider is not None:
            for deco in getattr(self.arena, "decorations", []):
                shape=provider(deco)
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
        """Los cofres de recompensa ocupan exactamente un bloque físico."""
        chest=self.chest
        if chest is None:
            return False
        half=TILE*0.5
        return abs(x-float(chest.x)) < half+radius and abs(y-float(chest.y)) < half+radius

    def _world_collision(self, x, y, radius):
        # El cofre no es un obstáculo físico: la interacción se controla por distancia.
        # Así, si el jugador queda encima del cofre justo cuando muere el último
        # enemigo, nunca puede quedar atrapado dentro de su hitbox.
        return (self._decoration_collision(x,y,radius) or
                self._crate_collision(x,y,radius))

    def move_actor(self, x, y, dx, dy, radius):
        """Movimiento contra paredes y objetos físicos de una casilla, permitiendo deslizarse por sus lados."""
        nx,ny=self.arena.move(x,y,dx,dy,radius)
        if not self._world_collision(nx,ny,radius):
            return nx,ny
        xx,xy=self.arena.move(x,y,dx,0,radius)
        if self._world_collision(xx,xy,radius):
            xx,xy=x,y
        yx,yy=self.arena.move(xx,xy,0,dy,radius)
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
            # Las esferas amarillas fueron retiradas.
        else:
            dtype={"fire":"fire","poison":"poison","electric":"electric"}[kind]
            color={"fire":(245,70,45),"poison":(70,220,85),"electric":(175,70,255)}[dtype]
            self.hazards.append({"x":x,"y":y,"radius":TILE*2.5,"life":9.0,"max_life":9.0,"tick":0.0,"particle_timer":0.0,"particles":[],"dtype":dtype,"color":color,"damage":1.0})
            self.emit("barrel_burst",x,y,dtype)

    def _damage_props(self, x, y, damage, explosive=False, color=None):
        for prop in self.props:
            if prop.get("broken"): continue
            if math.hypot(x-prop["x"],y-prop["y"]) <= prop.get("radius",24)+5:
                if explosive:
                    self._break_prop(prop,color)
                else:
                    prop["hp"]-=max(1,damage/8.0)
                    if prop["hp"]<=0: self._break_prop(prop,color)
                return True
        return False

    def _resolve_special_room(self,room):
        room.special_resolved=True
        cx,cy=self.arena.width/2,self.arena.height/2
        if room.room_type=="treasure":
            self._spawn_chest("common")
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
        x,y=self.arena.tile_center(self.arena.cols//2,self.arena.rows//3)
        mini_def=copy.copy(e); mini_def.hp*=2.45; mini_def.damage*=1.25; mini_def.speed*=.94
        mini_def.radius*=1.16; mini_def.sprite_scale=float(getattr(e,"sprite_scale",3.5))*1.12
        mini_def.miniboss_pulse_interval=4.2
        mini=Enemy(mini_def,x,y,self.rng); mini.is_miniboss=True
        scale=1.0 + 0.14*(self.difficulty-1); mini.hp*=scale; mini.max_hp=mini.hp; mini.d.damage*=scale
        self.enemies.append(mini); self.emit("miniboss_spawn",x,y,e.name)
    def _spawn_room_enemies(self):
        self.wave+=1; self.stats["waves"]=max(self.stats["waves"],self.wave)
        budget=self.data.rooms.get(self.room.room_type,{}).get("enemy_budget",5) or 5
        budget=min(12,budget+min(self.wave,3))
        biome_pool=self.data.biomes.get(self.arena.biome,{}).get("enemy_pool",[])
        pool=[self.data.enemies[eid] for eid in biome_pool if eid in self.data.enemies and self.data.enemies[eid].min_wave<=self.wave]
        if not pool: pool=[e for e in self.data.enemies.values() if e.min_wave<=self.wave]
        spots=list(self.arena.enemy_spawns) or [self.arena.player_spawn]; self.rng.shuffle(spots); weights=[e.weight for e in pool]
        for i in range(min(budget,len(spots))):
            e=self.rng.choices(pool,weights)[0]; sx,sy=spots[i]; self.enemies.append(self._new_enemy(e,sx,sy)); self.emit("spawn",sx,sy)
    def _setup_shop(self):
        self.shop_offers=[]
        cx,cy=self.arena.width/2,self.arena.height/2
        weapon_ids=list(self.data.weapons)
        self.rng.shuffle(weapon_ids)
        prices=self.data.shops.get("weapon_prices", {})
        # Tres ofertas reales e independientes: dos armas + un consumible.
        # El jugador puede comprar las tres durante la misma visita si tiene monedas.
        for idx,wid in enumerate(weapon_ids[:2]):
            w=self.data.weapons[wid]
            price=prices.get(w.rarity,20)
            self.shop_offers.append(type("ShopOffer",(),{"kind":"weapon","id":wid,"name":w.name,"price":price,"x":cx-72+idx*144,"y":cy-35,"sold":False})())
        # La tercera oferta es siempre un objeto real de data/items.json.
        # Antes se mezclaban consumibles auxiliares de shops.json con los objetos
        # permanentes del juego, lo que producía iconos inexistentes y compras que
        # podían quedar bloqueadas si el recurso correspondiente estaba lleno.
        item_ids=list(self.data.items)
        self.rng.shuffle(item_ids)
        if item_ids:
            ident=item_ids[0]
            item_def=self.data.items[ident]
            effects=item_def.get("effects", {}) if isinstance(item_def, dict) else getattr(item_def, "effects", {})
            name=item_def.get("name", ident) if isinstance(item_def, dict) else getattr(item_def, "name", ident)
            price=18 + 4 * len(effects)
            self.shop_offers.append(type("ShopOffer",(),{"kind":"item","id":ident,"name":name,"price":price,"amount":1,"x":cx,"y":cy+55,"sold":False})())
    def _buy_shop_offer(self, offer):
        p=self.player
        if offer.sold or p.coins < offer.price: return False
        if offer.kind == "weapon":
            # Las armas compradas respetan el límite de tres; el intercambio se
            # reserva para armas que están físicamente en el suelo.
            if len(p.inventory) >= 3 or any(w.d.id == offer.id for w in p.inventory): return False
            p.inventory.append(WeaponState(self.data.weapons[offer.id]))
        elif offer.kind == "heal":
            if p.hp >= p.max_hp: return False
            p.hp=min(p.max_hp,p.hp+offer.amount)
            p.set_status("heal", 1.8)
        elif offer.kind == "shield":
            if p.shield >= p.max_shield: return False
            p.shield=min(p.max_shield,p.shield+offer.amount)
            p.set_status("shield", 2.2)
        elif offer.kind == "energy":
            if p.energy >= p.max_energy: return False
            old_energy=p.energy; p.energy=min(p.max_energy,p.energy+offer.amount)
            if p.energy>old_energy:
                p.feedback_flash("energy",.26); self.emit("energy_pickup",offer.x,offer.y,p.energy-old_energy)
        elif offer.kind == "item":
            item_def=self.data.items.get(offer.id)
            if item_def is None: return False
            apply_item_bonuses(p, item_def, self.data.synergies)
        else: return False
        p.coins -= offer.price; self.stats["purchases"] += 1; offer.sold=True
        self.emit("shop_purchase",offer.x,offer.y,offer.id); return True

    def _spawn_boss(self):
        biome=self.arena.biome
        boss_id=self.data.biome_bosses.get(biome) if hasattr(self.data,"biome_bosses") else None
        b=self.data.bosses.get(boss_id) if boss_id else None
        b=b or next(iter(self.data.bosses.values()))
        x,y=self.arena.tile_center(self.arena.cols//2,self.arena.rows//3)
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
            if self.arena.box_hits(sx,sy,edef.radius*.9) or self._crate_collision(sx,sy,edef.radius*.9): continue
            if any(o.alive and math.hypot(sx-o.x,sy-o.y)<edef.radius+o.radius+8 for o in self.enemies): continue
            guard=self._new_enemy(edef,sx,sy); guard.is_boss_guard=True; guard.spawn_delay=.45
            self.enemies.append(guard); self.emit("boss_guard_spawn",sx,sy,edef.name); spawned+=1
    def _complete_room(self):
        if self.room.cleared:return
        self.room.cleared=True; self.room.doors_locked=False; self.arena.open_doors(); self.emit("room_clear",self.room.id)
        chest_type = self._chest_type_for_room(self.room.room_type)
        if chest_type:
            self._spawn_chest(chest_type)
            if self.chest is not None:
                if math.hypot(self.chest.x-self.player.x,self.chest.y-self.player.y) < TILE*1.35:
                    for ox,oy in ((TILE*2,0),(-TILE*2,0),(0,TILE*2),(0,-TILE*2)):
                        qx,qy=self._safe_drop_position(self.chest.x+ox,self.chest.y+oy,14.0)
                        if math.hypot(qx-self.player.x,qy-self.player.y) >= TILE*1.35:
                            self.chest.x,self.chest.y=qx,qy; break
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
        cx, cy = self.arena.width / 2, self.arena.height / 2
        if self.chest is not None:
            return
        self.chest = Chest(chest_type, cx, cy)
        self.emit("chest_spawn", cx, cy, chest_type)

    def _open_chest(self):
        if self.chest is None or self.chest.is_open:
            return False
        if not self.chest.open():
            return False
        self.emit("chest_open", self.chest.x, self.chest.y, self.chest.chest_type)
        # Los cofres de sala despejada entregan un arma y monedas. El antiguo
        # objeto genérico (dibujado como un orbe amarillo) ya no se usa aquí.
        choices=[w for w in self.data.weapons if w not in {x.d.id for x in self.player.inventory}]
        if choices:
            wid=self.rng.choice(choices)
            wx,wy=self._safe_drop_position(self.chest.x+42,self.chest.y,10.0)
            it=type("WeaponPickup",(),{"id":wid,"name":self.data.weapons[wid].name,"kind":"weapon","weapon_id":wid,"x":wx,"y":wy})()
            self.items.append(it); self.stats["items"]+=1; self.emit("weapon_drop",it.x,it.y,wid)
        self.emit("chest_coins",self.chest.x,self.chest.y,0)
        return True

    def _drop_room_reward(self,guaranteed=False,quality=0,position=None):
        cx,cy=position if position is not None else (self.arena.width/2,self.arena.height/2)
        cx,cy=self._safe_drop_position(cx,cy,10.0)
        chance=1.0 if guaranteed else .65
        if self.rng.random()<chance:
            ids=list(self.data.items)
            if quality>=2: ids=[i for i in ids if i not in ("magnetic","swift")] or ids
            ident=self.rng.choice(ids); it=make_item(self.data.items,ident); it.x,it.y=cx,cy; self.items.append(it); self.stats["items"]+=1; self.emit("item_drop",cx,cy,ident)
        if guaranteed or self.rng.random()<.35:self.keys+=1; self.emit("key_drop",cx,cy)
        if guaranteed or self.rng.random()<.30:
            choices=[w for w in self.data.weapons if w not in {x.d.id for x in self.player.inventory}]
            if choices:
                wid=self.rng.choice(choices); wx,wy=self._safe_drop_position(cx+42,cy,10.0); it=type('WeaponPickup',(object,),{'id':wid,'name':self.data.weapons[wid].name,'kind':'weapon','weapon_id':wid,'x':wx,'y':wy})(); self.items.append(it); self.emit('weapon_drop',it.x,it.y,wid)
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

    def _try_interact(self):
        p=self.player
        if self.portal:
            px,py=self.portal_position
            if math.hypot(px-p.x,py-p.y) < 78:
                self._enter_next_dungeon()
                return True
        if self._open_statue_menu():
            return True
        if self.chest is not None and not self.chest.is_open:
            if math.hypot(self.chest.x-p.x, self.chest.y-p.y) < 72:
                if self._open_chest(): return
        if self.room.room_type == "shop":
            for offer in self.shop_offers:
                if math.hypot(offer.x-p.x,offer.y-p.y)<55 and self._buy_shop_offer(offer): return
        # pickup nearest item/key represented in the pure simulation list
        for item in list(self.items):
            if hasattr(item,'x'): ix,iy=item.x,item.y
            else: ix,iy=self.arena.width/2,self.arena.height/2
            if math.hypot(ix-p.x,iy-p.y)<48:
                if getattr(item,'kind','item')=='weapon':
                    weapon_id = item.weapon_id
                    if len(p.inventory) < 3:
                        new_weapon = WeaponState(self.data.weapons[weapon_id])
                        p.inventory.append(new_weapon)
                        p.weapon = new_weapon
                        self.items.remove(item)
                    else:
                        # Con el inventario lleno se cambia el arma seleccionada
                        # por la del suelo y se deja caer la anterior en ese lugar.
                        selected_index = p.inventory.index(p.weapon)
                        old_weapon = p.inventory[selected_index]
                        p.inventory[selected_index] = WeaponState(self.data.weapons[weapon_id])
                        p.weapon = p.inventory[selected_index]
                        item.weapon_id = old_weapon.d.id
                        item.id = old_weapon.d.id
                        item.name = old_weapon.d.name
                        item.x, item.y = self._safe_drop_position(ix + 28, iy, 10.0)
                    self.emit('weapon_pickup',p.x,p.y,weapon_id); return
                if getattr(item,'kind',None)=='heal':
                    old_hp=p.hp; p.hp=min(p.max_hp,p.hp+2)
                    if p.hp>old_hp: p.set_status("heal",1.8); p.feedback_flash("heal",.26); self.emit('heal_pickup',p.x,p.y,p.hp-old_hp)
                    self.items.remove(item); self.emit('item_pickup',p.x,p.y,'heal'); return
                if getattr(item,'kind',None)=='energy':
                    old_energy=p.energy; p.energy=min(p.max_energy,p.energy+30)
                    if p.energy>old_energy: p.feedback_flash("energy",.26); self.emit('energy_pickup',p.x,p.y,p.energy-old_energy)
                    self.items.remove(item); self.emit('item_pickup',p.x,p.y,'energy'); return
                apply_item_bonuses(p,item); self.items.remove(item); self.emit('item_pickup',p.x,p.y,item.id); return
    def _enter_next_dungeon(self):
        """Usa el portal de la sala final y encadena otra dungeon mas dificil."""
        self.room.items=self.items; self.room.pickups=self.pickups
        self.difficulty += 1
        seed=self.rng.randrange(1,2**31)
        self.dungeon=Dungeon(seed,"ruins",self.difficulty)
        self.portal=False; self.portal_position=(0,0)
        self.enemies=[]; self.items=[]; self.pickups=[]; self.hazards=[]; self.wave_attacks=[]
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
        if inp.switch_weapon_pressed and len(p.inventory)>1:
            idx=p.inventory.index(p.weapon); p.weapon=p.inventory[(idx+1)%len(p.inventory)]; self.emit("weapon_switch",p.x,p.y)
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
        p.update(self,inp,dt)
        for e in self.enemies:e.update(self,dt)
        self._update_lasers(dt)
        self._update_drones(dt)
        self._update_projectiles(dt); self._update_pickups(dt); self._update_hazards(dt)
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
                    amount = coin_value if is_boss else self.rng.randint(1, coin_value)
                    cx, cy = self._safe_drop_position(e.x + self.rng.uniform(-10,10), e.y + self.rng.uniform(-10,10), 7.0)
                    self.pickups.append({"kind":"coin","x":cx,"y":cy,"amount":amount,"phase":self.rng.random()*math.tau})
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
        """Devuelve True si el escudo frontal absorbe el golpe; su integridad se agota."""
        if not getattr(enemy.d, "shielded", False) or getattr(enemy, "shield_integrity", 0) <= 0:
            return False
        da = (incoming_from_target - enemy.facing + math.pi) % (2 * math.pi) - math.pi
        if abs(da) >= getattr(enemy.d, "shield_arc", 2.1) * 0.5:
            return False
        drain = max(2.0, float(damage) * 0.5)
        enemy.shield_integrity = max(0.0, enemy.shield_integrity - drain)
        if enemy.shield_integrity <= 0:
            self.emit("shield_break", enemy.x, enemy.y, getattr(enemy.d, "color", (120, 190, 255)))
        else:
            self.emit("projectile_block", enemy.x, enemy.y, (120, 190, 255))
        return True

    @staticmethod
    def _freeze_duration(power):
        # La potencia del impacto determina la duracion: armas mas fuertes
        # congelan durante mas tiempo, con limites para evitar bloqueos extremos.
        return max(0.45, min(3.5, 0.45 + float(power) / 18.0))

    def _apply_freeze(self, target, power):
        duration = self._freeze_duration(power)
        if getattr(target, "is_boss", False):
            duration = min(duration, 1.2)
        elif getattr(target, "is_miniboss", False):
            duration = min(duration, 1.7)
        if hasattr(target, "frozen"):
            target.frozen = max(float(getattr(target, "frozen", 0.0)), duration)
        self.emit("freeze", target.x, target.y, duration)

    def perform_melee_attack(self, p, d):
        # El hitbox cubre toda la zona visible del corte, con margen de seguridad.
        reach=max(float(d.range)+p.radius, float(d.range)*1.20+p.radius)
        arc=max(float(getattr(d,"melee_arc",1.2)), 1.80)
        hit=0
        for e in self.enemies:
            if not e.alive: continue
            dx,dy=e.x-p.x,e.y-p.y; dist=math.hypot(dx,dy)
            if dist <= reach:
                da=math.atan2(dy,dx)-p.aim
                da=(da+math.pi)%(2*math.pi)-math.pi
                if abs(da) <= arc*0.5:
                    raw_damage = d.damage * p.damage_mult * getattr(p, "statue_melee_mult", 1.0)
                    is_boss = getattr(e, "is_boss", False) or getattr(e, "is_miniboss", False)
                    damage_cap = e.max_hp * (0.55 if not is_boss else 0.18)
                    damage = min(raw_damage, max(1.0, damage_cap))
                    if self._damage_shield(e, damage, math.atan2(p.y - e.y, p.x - e.x), "melee"):
                        hit += 1
                        continue
                    e.hurt(damage, p.aim)
                    level = max(1, int(getattr(d, "melee_level", 1)))
                    knockback = 105.0 + level * 24.0
                    e.kx += math.cos(p.aim) * knockback
                    e.ky += math.sin(p.aim) * knockback
                    status_type = getattr(d, "damage_type", "physical")
                    status_chance = float(getattr(d, "status_chance", 0.24 if status_type in ("ice","fire","poison","electric") else 0.0))
                    if status_type == "ice" and self.rng.random() < status_chance:
                        self._apply_freeze(e, damage)
                    elif status_type in ("fire","poison","electric") and self.rng.random() < status_chance:
                        self.emit("enemy_status",e.x,e.y,status_type,2.4)
                    hit += 1
                    self.emit("enemy_hit",e.x,e.y,d.color,damage,False)
        for prop in self.props:
            if prop.get("broken"): continue
            dx,dy=prop["x"]-p.x,prop["y"]-p.y; dist=math.hypot(dx,dy)
            if dist <= reach+prop.get("radius",24):
                da=(math.atan2(dy,dx)-p.aim+math.pi)%(2*math.pi)-math.pi
                if abs(da)<=arc*0.6:
                    prop["hp"]-=max(1.0,d.damage/8.0)
                    if prop["hp"]<=0: self._break_prop(prop,d.color)
        if hit: self.emit("melee_hit",p.x,p.y,hit)

    def _update_drones(self,dt):
        p=self.player
        if not getattr(p,"drones",0) or p.ability_shot_timer>0: return
        targets=[e for e in self.enemies if e.alive]
        if not targets: return
        target=min(targets,key=lambda e: math.hypot(e.x-p.x,e.y-p.y))
        ang=math.atan2(target.y-p.y,target.x-p.x)
        for i in range(p.drones):
            self.spawn_projectile(0,p.x+math.cos(ang)*18,p.y+math.sin(ang)*18,ang,360,4*p.damage_mult,3,1.2,(100,220,255),"energy",0,0,False)
        p.ability_shot_timer=0.7

    def _update_projectiles(self,dt):
        arena,p=self.arena,self.player
        for pr in self.pool.items:
            if not pr.active:continue
            pr.age += dt
            if pr.homing > 0 and pr.team == 1 and p.alive:
                dx, dy = p.x - pr.x, p.y - pr.y
                desired = math.atan2(dy, dx)
                current = math.atan2(pr.vy, pr.vx)
                delta = (desired - current + math.pi) % (2 * math.pi) - math.pi
                max_turn = pr.homing * dt
                delta = max(-max_turn, min(max_turn, delta))
                new_angle = current + delta
                speed = math.hypot(pr.vx, pr.vy) or 1.0
                pr.vx, pr.vy = math.cos(new_angle) * speed, math.sin(new_angle) * speed
            if pr.stuck:
                pr.stuck_timer -= dt
                if pr.stuck_enemy_id is not None:
                    target = next((e for e in self.enemies if e.id == pr.stuck_enemy_id and e.alive), None)
                    if target is not None:
                        pr.x = target.x + pr.stuck_offset_x
                        pr.y = target.y + pr.stuck_offset_y
                if pr.stuck_timer <= 0:
                    pr.active = False
                continue
            pr.life-=dt
            if pr.life<=0:pr.active=False;continue
            dist=math.hypot(pr.vx,pr.vy)*dt; steps=max(1,int(dist//6)+1); sx,sy=pr.vx*dt/steps,pr.vy*dt/steps
            for _ in range(steps):
                nx,ny=pr.x+sx,pr.y+sy
                if arena.point_solid(nx,ny):
                    if pr.bounces>0:
                        pr.bounces-=1
                        if arena.point_solid(pr.x+sx,pr.y):pr.vx,sx=-pr.vx,-sx
                        if arena.point_solid(pr.x,pr.y+sy):pr.vy,sy=-pr.vy,-sy
                        self.emit("bounce",pr.x,pr.y,pr.color);continue
                    if pr.explosive:
                        self._explode_projectile(pr)
                    elif pr.stick_on_hit:
                        pr.x, pr.y = nx, ny
                        pr.stuck = True; pr.stuck_timer = 3.0
                        pr.stuck_angle = math.atan2(pr.vy, pr.vx)
                        pr.vx = pr.vy = 0.0
                    else:
                        pr.active=False
                    self.emit("wall_hit",pr.x,pr.y,pr.color);break
                pr.x,pr.y=nx,ny
                hit_prop=self._damage_props(pr.x,pr.y,pr.damage,pr.explosive,pr.color)
                if hit_prop:
                    if pr.explosive: self._explode_projectile(pr)
                    else: pr.active=False
                    break
                # Las decoraciones del escenario tienen hitbox físico; un proyectil
                # no puede atravesar una roca, banco, fuente, estatua u hoguera.
                if self._decoration_collision(pr.x,pr.y,pr.radius):
                    if pr.explosive: self._explode_projectile(pr)
                    else: pr.active=False
                    self.emit("decoration_hit",pr.x,pr.y,pr.color)
                    break
                if pr.team==0:
                    if self._hit_enemies(pr):break
                else:
                    w=p.weapon.d
                    # Un arma cuerpo a cuerpo solo puede interceptar un proyectil
                    # durante la ventana activa del golpe. Apuntar no tiene efecto.
                    if getattr(w,"class","") == "melee" and p.melee_attack_timer > 0:
                        dist=math.hypot(pr.x-p.x,pr.y-p.y)
                        da=math.atan2(pr.y-p.y,pr.x-p.x)-p.aim
                        da=(da+math.pi)%(2*math.pi)-math.pi
                        hit_radius=w.range
                        if dist <= hit_radius + pr.radius and abs(da) <= getattr(w,"melee_arc",1.2)*0.5:
                            pr.active=False; self.emit("projectile_block",pr.x,pr.y,w.color); continue
                    if math.hypot(pr.x-p.x,pr.y-p.y)<pr.radius+p.radius-2:
                        if pr.explosive:
                            self._explode_projectile(pr)
                        elif p.take_damage(pr.damage):
                            self.on_player_hit(pr.x-pr.vx,pr.y-pr.vy,pr.damage)
                            if pr.dtype == "ice":
                                self._apply_freeze(p, pr.damage)
                                p.set_status("freeze", 1.6)
                            elif pr.dtype in ("fire", "poison", "electric"):
                                p.set_status({"fire":"burn","poison":"poison","electric":"electric"}[pr.dtype], 2.4)
                            pr.active=False
                        break
    def _explode_projectile(self, pr):
        """Detona un proyectil explosivo y aplica daño en un radio corto (aprox. 3x3 casillas)."""
        radius = max(TILE, getattr(pr, "explosion_radius", 0) or TILE * 1.5)
        for prop in self.props:
            if not prop.get("broken") and math.hypot(prop["x"]-pr.x,prop["y"]-pr.y)<=radius+prop.get("radius",24): self._break_prop(prop,pr.color)
        if pr.team == 1 and math.hypot(self.player.x-pr.x,self.player.y-pr.y) <= radius+self.player.radius:
            if self.player.take_damage(pr.damage):
                self.on_player_hit(pr.x,pr.y,pr.damage)
                if pr.dtype == "ice":
                    self._apply_freeze(self.player, pr.damage)
        for enemy in self.enemies:
            if not enemy.alive or enemy.spawn_delay > .3:
                continue
            if math.hypot(enemy.x - pr.x, enemy.y - pr.y) <= radius + enemy.radius:
                from_explosion = math.atan2(pr.y - enemy.y, pr.x - enemy.x)
                if self._damage_shield(enemy, pr.damage, from_explosion, "projectile"):
                    continue
                enemy.hurt(pr.damage, math.atan2(enemy.y - pr.y, enemy.x - pr.x))
                if pr.team == 0 and pr.status_chance > 0.0 and self.rng.random() < pr.status_chance and pr.dtype == "ice":
                    self._apply_freeze(enemy, pr.damage)
                self.emit("enemy_hit", enemy.x, enemy.y, pr.color, pr.damage, pr.crit)
        self.emit("explosion", pr.x, pr.y, radius, pr.color)
        pr.active = False

    def _hit_enemies(self,pr):
        for e in self.enemies:
            if not e.alive or e.id in pr.hit_ids or e.spawn_delay>.3:continue
            if math.hypot(pr.x-e.x,pr.y-e.y)<pr.radius+e.radius:
                if getattr(e,"shield_active",False):
                    self.emit("projectile_block",e.x,e.y,(120,190,255)); pr.active=False; return True
                incoming=math.atan2(pr.vy,pr.vx)
                from_projectile=(incoming+math.pi)%(2*math.pi)
                if self._damage_shield(e, pr.damage, from_projectile, "projectile"):
                    pr.active=False
                    return True
                if pr.explosive:
                    self._explode_projectile(pr)
                    return True
                e.hurt(pr.damage,math.atan2(pr.vy,pr.vx))
                if pr.status_chance > 0.0 and self.rng.random() < pr.status_chance:
                    if pr.dtype == "ice":
                        self._apply_freeze(e, pr.damage)
                    elif pr.dtype in ("fire","poison","electric"):
                        self.emit("enemy_status",e.x,e.y,pr.dtype,2.4)
                self.emit("enemy_hit",pr.x,pr.y,pr.color,pr.damage,pr.crit);pr.hit_ids.add(e.id)
                if pr.stick_on_hit:
                    pr.stuck = True; pr.stuck_timer = 3.0; pr.stuck_angle = math.atan2(pr.vy, pr.vx)
                    pr.stuck_enemy_id = e.id; pr.stuck_offset_x = pr.x - e.x; pr.stuck_offset_y = pr.y - e.y
                    pr.vx = pr.vy = 0.0
                    return True
                if pr.pierce>0:pr.pierce-=1;return False
                pr.active=False;return True
        return False
    def stop_player_laser(self):
        self.lasers=[l for l in self.lasers if l.get("owner") is not self.player]
        self.player.weapon.laser_active=False

    def update_player_laser(self, charge_time, dt):
        w=self.player.weapon
        d=w.d
        # Energy is drained only while the visible beam is active.
        drain=float(getattr(d,"laser_energy_per_second",18.0))*dt
        self.player.energy=max(0.0,self.player.energy-drain)
        self.player.since_shot=0.0
        if self.player.energy <= 0.0:
            w.laser_active=False
            self.stop_player_laser()
            return
        existing=next((l for l in self.lasers if l.get("owner") is self.player),None)
        if existing is None:
            existing={"owner":self.player,"team":0,"angle":self.player.aim,"charge":charge_time,
                      "duration":0.0,"tick":0.0,"color":tuple(getattr(d,"color",(120,220,255))),
                      "damage":float(getattr(d,"laser_damage",13.5))*self.player.damage_mult,
                      "width":float(getattr(d,"laser_width",2.0)),"max_width":float(getattr(d,"laser_max_width",14.0)),
                      "range":float(getattr(d,"laser_range",760.0)),"explosion_radius":float(getattr(d,"laser_explosion_radius",26.0))}
            self.lasers.append(existing)
        existing["angle"]=self.player.aim; existing["charge"]=min(3.0,float(charge_time)); existing["duration"]=0.0

    def start_enemy_laser(self, owner, angle, duration=2.2, color=None, damage=14.0, width=2.0, max_width=12.0, range_=760.0, explosion_radius=24.0):
        self.lasers.append({"owner":owner,"team":1,"angle":angle,"charge":1.0,"duration":float(duration),"tick":0.0,
                            "color":tuple(color or getattr(owner.d,"color",(255,100,100))),"damage":float(damage),
                            "width":float(width),"max_width":float(max_width),"range":float(range_),
                            "explosion_radius":float(explosion_radius)})
        self.emit("laser_start",owner.x,owner.y,angle,tuple(color or getattr(owner.d,"color",(255,100,100))))

    def _laser_hit_target(self, laser, dt):
        owner=laser["owner"]; angle=laser["angle"]; ux,uy=math.cos(angle),math.sin(angle)
        max_range=laser["range"]; width=laser["width"]
        # The beam stops at the first solid/prop/decoration or actor in its path.
        length=max_range; hit_enemy=None; hit_point=None
        steps=max(1,int(max_range/6))
        for i in range(1,steps+1):
            d=i*max_range/steps; x=owner.x+ux*d; y=owner.y+uy*d
            if self.arena.point_solid(x,y) or self._crate_collision(x,y,width) or self._decoration_collision(x,y,width):
                length=d; hit_point=(x,y); break
            if laser["team"]==0:
                candidates=[e for e in self.enemies if e.alive and e.spawn_delay<=0]
            else:
                candidates=[self.player] if self.player.alive else []
            for target in candidates:
                if target is owner: continue
                if math.hypot(target.x-x,target.y-y) <= target.radius+width*0.75:
                    length=d; hit_enemy=target; hit_point=(x,y); break
            if hit_enemy is not None: break
        if hit_point is None:
            hit_point=(owner.x+ux*length,owner.y+uy*length)
        if hit_enemy is not None and laser["tick"]<=0:
            if laser["team"]==0:
                damage=min(laser["damage"],hit_enemy.max_hp*(0.24 if getattr(hit_enemy,"is_boss",False) else 0.55))
                if not self._damage_shield(hit_enemy,damage,math.atan2(owner.y-hit_enemy.y,owner.x-hit_enemy.x),"laser"):
                    hit_enemy.hurt(damage,angle)
                    self.emit("enemy_hit",hit_enemy.x,hit_enemy.y,laser["color"],damage,False)
            else:
                if self.player.take_damage(laser["damage"]): self.on_player_hit(owner.x,owner.y,laser["damage"])
            self.emit("laser_impact",hit_point[0],hit_point[1],laser["color"],laser["explosion_radius"])
            laser["tick"]=0.12
        return length,hit_point,hit_enemy

    def _update_lasers(self,dt):
        active=[]
        for laser in self.lasers:
            owner=laser.get("owner")
            if owner is None or not getattr(owner,"alive",False): continue
            if laser.get("team")==0:
                if not getattr(owner.weapon,"laser_active",False): continue
                laser["angle"]=owner.aim
                laser["charge"]=min(3.0,float(owner.weapon.charge_time))
            else:
                laser["duration"]-=dt
                laser["angle"]=getattr(owner,"facing",laser.get("angle",0.0))
                if laser["duration"]<=0: continue
            laser["tick"]=max(0.0,laser.get("tick",0.0)-dt)
            charge=max(1.0,min(3.0,float(laser.get("charge",1.0))))
            laser["width"]=laser.get("width",2.0)+(charge-1.0)/(2.0)*max(0.0,laser.get("max_width",12.0)-laser.get("width",2.0))
            self._laser_hit_target(laser,dt)
            active.append(laser)
        self.lasers=active

    def _update_hazards(self,dt):
        for prop in self.props:
            if prop.get("broken") and prop.get("fade",0)>0: prop["fade"]-=dt
        self.props=[p for p in self.props if not p.get("broken") or p.get("fade",0)>0]
        for h in self.hazards:
            h["life"]-=dt; h["tick"]-=dt; h["particle_timer"]-=dt
            if h["particle_timer"]<=0 and h["life"]>0.25:
                h["particle_timer"]=0.09 if h["dtype"]=="electric" else 0.12
                angle=self.rng.random()*math.tau
                radius=h["radius"]*math.sqrt(self.rng.random())
                px=h["x"]+math.cos(angle)*radius; py=h["y"]+math.sin(angle)*radius
                if h["dtype"]=="fire":
                    color=self.rng.choice([(255,75,35),(255,125,45),(255,185,70)])
                elif h["dtype"]=="poison":
                    color=self.rng.choice([(70,255,95),(110,230,75),(45,190,90)])
                else:
                    color=self.rng.choice([(110,225,255),(160,245,255),(75,185,255)])
                bolt=h["dtype"]=="electric"
                h.setdefault("particles",[]).append({"x":px,"y":py,"dx":self.rng.uniform(-10,10),"dy":self.rng.uniform(-14,14),"life":self.rng.uniform(0.22,0.55),"max_life":0.55,"color":color,"bolt":bolt})
            for particle in h.get("particles", []):
                particle["life"]-=dt
                particle["x"]+=particle["dx"]*dt; particle["y"]+=particle["dy"]*dt
            h["particles"]=[particle for particle in h.get("particles",[]) if particle["life"]>0]
            if h["tick"]<=0:
                h["tick"]=0.65
                if math.hypot(self.player.x-h["x"],self.player.y-h["y"])<=h["radius"]:
                    if self.player.take_damage(h["damage"]):
                        self.player.set_status({"fire":"burn","poison":"poison","electric":"electric"}.get(h["dtype"], h["dtype"]), 1.3)
                        self.on_player_hit(h["x"],h["y"],h["damage"])
                for e in self.enemies:
                    if e.alive and math.hypot(e.x-h["x"],e.y-h["y"])<=h["radius"]:
                        e.hurt(h["damage"],math.atan2(e.y-h["y"],e.x-h["x"]))
        self.hazards=[h for h in self.hazards if h["life"]>0]
        for wave in self.wave_attacks:
            wave["life"]-=dt; wave["radius"]+=wave["speed"]*dt
            if not wave.get("hit") and abs(math.hypot(self.player.x-wave["x"],self.player.y-wave["y"])-wave["radius"])<16:
                wave["hit"]=True
                if self.player.take_damage(wave["damage"]): self.on_player_hit(wave["x"],wave["y"],wave["damage"])
        self.wave_attacks=[w for w in self.wave_attacks if w["life"]>0]

    def _update_pickups(self,dt):
        """Actualiza monedas físicas y las recoge al acercarse el jugador."""
        p=self.player
        kept=[]
        for pickup in self.pickups:
            if pickup.get("kind") != "coin":
                kept.append(pickup)
                continue
            dx,dy=pickup["x"]-p.x,pickup["y"]-p.y
            dist=math.hypot(dx,dy)
            magnet=64.0+float(getattr(p,"coin_radius",0))  # 2 bloques (TILE=32)
            if dist <= magnet:
                # Atracción física suave: la moneda vuela hacia el jugador antes
                # de ser recogida, en lugar de teletransportarse desde el radio.
                if dist > 13.0:
                    pull=420.0*dt
                    step=min(dist-13.0,max(0.0,pull))
                    if dist > 0.001:
                        pickup["x"] += dx/dist*step
                        pickup["y"] += dy/dist*step
                    kept.append(pickup)
                    continue
                amount=max(1,int(pickup.get("amount",1)))
                p.coins += amount
                self.stats["coins"] += amount
                self.emit("coin_pickup",pickup["x"],pickup["y"],amount)
            else:
                kept.append(pickup)
        self.pickups=kept
