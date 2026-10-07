"""Enemy movement/navigation helpers extracted from Enemy.

The Enemy object remains the state owner; these functions preserve the
existing movement contract while isolating steering and obstacle avoidance.
"""
import math

def step(enemy, sim, ux, uy, speed, dt):
        ox, oy = enemy.x, enemy.y
        n = math.hypot(ux, uy) or 1.0
        ux, uy = ux / n, uy / n
        distance = max(0.0, float(speed) * float(dt))
        if enemy.d.ai == "flying":
            margin = float(enemy.radius) + 2.0
            enemy.x = max(margin, min(sim.arena.width - margin, enemy.x + ux * distance))
            enemy.y = max(margin, min(sim.arena.height - margin, enemy.y + uy * distance))
            return

        # Primer intento: movimiento normal con deslizamiento por la superficie.
        nx, ny = sim.move_actor(enemy.x, enemy.y, ux * distance, uy * distance, enemy.radius)
        moved = math.hypot(nx - ox, ny - oy)
        if moved >= distance * 0.42 or distance <= 0.01:
            enemy.x, enemy.y = nx, ny
            return

        # Si quedó atrapado contra una esquina/objeto, no insiste en la misma
        # dirección. Prueba desvíos angulares y elige el que más conserva el
        # rumbo original. Esto permite rodear cajas, columnas y esquinas.
        candidates = []
        side = 1 if getattr(enemy, "strafe", 1) >= 0 else -1
        for deg in (22, -22, 45, -45, 68, -68, 90, -90, 115, -115, 145, -145):
            a = math.atan2(uy, ux) + math.radians(deg)
            cx, cy = math.cos(a), math.sin(a)
            tx, ty = sim.move_actor(enemy.x, enemy.y, cx * distance, cy * distance, enemy.radius)
            progress = math.hypot(tx - ox, ty - oy)
            alignment = cx * ux + cy * uy
            lateral = (-uy) * cx + ux * cy
            clear = True
            if hasattr(sim, "_obstacle_clear_to"):
                clear = sim._obstacle_clear_to(enemy.x, enemy.y, tx, ty, enemy.radius)
            # A steering candidate that immediately intersects a physical
            # obstacle is not a useful escape route, even if collision sliding
            # produced a small amount of progress.
            if not clear:
                continue
            score = progress * (0.68 + 0.32 * max(0.0, alignment))
            score += max(0.0, lateral * side) * min(distance * 0.08, 3.0)
            candidates.append((score, progress, tx, ty))
        if candidates:
            _, best_progress, bx, by = max(candidates, key=lambda q: q[0])
            if best_progress > moved + 0.5:
                enemy.x, enemy.y = bx, by
                return

        enemy.x, enemy.y = nx, ny
        if moved < distance * 0.18:
            enemy.strafe *= -1

def chase(enemy, sim, dt, speed):
        p = sim.player
        if (sim._target_line_clear(enemy.x, enemy.y, p.x, p.y)
        if hasattr(sim, "_target_line_clear")
        else sim.arena.line_of_sight(enemy.x, enemy.y, p.x, p.y)):
            tx, ty = p.x, p.y
        else:
            step = sim.arena.best_step(sim.flow, enemy.x, enemy.y, enemy.radius)
            if step is not None and hasattr(sim, "_obstacle_clear_to"):
                if not sim._obstacle_clear_to(enemy.x, enemy.y, step[0], step[1], enemy.radius):
                    step = None
            tx, ty = step if step is not None else (p.x, p.y)
        dx, dy = tx - enemy.x, ty - enemy.y
        n = math.hypot(dx, dy) or 1
        sx = sy = 0.0
        for o in sim.enemies:
            if o is not enemy and o.alive:
                ex, ey = enemy.x - o.x, enemy.y - o.y
                desired = enemy.radius + o.radius + 7.0
                dd = math.hypot(ex, ey)
                if dd < desired:
                    inv = 1.0 / (dd or 1.0)
                    strength = (desired - dd) / desired
                    sx += ex * inv * strength
                    sy += ey * inv * strength
        # Separation is stronger near narrow passages so enemies do not
        # stack in a doorway while all pursuing the same target.
        separation_weight = 1.35 if abs(sx) + abs(sy) > 0.12 else 0.8
        ux, uy = dx / n + sx * separation_weight, dy / n + sy * separation_weight
        m = math.hypot(ux, uy) or 1
        enemy._step(sim, ux / m, uy / m, speed, dt)

