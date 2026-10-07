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
        self.stunned = 0.0
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
        self.target_lock_timer = 0.0
        self.confused = 0.0
        self.shield_active = False
        self.shield_timer = 0.0
        self.dot_effects = {}
        self.stomp_timer = r.uniform(2.8, 5.2) if float(getattr(edef, "radius", 0)) >= 22 else 999.0

    def reset(self, edef, x, y, rng=None):
        self.d=edef; self.rng=rng; self.x,self.y=x,y
        self.hp=float(edef.hp); self.max_hp=float(edef.hp); self.radius=edef.radius
        self.state=IDLE; self.timer=0.0
        r=rng if rng is not None else __import__("random").Random()
        self.cooldown=r.uniform(0.3,1.0); self.alive=True; self.flash=0.0
        self.attack_anim_time=99.0
        self.kx=self.ky=0.0; self.facing=0.0; self.strafe=r.choice((-1,1))
        self.spawn_delay=0.6; self.frozen=0.0; self.stunned=0.0; self.summon_timer=0.0; self.boss_pulse_cd=2.2; self.miniboss_pulse_cd=3.0
        self.is_boss=False; self.is_miniboss=False; self.is_summoned=False; self.is_boss_guard=False
        self.weapon_id=getattr(edef, "weapon_id", None)
        self.shield_integrity=0.0
        self.shield_timer=0.0
        self.brain_state="observe"; self.brain_timer=r.uniform(0.45,1.15); self.dodge_cd=0.0
        self.target=None; self.target_lock_timer=0.0; self.confused=0.0; self.shield_active=False; self.shield_timer=0.0; self.dot_effects = {}
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
        self.stunned = max(0.0, getattr(self, "stunned", 0.0) - dt)
        self.summon_timer = max(0.0, self.summon_timer - dt)
        self.boss_pulse_cd = max(0.0, self.boss_pulse_cd - dt)
        self.miniboss_pulse_cd = max(0.0, self.miniboss_pulse_cd - dt)
        self.dodge_cd = max(0.0, self.dodge_cd - dt)
        self.target_lock_timer = max(0.0, self.target_lock_timer - dt)
        self.confused = max(0.0, getattr(self, "confused", 0.0) - dt)
        if self.shield_active:
            self.shield_timer = max(0.0, self.shield_timer - dt)
            if self.shield_timer <= 0:
                self.shield_active = False
                self.shield_integrity = 0.0
        self.attack_anim_time = min(8.0, self.attack_anim_time + dt)
        if self.frozen > 0 or getattr(self, "stunned", 0.0) > 0:
            return
        if abs(self.kx) + abs(self.ky) > 1:
            self.x, self.y = sim.move_actor(self.x, self.y, self.kx * dt, self.ky * dt, self.radius)
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

        # Confusion is intentionally different from stun/freeze: the enemy can
        # still move, but loses reliable pursuit/attack direction for its
        # duration.  This gives Rook's confusion effect real gameplay impact
        # without adding another immobilizing status.
        confused = getattr(self, "confused", 0.0) > 0.0
        if confused and sees:
            dx, dy = -dx, -dy
            self.facing = math.atan2(dy, dx)
            dist = math.hypot(dx, dy) or 0.001
        if self._defensive_reaction(sim, dt):
            return

        if confused:
            # Confused enemies do not initiate attacks or deliberate pursuit.
            # When they can see the target they retreat from it; otherwise they
            # drift laterally, preserving the distinction from stun/freeze.
            if sees:
                self._step(sim, dx / dist, dy / dist, d.speed * 0.75, dt)
            else:
                self._step(sim, -dy / dist * self.strafe, dx / dist * self.strafe, d.speed * 0.55, dt)
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
        for pr in getattr(sim,"_active_player_projectiles",()):
            vx,vy=pr.vx,pr.vy; speed2=vx*vx+vy*vy
            if speed2<=1: continue
            t=((self.x-pr.x)*vx+(self.y-pr.y)*vy)/speed2
            if 0<t<0.8:
                cx,cy=pr.x+vx*t,pr.y+vy*t
                if math.hypot(self.x-cx,self.y-cy)<self.radius+22: threats.append((pr,t))
        if not threats: return False
        pr,_=min(threats,key=lambda q:q[1])
        lethal=float(pr.damage)>=max(1.0,self.hp+self.shield_integrity)
        weapon_def=sim.data.weapons.get(getattr(self.d,"weapon_id",None))
        magic_capable=(getattr(self.d,"magic_user",False)
                        or getattr(weapon_def,"class","")=="magic")
        # Los escudos son una defensa mágica, no una habilidad genérica de cualquier NPC.
        # Especialmente los enemigos de melee (esqueletos, goblins, etc.) nunca los generan.
        shield_chance=float(getattr(self.d,"shield_chance",0.04))
        if magic_capable and getattr(self.d,"shielded",False) and self.shield_timer <= 0 and self.rng.random() < min(0.08,shield_chance):
            self.shield_active=True
            self.shield_integrity=float(getattr(self.d,"shield_durability",48.0))
            self.shield_timer=float(getattr(self.d,"emergency_shield_duration",1.2))
            sim.emit("enemy_shield_up",self.x,self.y,self.shield_timer)
            return True
        if self.dodge_cd<=0 and self.rng.random()<float(getattr(self.d,"dodge_chance",0.10)):
            self.dodge_cd=float(getattr(self.d,"dodge_cooldown",0.9))
            vx,vy=pr.vx,pr.vy; n=math.hypot(vx,vy) or 1.0
            self._step(sim,-vy/n*self.strafe,vx/n*self.strafe,self.d.speed*1.35,dt)
            self.strafe*=-1
            sim.emit("enemy_dodge",self.x,self.y)
            return True
        if self.rng.random()<float(getattr(self.d,"cover_chance",0.12)):
            # Buscar cobertura real contra el proyectil, no simplemente el prop
            # más cercano. El enemigo debe colocarse en el lado opuesto al
            # proyectil para que el obstáculo quede entre ambos.
            vx,vy=pr.vx,pr.vy
            vn=math.hypot(vx,vy) or 1.0
            ux,uy=vx/vn,vy/vn
            props=[]
            for q in getattr(sim,"props",()):
                if q.get("broken"):
                    continue
                qx,qy=float(q.get("x",0)),float(q.get("y",0))
                ex,ey=qx-self.x,qy-self.y
                along=ex*ux+ey*uy
                if along <= 0 or along > 180:
                    continue
                lateral=abs(ex*uy-ey*ux)
                qr=float(q.get("radius",16.0))
                if lateral <= qr + self.radius + 18:
                    # Punto protegido: el prop queda entre el enemigo y la
                    # dirección de llegada del proyectil.
                    cover_x=qx+ux*(qr+self.radius+10.0)
                    cover_y=qy+uy*(qr+self.radius+10.0)
                    distance=math.hypot(cover_x-self.x,cover_y-self.y)
                    if distance <= 220:
                        props.append((distance,q,cover_x,cover_y))
            if props:
                _,q,cx,cy=min(props,key=lambda item:item[0])
                self._step(sim,cx-self.x,cy-self.y,self.d.speed*1.15,dt)
                sim.emit("enemy_cover",self.x,self.y,q.get("kind","prop"))
                return True
        return False

    def _step(self, sim, ux, uy, speed, dt):
        from .systems.enemy_movement import step
        return step(self, sim, ux, uy, speed, dt)

    def _chase(self, sim, dt, speed):
        from .systems.enemy_movement import chase
        return chase(self, sim, dt, speed)

    def _attack(self, sim, dist):
        """Compatibility facade for the extracted enemy combat system."""
        from .systems.enemy_combat import attack
        return attack(self, sim, dist)
