"""Partículas, números de daño y screenshake con límites fijos (rendimiento en PCs modestos)."""
import math
import random

MAX_PARTICLES = 700


class Fx:
    def __init__(self):
        self.particles = []   # [x,y,vx,vy,life,maxlife,size,color]
        self.texts = []       # [x,y,life,text,color]
        self.shake = 0.0
        self.flash = 0.0
        # Animaciones de combate basadas en sprites. Los PNG son opcionales:
        # si faltan, el renderer simplemente no dibuja la animacion.
        self.melee_slashes = []   # [x, y, angle, life, max_life, size]
        self.explosions = []      # [x, y, life, max_life, size]
        self.enemy_deaths = []    # [x, y, life, max_life, sprite_set, size, facing, variant_id]
        self.special_effects = [] # [kind, x, y, angle, life, max_life, size]

    def burst(self, x, y, color, n=8, speed=140, life=0.35, size=2.5, angle=None, arc=math.tau):
        room = MAX_PARTICLES - len(self.particles)
        for _ in range(min(n, max(0, room))):
            a = (angle if angle is not None else random.uniform(0, math.tau)) + random.uniform(-arc / 2, arc / 2)
            s = random.uniform(0.3, 1.0) * speed
            l = life * random.uniform(0.6, 1.2)
            self.particles.append([x, y, math.cos(a) * s, math.sin(a) * s, l, l, size * random.uniform(0.6, 1.2), color])

    def text(self, x, y, txt, color=(255, 255, 255)):
        if len(self.texts) < 40:
            self.texts.append([x + random.uniform(-6, 6), y - 8, 0.7, txt, color])

    def add_shake(self, amount):
        self.shake = min(8.0, self.shake + amount)

    def handle(self, ev):
        k = ev[0]
        if k == "shoot":
            _, x, y, a, c = ev
            self.burst(x, y, c, 3, 90, 0.1, 2, a, 0.6)
            self.add_shake(0.5)
        elif k == "enemy_hit":
            _, x, y, c, dmg, crit = ev
            self.burst(x, y, (255, 240, 200), 4, 110, 0.2, 2)
            self.text(x, y, str(int(dmg)), (255, 220, 60) if crit else (255, 255, 255))
        elif k == "enemy_die":
            _, x, y, c, *extra = ev
            self.burst(x, y, c, 18, 190, 0.5, 3.5)
            if extra and extra[0] and len(self.enemy_deaths) < 80:
                sprite_set = extra[0]
                size = float(extra[1]) if len(extra) > 1 else 70.0
                facing = float(extra[2]) if len(extra) > 2 else 0.0
                self.enemy_deaths.append([x, y, 0.0, 0.48, sprite_set, size, facing, extra[1] if len(extra) > 1 else None])
            self.add_shake(1.5)
        elif k == "player_hit":
            _, x, y, a = ev
            self.burst(x, y, (255, 70, 70), 14, 170, 0.4, 3)
            self.add_shake(5)
            self.flash = 0.35
        elif k == "player_die":
            _, x, y = ev
            self.burst(x, y, (255, 90, 90), 40, 260, 0.9, 4)
            self.add_shake(8)
        elif k in ("wall_hit", "bounce"):
            _, x, y, c = ev
            self.burst(x, y, c, 3, 70, 0.15, 1.5)
        elif k == "spawn":
            _, x, y = ev
            self.burst(x, y, (200, 120, 255), 10, 90, 0.5, 2.5)
        elif k == "dash":
            _, x, y = ev
            self.burst(x, y, (180, 220, 255), 8, 80, 0.25, 2.5)
        elif k == "explosion":
            _, x, y, radius, color = ev
            self.burst(x,y,color,42,260,0.65,4)
            self.burst(x,y,(255,235,180),18,170,0.35,5)
            # Animacion generica de explosion de 8 frames.
            if len(self.explosions) < 80:
                size = max(28.0, float(radius) * 2.0)
                self.explosions.append([x, y, 0.0, 0.40, size])
            self.add_shake(3.0)
        elif k == "boss_shockwave":
            _, x, y, radius, color = ev
            if not isinstance(color, (tuple, list)):
                color = (220, 105, 95)
            self.burst(x, y, tuple(color), 26, 150, 0.35, 2.5)
            self.add_shake(2.0)
        elif k == "miniboss_shockwave":
            _, x, y, radius, color = ev
            if not isinstance(color, (tuple, list)):
                color = (190, 110, 220)
            self.burst(x, y, tuple(color), 16, 105, 0.28, 2.0)
        elif k == "melee_swing":
            _, x, y, angle, color, weapon_range, *extra = ev
            # The six-frame slash is now the only melee visual. Size follows weapon
            # reach/power and actor rank; the source PNG faces right and is rotated here.
            power_scale = float(extra[0]) if extra else 1.0
            if len(self.melee_slashes) < 40:
                size = max(44.0, float(weapon_range) * 1.65) * max(0.75, power_scale)
                self.melee_slashes.append([x, y, angle, 0.0, 0.24, size])
            self.burst(x, y, color, 5, 80, 0.12, 1.5, angle, 1.0)
        elif k == "barrel_burst":
            _, x, y, dtype = ev
            color={"fire":(255,75,45),"poison":(80,230,100),"electric":(190,90,255)}.get(dtype,(255,180,90))
            self.burst(x,y,color,28,190,0.55,3.5)
            if len(self.explosions) < 80:
                self.explosions.append([x, y, 0.0, 0.40, 82.0])
            self.burst(x,y,(245,240,230),12,110,0.3,2)
            self.add_shake(1.5)
        elif k == "crate_break":
            _, x, y = ev
            self.burst(x,y,(190,135,80),16,150,0.45,3)
        elif k == "boss_stomp":
            _, x, y = ev
            self.burst(x,y,(255,110,45),34,240,0.65,4)
            self._special("tornado", x, y, 0.0, 0.58, 112.0)
            self.add_shake(5)
        elif k == "boss_summon_ring":
            _, x, y, phase = ev
            self._special("water", x, y, 0.0, 0.48, 118.0 + phase * 8.0)
        elif k == "boss_heavy_burst":
            _, x, y, phase = ev
            self._special("large_explosion", x, y, 0.0, 0.52, 92.0 + phase * 12.0)
        elif k == "boss_lance":
            _, x, y, phase = ev
            self._special("lightning", x, y, -math.pi / 2, 0.62, 118.0 + phase * 8.0)
        elif k == "boss_homing":
            _, x, y, phase, *extra = ev
            angle = float(extra[0]) if extra else 0.0
            self._special("arrow", x, y, angle, 0.34, 72.0 + phase * 5.0)
        elif k == "boss_phase":
            _, x, y, phase = ev
            self._special("large_explosion", x, y, 0.0, 0.56, 105.0 + phase * 10.0)
        elif k == "boss_shield":
            _, x, y, active = ev
            self.burst(x,y,(100,180,255),18,130,0.4,3)
        elif k == "chest_spawn":
            _, x, y, _ = ev
            self.burst(x, y, (255, 215, 110), 10, 70, 0.35, 2.5)
        elif k == "chest_open":
            _, x, y, _ = ev
            self.burst(x, y, (255, 230, 130), 28, 180, 0.65, 3.5)
            self.add_shake(1.0)
        elif k == "room_clear":
            _, room_id = ev
            self.text(480, 70, "SALA DESPEJADA", (120, 240, 170))
        elif k == "boss_spawn":
            _, x, y, name = ev
            self.burst(x, y, (210, 90, 255), 28, 150, 0.7, 3)
            self.text(x, y - 45, name, (230, 170, 255))
            self.add_shake(2)
        elif k == "boss_phase":
            _, x, y, phase = ev
            self.burst(x, y, (255, 180, 70), 22, 180, 0.45, 3)
            self.text(x, y - 38, "FASE %d" % phase, (255, 200, 100))
            self.add_shake(2)
        elif k == "victory_portal":
            _, x, y = ev
            self.burst(x, y, (100, 220, 255), 35, 170, 0.8, 3)
        elif k == "victory":
            self.burst(480, 270, (120, 240, 180), 70, 240, 1.0, 4)
            self.text(480, 180, "VICTORIA", (130, 255, 190))
        elif k in ("item_pickup", "weapon_pickup", "shop_purchase"):
            _, x, y, *_ = ev
            self.burst(x, y, (120, 220, 255), 10, 120, 0.35, 2.5)
        elif k.startswith("ability_"):
            _, x, y, *_ = ev
            self.burst(x, y, (180, 120, 255), 18, 130, 0.45, 3)

    def _special(self, kind, x, y, angle, duration, size):
        if len(self.special_effects) >= 36:
            return
        self.special_effects.append([kind, float(x), float(y), float(angle), 0.0, float(duration), float(size)])

    def update(self, dt):
        for effect in self.melee_slashes:
            effect[3] += dt
        self.melee_slashes = [e for e in self.melee_slashes if e[3] < e[4]]
        for effect in self.explosions:
            effect[2] += dt
        self.explosions = [e for e in self.explosions if e[2] < e[3]]
        for effect in self.enemy_deaths:
            effect[2] += dt
        self.enemy_deaths = [e for e in self.enemy_deaths if e[2] < e[3]]
        for effect in self.special_effects:
            effect[4] += dt
        self.special_effects = [e for e in self.special_effects if e[4] < e[5]]

        keep = []
        for p in self.particles:
            p[4] -= dt
            if p[4] > 0:
                p[0] += p[2] * dt
                p[1] += p[3] * dt
                p[2] *= max(0.0, 1 - 5 * dt)
                p[3] *= max(0.0, 1 - 5 * dt)
                keep.append(p)
        self.particles = keep
        for t in self.texts:
            t[2] -= dt
            t[1] -= 28 * dt
        self.texts = [t for t in self.texts if t[2] > 0]
        self.shake = max(0.0, self.shake - 18 * dt)
        self.flash = max(0.0, self.flash - dt)
