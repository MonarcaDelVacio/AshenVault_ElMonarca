"""Jefes: fases con patrones de ataque realmente distintos y overlays de datos."""
import math
import copy
from .enemies import Enemy


class Boss(Enemy):
    def __init__(self, bdef, x, y, rng=None, difficulty=1):
        bdef=copy.copy(bdef)
        bdef.phases=copy.deepcopy(getattr(bdef, "phases", []))
        super().__init__(bdef, x, y, rng)
        self.difficulty_scale=max(1.0,float(difficulty))
        self.d.base_boss_damage=float(getattr(bdef,"damage",3))
        self.hp*=1.0 + 0.18*(self.difficulty_scale-1); self.max_hp=self.hp
        self.phase = 1
        self.phase_defs = bdef.phases
        self.is_boss = True
        self.boss_style = getattr(bdef, "boss_style", "commander")
        self.shield_active = False
        self.shield_timer = 0.0
        self.stomp_timer = 2.5
        self.special_counter = 0
        self.laser_timer = 4.0
        self._phase_base = {
            k: getattr(bdef, k) for k in (
                "cooldown", "speed", "pellets", "fan_angle",
                "projectile_pattern", "burst_ring", "spiral_speed",
                "summon_interval", "summon_ids", "summon_count", "max_summons"
            ) if hasattr(bdef, k)
        }


    def _attack(self, sim, dist):
        style=self.boss_style
        self.special_counter += 1
        p = sim.player
        self.cooldown = self.d.cooldown
        if getattr(self, "_special_windup", None) == "stomp":
            self._special_windup = None
            radius = 72.0 + 12.0 * self.phase
            damage = float(self.d.damage) * (1.0 + 0.12 * (self.phase - 1))
            sim.wave_attacks.append({"x": self.x, "y": self.y, "radius": 18.0, "speed": 250.0 + 35.0 * self.phase,
                                     "life": 1.15, "damage": damage, "color": tuple(self.d.color), "hit": False})
            sim.emit("boss_stomp", self.x, self.y)
            sim.emit("boss_shockwave", self.x, self.y, radius, damage)
            return
        melee_profile = bool(getattr(self.d, "ranged_melee_profile", False))
        melee_threshold = float(getattr(self.d, "ranged_melee_threshold", 155.0))

        # Los jefes comparten los materiales visuales, pero NO comparten el patrón.
        # Cada arquetipo tiene una respuesta propia a larga distancia y conserva
        # su identidad melee cuando el jugador se acerca.
        if melee_profile and dist <= melee_threshold:
            hit_radius = float(getattr(self.d, "hit_radius", 58.0))
            if dist <= hit_radius + p.radius and p.take_damage(self.d.damage):
                sim.on_player_hit(self.x, self.y, self.d.damage)
            rank_scale = 1.65 + 0.12 * max(0, self.phase - 1)
            sim.emit("melee_swing", self.x, self.y, self.facing, self.d.color, max(48.0, hit_radius), rank_scale)
            if style in ("tank", "colossus") and self.phase >= 2:
                radius = 82.0 + 14.0 * self.phase
                sim.emit("explosion", self.x + math.cos(self.facing) * 42.0,
                         self.y + math.sin(self.facing) * 42.0, radius, tuple(self.d.color))
            return

        # Custodio: cazador. Tres proyectiles teledirigidos que corrigen su rumbo.
        if style == "commander":
            base=math.atan2(p.y-self.y,p.x-self.x)
            count=1 if self.phase==1 else 2 if self.phase==2 else 3
            for i in range(count):
                off=(i-(count-1)/2)*0.20
                sim.spawn_projectile(1,self.x,self.y,base+off,225+28*self.phase,
                    5+self.phase,7.0+0.8*self.phase,7.0,tuple(self.d.color),"fire",0,0,
                    False,None,self.phase>=3,88+16*self.phase,False,4.0,1.75+0.18*self.phase)
            sim.emit("boss_homing",self.x,self.y,self.phase,base)
            sim.emit("enemy_shoot", self.x, self.y, f"homing_fire_phase{self.phase}")
            return

        # Matrona: invocación + anillo giratorio. No dispara la misma ráfaga que el Custodio.
        if style == "summoner":
            base=sim.time*1.4
            count=6+self.phase*2
            for i in range(count):
                a=base+2*math.pi*i/count
                sim.spawn_projectile(1,self.x,self.y,a,150+18*self.phase,3.0+self.phase*0.6,
                    6.0,5.0,tuple(self.d.color),"ice",0,0,False,None,False,0,False,0,1.25+0.1*self.phase)
            sim.emit("boss_summon_ring",self.x,self.y,self.phase)
            sim.emit("enemy_shoot", self.x, self.y, f"summon_ring_phase{self.phase}")
            if self.phase>=2 and self.summon_timer<=0:
                self.summon_timer=2.0
            return

        # Juez: pesado. Una descarga explosiva lenta y una onda frontal en fases altas.
        if style == "tank":
            base=math.atan2(p.y-self.y,p.x-self.x)
            count=2 if self.phase<3 else 3
            for i in range(count):
                off=(i-(count-1)/2)*0.24
                sim.spawn_projectile(1,self.x,self.y,base+off,165+18*self.phase,7+self.phase,
                    10.0,7.0,tuple(self.d.color),"explosive",0,0,False,None,True,
                    95+18*self.phase,False,0,1.9+0.15*self.phase)
            sim.emit("boss_heavy_burst",self.x,self.y,self.phase)
            sim.emit("enemy_shoot", self.x, self.y, f"heavy_burst_phase{self.phase}")
            return

        # Arconte: barrera + lanzas rápidas en cruz. Es un patrón de precisión, no de abanico.
        if style == "mage":
            base=math.atan2(p.y-self.y,p.x-self.x)
            count=4 if self.phase<3 else 6
            for i in range(count):
                a=base + (i-(count-1)/2)*0.12
                sim.spawn_projectile(1,self.x,self.y,a,360+35*self.phase,3.5+self.phase,
                    5.0,5.0,tuple(self.d.color),"energy",0,0,False,None,False,0,False,0,1.35+0.1*self.phase)
            sim.emit("boss_lance",self.x,self.y,self.phase)
            sim.emit("enemy_shoot", self.x, self.y, f"lance_phase{self.phase}")
            return

        # Coloso: pisotón cerca; a distancia lanza proyectiles pesados en línea y, en
        # la última fase, una explosión retardada. El material visual sigue siendo fuego.
        if style == "colossus":
            base=math.atan2(p.y-self.y,p.x-self.x)
            count=1 if self.phase==1 else 2 if self.phase==2 else 3
            for i in range(count):
                off=(i-(count-1)/2)*0.28
                sim.spawn_projectile(1,self.x,self.y,base+off,185+20*self.phase,8+self.phase*1.5,
                    11.0,7.0,tuple(self.d.color),"fire",0,0,False,None,self.phase>=3,
                    105+20*self.phase,False,0,2.0+0.18*self.phase)
            sim.emit("boss_heavy_burst",self.x,self.y,self.phase)
            sim.emit("enemy_shoot", self.x, self.y, f"colossus_burst_phase{self.phase}")
            return

        # Regente: espiral que gira alrededor de su propio eje y una segunda ráfaga
        # teledirigida en la fase final.
        if style == "regent":
            base=sim.time*getattr(self.d,"spiral_speed",3.5)
            count=8+self.phase*2
            for i in range(count):
                a=base+2*math.pi*i/count
                sim.spawn_projectile(1,self.x,self.y,a,205+22*self.phase,4+self.phase,
                    6.5,6.0,tuple(self.d.color),"fire",0,0,False,None,self.phase>=3,
                    78+15*self.phase,False,0,1.5+0.12*self.phase)
            if self.phase>=3:
                target=math.atan2(p.y-self.y,p.x-self.x)
                sim.spawn_projectile(1,self.x,self.y,target,300,9,8,7,tuple(self.d.color),"fire",
                    0,0,False,None,True,120,False,5.0,2.2)
                sim.emit("boss_homing",self.x,self.y,self.phase,target)
                sim.emit("enemy_shoot", self.x, self.y, f"regent_spiral_phase{self.phase}")
            return

        super()._attack(sim,dist)

    def update(self, sim, dt):
        self.shield_timer=max(0.0,self.shield_timer-dt)
        self.laser_timer=max(0.0,self.laser_timer-dt)
        # Todos los jefes pueden canalizar el mismo rayo base; el color, daño y
        # grosor escalan con su propio modelo y fase. No reemplaza su patrón normal.
        if self.laser_timer <= 0 and self.spawn_delay <= 0 and self.state not in ("windup","recover") and self.difficulty_scale >= 1:
            if self.boss_style == "tank" and self.phase == 1:
                self.laser_timer = 6.5
            else:
                self.laser_timer = max(4.2, float(getattr(self.d,"laser_interval",5.8)) - self.phase*0.35)
            sim.start_enemy_laser(
                self, self.facing,
                duration=1.8 + 0.25*self.phase,
                color=tuple(getattr(self.d,"laser_color",getattr(self.d,"color",(255,100,100)))),
                damage=float(getattr(self.d,"laser_damage",10.0)) + 2.5*self.phase,
                width=1.5 + 0.5*self.phase,
                max_width=8.0 + 2.5*self.phase,
                range_=float(getattr(self.d,"laser_range",820.0)),
                explosion_radius=20.0 + 4.0*self.phase,
            )
        if self.boss_style == "mage":
            if self.shield_timer <= 0:
                self.shield_active = True
                self.shield_timer = getattr(self.d,"shield_interval",5.5)
                sim.emit("boss_shield",self.x,self.y,True)
            # Shield is active only during the first portion of each cycle.
            self.shield_active = self.shield_timer > max(0.0,getattr(self.d,"shield_interval",5.5)-getattr(self.d,"shield_duration",2.2))
        if self.boss_style == "colossus":
            self.stomp_timer-=dt
            if self.stomp_timer<=0 and self.state not in ("windup","recover"):
                self.state="windup"; self.timer=0.9; self._special_windup="stomp"
                self.stomp_timer=getattr(self.d,"stomp_interval",4.8)
        hp_ratio = self.hp / self.max_hp if self.max_hp else 0
        new_phase = 1 if hp_ratio > 0.66 else 2 if hp_ratio > 0.33 else 3
        if new_phase != self.phase:
            self.phase = new_phase
            sim.emit("boss_phase", self.x, self.y, self.phase)
            self.cooldown = 0.0
            self.summon_timer = 0.0

        pd = self.phase_defs[self.phase - 1]
        scale=self.difficulty_scale
        keys = (
            "cooldown", "speed", "pellets", "fan_angle", "projectile_pattern", "projectile_speed",
            "burst_ring", "spiral_speed", "summon_interval", "summon_ids",
            "summon_count", "max_summons", "preferred_distance"
        )
        old = {k: getattr(self.d, k, None) for k in keys}
        for k in keys:
            if k in pd:
                value=pd[k]
                if k in ("cooldown", "speed", "projectile_speed", "preferred_distance"):
                    if k == "cooldown": value=max(0.28, float(value)/(1+0.08*(scale-1)))
                    elif k == "speed": value=float(value)*(1+0.035*(scale-1))
                    elif k == "projectile_speed": value=float(value)*(1+0.05*(scale-1))
                setattr(self.d, k, value)
        self.d.damage = getattr(self.d, "base_boss_damage", getattr(self.d, "damage", 3)) * (1+0.16*(scale-1))

        # Cada arquetipo ocupa el espacio de forma distinta: presión cercana,
        # control a distancia, o invocación para obligar al jugador a reposicionarse.
        style = self.boss_style
        preferred = {
            "commander": 245, "summoner": 285, "tank": 105,
            "mage": 355, "colossus": 135, "regent": 175,
        }.get(style, self.d.preferred_distance)
        self.d.preferred_distance = preferred

        # Sólo ciertos jefes invocan; los demás tienen sus propios patrones.
        summon_interval = (getattr(self.d, "summon_interval", 5.5) if style == "summoner"
                           else 7.0 if style == "regent" and self.phase >= 3 else 0.0)
        if summon_interval > 0 and self.summon_timer <= 0 and self.spawn_delay <= 0:
            if sim.count_summoned() < min(7, getattr(self.d, "max_summons", 6)):
                summon_ids = getattr(self.d, "summon_ids", ["grunt", "runner", "gunner", "spreader"])
                count = 3 if self.phase == 3 else 2
                if sim.spawn_summons(self, summon_ids, count):
                    sim.emit("enemy_summon", self.x, self.y, self.id)
                    self.summon_timer = summon_interval
            else:
                self.summon_timer = 0.6

        super().update(sim, dt)
        for k, value in old.items():
            if value is None:
                try:
                    delattr(self.d, k)
                except AttributeError:
                    pass
            else:
                setattr(self.d, k, value)
