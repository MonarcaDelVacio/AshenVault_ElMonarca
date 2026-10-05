"""Enemigos: IA determinista con telegráficos, variantes por bioma y comportamiento de invocación."""
import math

IDLE, MOVE, WINDUP, RECOVER = "idle", "move", "windup", "recover"


class Enemy:
    _next_id = 1

    def __init__(self, edef, x, y, rng=None):
        self.d = edef
        self.id = Enemy._next_id
        Enemy._next_id += 1
        self.rng = rng
        self.x, self.y = x, y
        self.hp = float(edef.hp)
        self.max_hp = float(edef.hp)
        self.radius = edef.radius
        self.state = IDLE
        self.timer = 0.0
        self.attack_anim_time = 99.0
        r = rng if rng is not None else __import__("random").Random()
        self.cooldown = r.uniform(0.3, 1.0)
        self.alive = True
        self.flash = 0.0
        self.kx = self.ky = 0.0
        self.facing = 0.0
        self.strafe = r.choice((-1, 1))
        self.spawn_delay = 0.6
        self.frozen = 0.0
        self.summon_timer = 0.0
        self.boss_pulse_cd = 2.2
        self.miniboss_pulse_cd = 3.0
        self.is_boss = False
        self.is_miniboss = False
        self.weapon_id = getattr(edef, "weapon_id", None)
        self.shield_integrity = 0.0
        self.shield_timer = 0.0
        self.brain_state = "observe"
        self.brain_timer = r.uniform(0.45, 1.15)
        self.dodge_cd = 0.0
        self.target = None
        self.shield_active = False
        self.shield_timer = 0.0
        self.stomp_timer = r.uniform(2.8, 5.2) if float(getattr(edef, "radius", 0)) >= 22 else 999.0

    def reset(self, edef, x, y, rng=None):
        self.d=edef; self.rng=rng; self.x,self.y=x,y
        self.hp=float(edef.hp); self.max_hp=float(edef.hp); self.radius=edef.radius
        self.state=IDLE; self.timer=0.0
        r=rng if rng is not None else __import__("random").Random()
        self.cooldown=r.uniform(0.3,1.0); self.alive=True; self.flash=0.0
        self.attack_anim_time=99.0
        self.kx=self.ky=0.0; self.facing=0.0; self.strafe=r.choice((-1,1))
        self.spawn_delay=0.6; self.frozen=0.0; self.summon_timer=0.0; self.boss_pulse_cd=2.2; self.miniboss_pulse_cd=3.0
        self.is_boss=False; self.is_miniboss=False; self.is_summoned=False; self.is_boss_guard=False
        self.weapon_id=getattr(edef, "weapon_id", None)
        self.shield_integrity=0.0
        self.shield_timer=0.0
        self.brain_state="observe"; self.brain_timer=r.uniform(0.45,1.15); self.dodge_cd=0.0
        self.target=None; self.shield_active=False; self.shield_timer=0.0
        self.stomp_timer=r.uniform(2.8,5.2) if float(getattr(edef,"radius",0))>=22 else 999.0
        return self

    @property
    def telegraph(self):
        if self.state == WINDUP and self.d.windup > 0:
            return 1 - self.timer / self.d.windup
        return 0.0

    def hurt(self, dmg, ang):
        self.hp -= dmg
        self.flash = 0.1
        self.kx += math.cos(ang) * 90
        self.ky += math.sin(ang) * 90
        if self.hp <= 0:
            self.alive = False

    def update(self, sim, dt):
        d = self.d
        p = sim.player
        self.flash = max(0.0, self.flash - dt)
        self.spawn_delay = max(0.0, self.spawn_delay - dt)
        self.cooldown = max(0.0, self.cooldown - dt)
        self.frozen = max(0.0, self.frozen - dt)
        self.summon_timer = max(0.0, self.summon_timer - dt)
        self.boss_pulse_cd = max(0.0, self.boss_pulse_cd - dt)
        self.miniboss_pulse_cd = max(0.0, self.miniboss_pulse_cd - dt)
        self.dodge_cd = max(0.0, self.dodge_cd - dt)
        if self.shield_active:
            self.shield_timer = max(0.0, self.shield_timer - dt)
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_integrity = 0.0
        self.attack_anim_time = min(8.0, self.attack_anim_time + dt)
        if self.frozen > 0:
            return
        if abs(self.kx) + abs(self.ky) > 1:
            self.x, self.y = sim.arena.move(self.x, self.y, self.kx * dt, self.ky * dt, self.radius)
            self.kx *= max(0.0, 1 - 10 * dt)
            self.ky *= max(0.0, 1 - 10 * dt)
        if self.spawn_delay > 0 or not p.alive:
            return

        # Los jefes gestionan sus invocaciones según su arquetipo; aquí sólo enemigos normales.
        if not self.is_boss and getattr(d, "summon_interval", 0) > 0 and self.summon_timer <= 0:
            if sim.count_summoned() < getattr(d, "max_summons", 3):
                if sim.spawn_summons(self, getattr(d, "summon_ids", []), getattr(d, "summon_count", 1)):
                    self.summon_timer = d.summon_interval
                    self.cooldown = max(self.cooldown, d.summon_interval * 0.35)
                    self.state = RECOVER
                    self.timer = d.recover
                    sim.emit("enemy_summon", self.x, self.y, self.id)
                    return
            self.summon_timer = min(0.5, getattr(d, "summon_interval", 0))

        target = sim.enemy_target(self)
        self.target = target
        tx, ty = (target["x"], target["y"]) if target else (p.x, p.y)
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy) or 0.001
        self.facing = math.atan2(dy, dx)
        sees = dist < d.detect_range and sim.arena.line_of_sight(self.x, self.y, tx, ty)
        if self._defensive_reaction(sim, dt):
            return
        if (not self.is_boss and not self.is_miniboss and float(getattr(d,"radius",0)) >= 22
                and self.stomp_timer <= 0 and self.state not in (WINDUP,RECOVER)):
            self.stomp_timer=float(getattr(d,"stomp_interval",5.0))
            radius=float(getattr(d,"stomp_radius",145.0))
            damage=float(getattr(d,"stomp_damage",d.damage*1.15))
            sim.wave_attacks.append({"x":self.x,"y":self.y,"radius":10.0,"speed":360.0,
                "life":radius/360.0+0.25,"damage":damage,"color":tuple(getattr(d,"color",(180,160,140))),
                "team":1,"max_radius":radius,"hit":False})
            sim.emit("boss_stomp",self.x,self.y,radius,damage)
            return

        # Los jefes expulsan al jugador si logra pegarse demasiado. Es un pulso de
        # control de espacio, sin daño, con telegráfico visual y enfriamiento propio.
        if self.is_boss and dist <= 118 and self.boss_pulse_cd <= 0:
            push = 420.0
            p.rvx += math.cos(self.facing) * push
            p.rvy += math.sin(self.facing) * push
            self.boss_pulse_cd = 2.8
            sim.emit("boss_shockwave", self.x, self.y, 118.0, getattr(d, "color", (220, 100, 100)))

        if self.is_miniboss and dist <= 96 and self.miniboss_pulse_cd <= 0:
            push = 250.0
            p.rvx += math.cos(self.facing) * push
            p.rvy += math.sin(self.facing) * push
            self.miniboss_pulse_cd = float(getattr(d, "miniboss_pulse_interval", 4.2))
            sim.emit("miniboss_shockwave", self.x, self.y, 96.0, getattr(d, "color", (190, 110, 220)))

        if self.state == WINDUP:
            self.timer -= dt
            if self.timer <= 0:
                self._attack(sim, dist)
                self.state, self.timer = RECOVER, d.recover
            return
        if self.state == RECOVER:
            self.timer -= dt
            if self.timer <= 0:
                self.state = MOVE
            return

        self.brain_timer -= dt
        if self.brain_timer <= 0:
            if d.ai in ("melee","charger"):
                self.brain_state=self.rng.choice(("observe","approach","attack","retreat","rush"))
            else:
                self.brain_state=self.rng.choice(("observe","approach","attack","retreat","strafe"))
            self.brain_timer=self.rng.uniform(0.55,1.45)
        self.state = MOVE
        if d.ai in ("melee", "charger"):
            if dist <= d.attack_range and self.cooldown <= 0 and self.brain_state in ("attack","rush","approach"):
                self.state, self.timer = WINDUP, d.windup
                self.attack_anim_time = 0.0
            elif self.brain_state == "retreat" and sees:
                self._step(sim, -dx / dist, -dy / dist, d.speed * 1.15, dt)
            elif d.ai == "charger" and sees and dist > d.attack_range and self.brain_state == "rush":
                self._step(sim, dx / dist, dy / dist, getattr(d, "charge_speed", d.speed), dt)
            elif self.brain_state == "observe":
                self._step(sim, -dy / dist * self.strafe, dx / dist * self.strafe, d.speed * 0.18, dt)
            else:
                self._chase(sim, dt, d.speed * (0.72 if self.brain_state == "approach" else 1.0))
        elif d.ai == "flying":
            # Los voladores no necesitan navegar por el flow-field; sólo evitan el contacto.
            if sees and dist <= d.attack_range and self.cooldown <= 0:
                self.state, self.timer = WINDUP, d.windup
            elif sees and dist < d.preferred_distance * 0.75:
                self._step(sim, -dx / dist, -dy / dist, d.speed, dt)
            elif sees and dist <= d.preferred_distance * 1.2:
                self._step(sim, -dy / dist * self.strafe, dx / dist * self.strafe, d.speed * .65, dt)
                if self.rng and self.rng.random() < dt * .35:
                    self.strafe *= -1
            else:
                self._step(sim, dx / dist, dy / dist, d.speed, dt)
        else:
            if sees and dist <= d.attack_range and self.cooldown <= 0 and self.brain_state in ("attack","strafe","retreat"):
                self.state, self.timer = WINDUP, d.windup
            elif self.brain_state == "retreat" and sees:
                self._step(sim, -dx / dist, -dy / dist, d.speed * 1.15, dt)
            elif self.brain_state in ("strafe","observe") and sees:
                self._step(sim, -dy / dist * self.strafe, dx / dist * self.strafe, d.speed * 0.72, dt)
                if self.rng and self.rng.random() < dt * 0.55:
                    self.strafe *= -1
            elif sees and dist < d.preferred_distance * 0.65:
                self._step(sim, -dx / dist, -dy / dist, d.speed, dt)
            else:
                self._chase(sim, dt, d.speed * (0.75 if self.brain_state == "approach" else 1.0))

    def _defensive_reaction(self, sim, dt):
        threats=[]
        for pr in sim.pool.items:
            if not pr.active or pr.team != 0: continue
            vx,vy=pr.vx,pr.vy; speed2=vx*vx+vy*vy
            if speed2<=1: continue
            t=((self.x-pr.x)*vx+(self.y-pr.y)*vy)/speed2
            if 0<t<0.8:
                cx,cy=pr.x+vx*t,pr.y+vy*t
                if math.hypot(self.x-cx,self.y-cy)<self.radius+22: threats.append((pr,t))
        if not threats: return False
        pr,_=min(threats,key=lambda q:q[1])
        lethal=float(pr.damage)>=max(1.0,self.hp+self.shield_integrity)
        if getattr(self.d,"shielded",False) and self.shield_timer <= 0 and self.rng.random() < 0.45:
            self.shield_active=True
            self.shield_integrity=float(getattr(self.d,"shield_durability",48.0))
            self.shield_timer=float(getattr(self.d,"emergency_shield_duration",1.2))
            sim.emit("enemy_shield_up",self.x,self.y,self.shield_timer)
            return True
        if lethal and self.rng.random()<float(getattr(self.d,"emergency_shield_chance",0.12)):
            self.shield_active=True
            self.shield_integrity=float(getattr(self.d,"shield_durability",48.0))
            self.shield_timer=float(getattr(self.d,"emergency_shield_duration",1.2))
            sim.emit("enemy_emergency_shield",self.x,self.y,self.shield_timer)
            return True
        if self.dodge_cd<=0 and self.rng.random()<float(getattr(self.d,"dodge_chance",0.10)):
            self.dodge_cd=float(getattr(self.d,"dodge_cooldown",0.9))
            vx,vy=pr.vx,pr.vy; n=math.hypot(vx,vy) or 1.0
            self._step(sim,-vy/n*self.strafe,vx/n*self.strafe,self.d.speed*1.35,dt)
            self.strafe*=-1
            sim.emit("enemy_dodge",self.x,self.y)
            return True
        if self.rng.random()<float(getattr(self.d,"cover_chance",0.12)):
            props=[q for q in getattr(sim,"props",[]) if not q.get("broken") and math.hypot(q["x"]-self.x,q["y"]-self.y)<150]
            if props:
                q=min(props,key=lambda o:math.hypot(o["x"]-self.x,o["y"]-self.y))
                self._step(sim,q["x"]-self.x,q["y"]-self.y,self.d.speed*0.9,dt)
                sim.emit("enemy_cover",self.x,self.y)
                return True
        return False

    def _step(self, sim, ux, uy, speed, dt):
        ox, oy = self.x, self.y
        # Flying enemies can cross interior walls; they still remain inside arena bounds.
        if self.d.ai == "flying":
            self.x = max(self.radius + 2, min(sim.arena.width - self.radius - 2, self.x + ux * speed * dt))
            self.y = max(self.radius + 2, min(sim.arena.height - self.radius - 2, self.y + uy * speed * dt))
        else:
            self.x, self.y = sim.move_actor(self.x, self.y, ux * speed * dt, uy * speed * dt, self.radius)
        if abs(self.x - ox) + abs(self.y - oy) < speed * dt * 0.2:
            self.strafe *= -1

    def _chase(self, sim, dt, speed):
        p = sim.player
        if sim.arena.line_of_sight(self.x, self.y, p.x, p.y):
            tx, ty = p.x, p.y
        else:
            step = sim.arena.best_step(sim.flow, self.x, self.y)
            tx, ty = step if step else (p.x, p.y)
        dx, dy = tx - self.x, ty - self.y
        n = math.hypot(dx, dy) or 1
        sx = sy = 0.0
        for o in sim.enemies:
            if o is not self and o.alive:
                ex, ey = self.x - o.x, self.y - o.y
                r = self.radius + o.radius + 4
                if abs(ex) < r and abs(ey) < r:
                    dd = math.hypot(ex, ey) or 1
                    if dd < r:
                        sx += ex / dd * (r - dd) / r
                        sy += ey / dd * (r - dd) / r
        ux, uy = dx / n + sx * 0.8, dy / n + sy * 0.8
        m = math.hypot(ux, uy) or 1
        self._step(sim, ux / m, uy / m, speed, dt)

    def _attack(self, sim, dist):
        d = self.d
        p = sim.player
        self.cooldown = d.cooldown
        if d.ai in ("melee", "charger"):
            target=self.target or {"kind":"player","obj":p,"x":p.x,"y":p.y}
            if target.get("kind")=="drone":
                if dist <= d.hit_radius + target["obj"].get("radius",10):
                    sim.damage_drone(target["obj"],d.damage,self.x,self.y)
                return
            if dist <= d.hit_radius + p.radius:
                if p.take_damage(d.damage, math.atan2(self.y-p.y,self.x-p.x)):
                    sim.on_player_hit(self.x, self.y, d.damage)
                    dtype=getattr(d, "damage_type", "physical")
                    if dtype == "ice":
                        sim._apply_freeze(p, d.damage)
                        p.set_status("freeze", 1.6)
                    elif dtype in ("fire", "poison", "electric"):
                        p.set_status({"fire":"burn","poison":"poison","electric":"electric"}[dtype], 2.4)
            rank_scale = 1.0
            if getattr(self, "is_miniboss", False): rank_scale = 1.28
            elif getattr(self, "is_boss", False): rank_scale = 1.65
            # The new melee slash is the only melee attack visual. Its size follows
            # attack power/range and actor rank instead of using a fixed trail.
            slash_range = max(34.0, float(getattr(d, "hit_radius", 36)))
            sim.emit("melee_swing", self.x, self.y, self.facing, d.color, slash_range, rank_scale)
            if getattr(d, "melee_explosion", False):
                ex = self.x + math.cos(self.facing) * min(float(d.hit_radius) * 0.78, 70.0)
                ey = self.y + math.sin(self.facing) * min(float(d.hit_radius) * 0.78, 70.0)
                radius = float(getattr(d, "melee_explosion_radius", 55.0)) * rank_scale
                sim.emit("explosion", ex, ey, radius, tuple(getattr(d, "color", (255, 120, 90))))
            for prop in getattr(sim,"props",[]):
                if prop.get("broken"): continue
                pdx,pdy=prop["x"]-self.x,prop["y"]-self.y
                pdist=math.hypot(pdx,pdy)
                if pdist <= d.hit_radius + prop.get("radius",24):
                    angle=(math.atan2(pdy,pdx)-self.facing+math.pi)%(2*math.pi)-math.pi
                    if abs(angle)<1.1:
                        prop["hp"]-=max(1.0,d.damage/8.0)
                        if prop["hp"]<=0: sim._break_prop(prop,d.color)
            return

        pattern = getattr(d, "projectile_pattern", "single")
        angles = []
        if pattern == "circle":
            angles = [2 * math.pi * i / max(1, d.pellets) for i in range(d.pellets)]
        elif pattern == "spiral":
            base = sim.time * getattr(d, "spiral_speed", 2.4)
            angles = [base + 2 * math.pi * i / max(1, d.pellets) for i in range(d.pellets)]
        elif pattern == "burst":
            angles = [self.facing + off for off in (-math.radians(18), 0, math.radians(18))]
            if getattr(d, "burst_ring", False):
                angles += [self.facing + math.pi / 2, self.facing - math.pi / 2]
        else:
            n = d.pellets
            for i in range(n):
                off = 0.0 if n == 1 else math.radians(d.fan_angle) * (i / (n - 1) - 0.5)
                angles.append(self.facing + off)
        weapon_def = sim.data.weapons.get(getattr(d, "weapon_id", ""))
        projectile_sprite = getattr(weapon_def, "projectile_sprite", None) if weapon_def else None
        dtype = getattr(d, "damage_type", None) or (getattr(weapon_def, "damage_type", "physical") if weapon_def else "physical")
        color = tuple(getattr(d, "projectile_color", getattr(weapon_def, "color", getattr(d, "color", (255, 120, 90))))) if weapon_def else tuple(getattr(d, "projectile_color", getattr(d, "color", (255, 120, 90))))
        explosive = bool(getattr(d, "explosive", False) or (weapon_def and getattr(weapon_def, "explosive", False)))
        rank_scale = 1.0
        if getattr(self, "is_miniboss", False): rank_scale = 1.28
        elif getattr(self, "is_boss", False): rank_scale = 1.65
        visual_scale = float(getattr(d, "projectile_visual_scale", 1.0)) * rank_scale
        explosion_radius = float(getattr(d, "explosion_radius", 0) or 0)
        if explosive and not explosion_radius:
            explosion_radius = 74.0
        explosion_radius *= rank_scale
        rock_sheet = getattr(d, "projectile_asset_sheet", None)
        if rock_sheet:
            projectile_sprite = f"__sheet__:{rock_sheet}"
        # Enemies borrow weapon visuals but retain their own damage/cooldown limits.
        for a in angles:
            speed = d.projectile_speed
            if weapon_def:
                speed = min(520, max(160, weapon_def.projectile_speed * 0.58))
            sim.spawn_projectile(1, self.x, self.y, a, speed, d.damage,
                                 d.projectile_radius, 4.0, color,
                                 dtype, 0, 0, False, projectile_sprite,
                                 explosive, explosion_radius, False, 0.0, visual_scale)
        sim.emit("enemy_shoot", self.x, self.y, pattern)
