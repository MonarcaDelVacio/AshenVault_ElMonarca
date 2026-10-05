"""Proyectiles con object pooling (lista fija reutilizable, sin asignaciones por disparo)."""
import math


class Projectile:
    __slots__ = ("active", "team", "x", "y", "vx", "vy", "damage", "radius", "life", "color",
                 "dtype", "pierce", "bounces", "crit", "hit_ids", "sprite_key", "explosive", "explosion_radius",
                 "stick_on_hit", "stuck", "stuck_timer", "stuck_angle", "stuck_enemy_id", "stuck_offset_x", "stuck_offset_y", "age",
                 "homing", "visual_scale", "status_chance")

    def __init__(self):
        self.active = False
        self.hit_ids = set()
        self.age = 0.0


class ProjectilePool:
    def __init__(self, size=600):
        self.items = [Projectile() for _ in range(size)]
        self._cursor = 0

    def spawn(self, team, x, y, angle, speed, damage, radius, life, color, dtype="physical",
              pierce=0, bounces=0, crit=False, sprite_key=None, explosive=False, explosion_radius=0,
              stick_on_hit=False, homing=0.0, visual_scale=1.0, status_chance=0.0):
        n = len(self.items)
        for i in range(n):
            p = self.items[(self._cursor + i) % n]
            if not p.active:
                self._cursor = (self._cursor + i + 1) % n
                break
        else:
            return None  # pool lleno: se descarta
        p.active = True
        p.team, p.x, p.y = team, x, y
        p.vx, p.vy = math.cos(angle) * speed, math.sin(angle) * speed
        p.damage, p.radius, p.life, p.color = damage, radius, life, color
        p.dtype, p.pierce, p.bounces, p.crit = dtype, pierce, bounces, crit
        p.sprite_key = sprite_key
        p.explosive = bool(explosive)
        p.explosion_radius = float(explosion_radius or 0)
        p.stick_on_hit = bool(stick_on_hit)
        p.stuck = False
        p.stuck_timer = 0.0
        p.stuck_angle = angle
        p.stuck_enemy_id = None
        p.stuck_offset_x = p.stuck_offset_y = 0.0
        p.age = 0.0
        p.homing = float(homing or 0.0)
        p.visual_scale = max(0.55, float(visual_scale or 1.0))
        p.status_chance = max(0.0, min(1.0, float(status_chance or 0.0)))
        p.hit_ids.clear()
        return p

    def clear(self):
        for p in self.items:
            p.active = False
