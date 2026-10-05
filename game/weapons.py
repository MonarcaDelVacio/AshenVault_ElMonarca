"""Estado de arma y lógica de disparo, incluidas armas arrojadizas con carga."""
import math
from .world import TILE


class WeaponState:
    def __init__(self, wdef):
        self.d = wdef
        self.ammo = wdef.magazine
        self.reserve_magazines = int(getattr(wdef, "max_magazines", 3))
        self.max_reserve_magazines = self.reserve_magazines
        self.durability = int(getattr(wdef, "durability", wdef.magazine))
        self.max_durability = int(getattr(wdef, "durability", wdef.magazine))
        self.cooldown = 0.0
        self.reload_left = 0.0
        self.charge_time = 0.0
        self.laser_active = False

    @property
    def reloading(self):
        return self.reload_left > 0

    def start_reload(self):
        if getattr(self.d, "class", "") == "melee":
            return False
        if self.reserve_magazines <= 0 or self.reloading or self.ammo >= self.d.magazine:
            return False
        self.reserve_magazines -= 1
        self.reload_left = self.d.reload_time
        return True

    def update(self, dt):
        """Devuelve True en el frame en que termina la recarga."""
        self.cooldown = max(0.0, self.cooldown - dt)
        if self.reload_left > 0:
            self.reload_left -= dt
            if self.reload_left <= 0:
                self.reload_left = 0.0
                self.ammo = self.d.magazine
                return True
        return False


def _fire_projectiles(sim, p, w, charge_ratio=0.0):
    d = w.d
    if w.ammo <= 0:
        if w.start_reload():
            sim.emit("reload_start", p.x, p.y)
        return False
    if p.energy < d.energy_cost:
        if p.noenergy_cd <= 0:
            sim.emit("no_energy", p.x, p.y)
            p.noenergy_cd = 0.4
        return False

    charge_ratio = max(0.0, min(1.0, charge_ratio))
    speed_mult = 1.0 + (getattr(d, "charge_speed_mult", 1.8) - 1.0) * charge_ratio
    range_mult = 1.0 + (getattr(d, "charge_range_mult", 2.0) - 1.0) * charge_ratio
    damage_mult = 1.0 + (getattr(d, "charge_damage_mult", 2.2) - 1.0) * charge_ratio
    w.ammo -= 1
    w.cooldown = d.fire_interval / max(0.1, getattr(p, "attack_speed_mult", 1.0))
    p.energy -= d.energy_cost
    p.since_shot = 0.0
    sim.stats["shots"] += 1
    mx = p.x + math.cos(p.aim) * (p.radius + 8)
    my = p.y + math.sin(p.aim) * (p.radius + 8)
    if sim.arena.point_solid(mx, my):
        mx, my = p.x, p.y
    rng = getattr(sim, "rng", None)
    uniform = rng.uniform if rng else __import__("random").uniform
    rand = rng.random if rng else __import__("random").random
    pellets = int(d.pellets or 1) + getattr(p, "bonus_projectiles", 0)
    explosive = bool(getattr(d, "explosive", False) or getattr(d, "class", "") == "launcher")
    # A charged bow/spear is a single heavier projectile; ordinary shotguns retain their pellet spread.
    if getattr(d, "charged_projectile", False):
        pellets = 1
    for _ in range(pellets):
        spread = d.spread
        if getattr(d, "class", "") == "shotgun":
            spread = max(spread, 24)
        a = p.aim + math.radians(uniform(-spread, spread))
        class_name = str(getattr(d, "class", "")).lower()
        statue_mult = getattr(p, "statue_melee_mult", 1.0) if class_name == "melee" else getattr(p, "statue_ranged_mult", 1.0)
        dmg = d.damage * p.damage_mult * damage_mult * statue_mult
        crit = rand() < p.crit_chance
        if crit:
            dmg *= 2 * getattr(p, "statue_crit_damage_mult", 1.0)
        speed = d.projectile_speed * speed_mult
        projectile_range = d.range * range_mult
        sprite = getattr(d, "projectile_sprite", None)
        # The thrown spear/bow visual travels with the projectile, oriented along its trajectory.
        sim.spawn_projectile(
            0, mx, my, a, speed, dmg, d.projectile_radius,
            projectile_range / speed if speed else 0.1, d.color, d.damage_type,
            d.pierce + getattr(p, "bonus_pierce", 0), d.bounces, crit, sprite,
            explosive, TILE * (getattr(d, "explosion_tiles", 3) / 2) if explosive else 0,
            bool(getattr(d, "stick_on_hit", False)),
            0.0,
            float(getattr(d, "projectile_visual_scale", 1.0)),
            float(getattr(d, "status_chance", 0.24 if getattr(d, "damage_type", "") in ("ice", "fire", "poison", "electric") else 0.0)),
            float(getattr(d, "ally_heal", 0.0)),
        )
    p.rvx -= math.cos(p.aim) * d.recoil
    p.rvy -= math.sin(p.aim) * d.recoil
    sim.emit("shoot", mx, my, p.aim, d.color)
    if getattr(d, "charged_projectile", False):
        sim.emit("charge_release", p.x, p.y, charge_ratio)
    if w.ammo <= 0 and w.start_reload():
        sim.emit("reload_start", p.x, p.y)
    return True


