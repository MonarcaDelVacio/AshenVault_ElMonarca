import math
from .weapons import WeaponState, try_fire


class Player:
    def __init__(self, cdef, wdef, pos, meta_upgrades=None, character_progress=None):
        self.c = cdef
        self.x, self.y = pos
        self.radius = cdef.radius
        u = meta_upgrades or {}
        cp = character_progress or {"level":1,"xp":0,"upgrades":{}}
        cu = cp.get("upgrades", {})
        cid = getattr(cdef, "id", "soldier")
        def lv(key): return int(cu.get(key, 0))
        self.character_level = int(cp.get("level", 1))
        self.max_hp = cdef.max_hp + int(u.get("vitality",0))
        self.max_shield = cdef.max_shield + int(u.get("shield",0))
        self.max_energy = cdef.max_energy + int(u.get("energy",0))*10
        self.speed = cdef.speed + int(u.get("speed",0))*5
        self.damage_mult = cdef.damage_mult * (1.0 + int(u.get("damage",0))*0.05)
        self.crit_chance = cdef.crit_chance
        self.shield_regen_rate = cdef.shield_regen_rate + int(u.get("shield_regen",0))*0.15
        if cid == "soldier":
            self.max_hp += lv("max_hp"); self.max_shield += lv("shield"); self.damage_mult *= 1 + lv("damage")*.04
        elif cid == "medic":
            self.max_hp += lv("max_hp"); self.max_energy += lv("energy")*10; self.speed += lv("speed")*5
        elif cid == "vanguard":
            self.max_hp += lv("max_hp"); self.max_shield += lv("shield"); self.damage_mult *= 1 + lv("damage")*.05
        elif cid == "pyromancer":
            self.max_energy += lv("energy")*10; self.damage_mult *= 1 + lv("damage")*.04; self.speed += lv("speed")*5
        elif cid == "striker":
            self.speed += lv("speed")*6; self.crit_chance += lv("crit")*.02; self.damage_mult *= 1 + lv("damage")*.04
        elif cid == "engineer":
            self.max_energy += lv("energy")*10; self.speed += lv("speed")*4; self.damage_mult *= 1 + lv("damage")*.03
        self.hp = self.max_hp
        self.shield = float(self.max_shield)
        self.energy = float(self.max_energy)
        self.character_upgrade_levels = dict(cu)
        self.ability = dict(cdef.ability)
        if cid == "soldier": self.ability["amount"] = self.ability.get("amount",4) + lv("ability")
        elif cid == "medic": self.ability["amount"] = self.ability.get("amount",3) + lv("ability")
        elif cid == "vanguard":
            self.ability["damage"] = self.ability.get("damage",24) + lv("ability")*4
            self.ability["radius"] = self.ability.get("radius",125) + lv("ability")*8
        elif cid == "pyromancer": self.ability["duration"] = self.ability.get("duration",3.0) + lv("ability")*.35
        elif cid == "striker": self.ability["duration"] = self.ability.get("duration",5.0) + lv("ability")*.5
        elif cid == "engineer": self.ability["max_drones"] = self.ability.get("max_drones",2) + lv("ability")
        self.weapon = WeaponState(wdef)
        self.inventory = [self.weapon]
        self.items = []
        self.synergies = []
        self.bonus_pierce = 0
        self.bonus_projectiles = 0
        self.aim = 0.0
        self.facing_x = 1
        self.walk_time = 0.0
        self.fire_buffer = 0.0
        self.noenergy_cd = 0.0
        self.since_hit = 99.0
        self.since_shot = 99.0
        self.rvx = self.rvy = 0.0
        self.invuln = 0.0
        self.hurt_flash = 0.0
        self.heal_flash = 0.0
        self.energy_flash = 0.0
        self.dash_left = 0.0
        self.dash_cd = 0.0
        self.dash_dir = (1.0, 0.0)
        self.ability_cd = 0.0
        self.ability_buff = 0.0
        self.ability_shield_fx = 0.0
        self.drones = 0
        self.ability_shot_timer = 0.0
        # Ventana breve en la que el golpe cuerpo a cuerpo puede interceptar proyectiles.
        # Apuntar por sí solo nunca activa esta protección.
        self.melee_attack_timer = 0.0
        self.alive = True
        self.frozen = 0.0
        # Estados temporales mostrados en el HUD. La simulación los actualiza
        # según el tipo de daño/curación recibido.
        self.status_timers = {}
        self.coins = 0
        # Buffs de estatuas: solo memoria de la run, nunca se guardan en SaveData.
        self.statue_damage_taken_mult = 1.0
        self.statue_melee_mult = 1.0
        self.statue_ranged_mult = 1.0
        self.statue_ability_mult = 1.0
        self.statue_crit_damage_mult = 1.0

    def set_status(self, kind, duration):
        if duration <= 0:
            return
        self.status_timers[str(kind)] = max(float(duration), float(self.status_timers.get(str(kind), 0.0)))

    def feedback_flash(self, kind, duration=0.24):
        duration=max(0.0,float(duration))
        if kind == "heal":
            self.heal_flash=max(self.heal_flash,duration)
        elif kind == "energy":
            self.energy_flash=max(self.energy_flash,duration)

    # ---- daño: primero escudo, luego vida ----
    def take_damage(self, amount):
        if self.invuln > 0 or not self.alive:
            return False
        self.since_hit = 0.0
        self.invuln = 0.6
        self.hurt_flash = 0.25
        self.heal_flash = 0.0
        self.energy_flash = 0.0
        amount = max(0.0, float(amount) * getattr(self, "statue_damage_taken_mult", 1.0))
        left = amount
        if self.shield > 0:
            absorbed = min(self.shield, left)
            self.shield -= absorbed
            left -= absorbed
        if left > 0:
            self.hp = max(0, self.hp - int(math.ceil(left)))
        if self.hp <= 0:
            self.alive = False
        return True

    def update(self, sim, inp, dt):
        c = self.c
        self.since_hit += dt
        self.since_shot += dt
        self.invuln = max(0.0, self.invuln - dt)
        self.hurt_flash = max(0.0, self.hurt_flash - dt)
        self.heal_flash = max(0.0, self.heal_flash - dt)
        self.energy_flash = max(0.0, self.energy_flash - dt)
        self.noenergy_cd = max(0.0, self.noenergy_cd - dt)
        self.dash_cd = max(0.0, self.dash_cd - dt)
        self.ability_cd = max(0.0, self.ability_cd - dt)
        self.ability_buff = max(0.0, self.ability_buff - dt)
        self.ability_shield_fx = max(0.0, self.ability_shield_fx - dt)
        self.ability_shot_timer = max(0.0, self.ability_shot_timer - dt)
        self.melee_attack_timer = max(0.0, self.melee_attack_timer - dt)
        self.frozen = max(0.0, self.frozen - dt)
        for key in list(self.status_timers):
            self.status_timers[key] = max(0.0, self.status_timers[key] - dt)
            if self.status_timers[key] <= 0:
                self.status_timers.pop(key, None)
        if self.frozen > 0:
            self.status_timers["freeze"] = max(self.status_timers.get("freeze", 0.0), self.frozen)
        # regeneración de escudo y energía
        if self.since_hit > c.shield_regen_delay and self.shield < self.max_shield:
            self.shield = min(self.max_shield, self.shield + self.shield_regen_rate * dt)
        if self.since_shot > 0.6:
            self.energy = min(self.max_energy, self.energy + c.energy_regen * dt)
        # Apuntado: el personaje mira horizontalmente hacia el cursor,
        # independientemente de la dirección en la que se esté moviendo.
        self.aim = math.atan2(inp.aim_y - self.y, inp.aim_x - self.x)
        if abs(inp.aim_x - self.x) > 1:
            self.facing_x = 1 if inp.aim_x > self.x else -1
        if self.frozen > 0:
            self.is_moving = False
            self.rvx = self.rvy = 0.0
            return
        # movimiento: respuesta inmediata, sin aceleración
        mx, my = inp.move_x, inp.move_y
        n = math.hypot(mx, my)
        self.is_moving = n > 0.01
        if n > 0:
            mx, my = mx / n, my / n
            self.walk_time += dt
        if inp.ability_pressed:
            from .abilities import use_ability
            use_ability(sim)
        if inp.dash_pressed and self.dash_cd <= 0 and self.dash_left <= 0:
            self.dash_dir = (mx, my) if n > 0 else (math.cos(self.aim), math.sin(self.aim))
            self.dash_left = c.dash["duration"]
            self.dash_cd = c.dash["cooldown"]
            self.invuln = max(self.invuln, c.dash["duration"] + 0.08)
            sim.emit("dash", self.x, self.y)
        if self.dash_left > 0:
            self.dash_left -= dt
            vx, vy = self.dash_dir[0] * c.dash["speed"], self.dash_dir[1] * c.dash["speed"]
        else:
            speed_mult = 1.35 if self.ability_buff > 0 else 1.0
            vx, vy = mx * self.speed * speed_mult, my * self.speed * speed_mult
        # el retroceso decae rápido
        self.rvx *= max(0.0, 1 - 14 * dt)
        self.rvy *= max(0.0, 1 - 14 * dt)
        self.x, self.y = sim.move_actor(self.x, self.y, (vx + self.rvx) * dt, (vy + self.rvy) * dt, self.radius)
        try_fire(sim, self, inp, dt)