def try_fire(sim, p, inp, dt):
    w = p.weapon
    if w is None:
        if not inp.fire_pressed or getattr(p, "fist_cooldown", 0.0) > 0:
            return False
        p.fist_cooldown = 0.28 / max(0.1, getattr(p, "attack_speed_mult", 1.0))
        p.since_shot = 0.0
        sim.perform_fist_attack(p)
        sim.emit("melee_swing", p.x, p.y, p.aim, (205, 205, 205), 30.0)
        return True
    d = w.d
    if getattr(d, "laser_weapon", False):
        # El láser consume energía de forma continua. La primera línea aparece
        # al completar 1 s de carga y puede seguir creciendo hasta 3 s.
        if not inp.fire_held or w.reloading or w.cooldown > 0:
            if w.laser_active:
                w.laser_active = False
                sim.stop_player_laser()
            w.charge_time = 0.0
            return False
        if p.energy <= 0.01:
            if w.laser_active:
                w.laser_active = False
                sim.stop_player_laser()
            w.charge_time = 0.0
            if p.noenergy_cd <= 0:
                sim.emit("no_energy", p.x, p.y); p.noenergy_cd = 0.4
            return False
        p.since_shot=0.0
        w.charge_time = min(float(getattr(d, "laser_max_charge", 3.0)), w.charge_time + dt)
        if w.charge_time >= float(getattr(d, "laser_start_charge", 1.0)):
            w.laser_active = True
            sim.update_player_laser(w.charge_time, dt)
        return False
    finished = w.update(dt)
    if finished:
        sim.emit("reload_done", p.x, p.y)
    if inp.reload_pressed and w.start_reload():
        w.charge_time = 0.0
        sim.emit("reload_start", p.x, p.y)

    chargeable = bool(getattr(d, "charged_projectile", False))
    if chargeable:
        max_charge = max(0.1, float(getattr(d, "charge_max", 3.0)))
        if inp.fire_held and not w.reloading and w.cooldown <= 0 and w.ammo > 0:
            w.charge_time = min(max_charge, w.charge_time + dt)
            return False
        if w.charge_time > 0 and (inp.fire_released or not inp.fire_held):
            if w.cooldown > 0 or w.reloading:
                return False
            ratio = min(1.0, w.charge_time / max_charge)
            w.charge_time = 0.0
            return _fire_projectiles(sim, p, w, ratio)
        return False

    if inp.fire_pressed:
        p.fire_buffer = 0.12
    else:
        p.fire_buffer = max(0.0, p.fire_buffer - dt)
    want = inp.fire_held if d.auto else p.fire_buffer > 0
    if not want or w.cooldown > 0 or w.reloading:
        return False
    if getattr(d, "class", "") == "melee":
        if w.durability <= 0:
            return False
        p.fire_buffer = 0.0
        w.cooldown = d.fire_interval / max(0.1, getattr(p, "attack_speed_mult", 1.0))
        if d.energy_cost > 0:
            if p.energy < d.energy_cost:
                if p.noenergy_cd <= 0:
                    sim.emit("no_energy", p.x, p.y)
                    p.noenergy_cd = 0.4
                return False
            p.energy -= d.energy_cost
        p.since_shot = 0.0
        w.durability = max(0, w.durability - 1)
        w.ammo = w.durability
        sim.stats["shots"] += 1
        sim.perform_melee_attack(p, d)
        if w.durability <= 0:
            sim.break_weapon(p, w)
        # La defensa contra proyectiles existe únicamente durante el golpe real.
        # Apuntar por sí solo nunca activa esta protección.
        p.melee_attack_timer = max(0.08, min(0.18, float(getattr(d, "fire_interval", 0.25)) * 0.45))
        sim.emit("melee_swing", p.x, p.y, p.aim, d.color, d.range)
        return True
    p.fire_buffer = 0.0
    return _fire_projectiles(sim, p, w, 0.0)
