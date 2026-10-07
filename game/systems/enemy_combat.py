"""Enemy attack execution extracted from Enemy without changing combat contracts.\n\nThe Enemy instance remains the state owner; this module only orchestrates\nmelee contact, projectile patterns, enemy weapon visuals and attack events.\n"""\nimport math\n\n\ndef _attack(self, sim, dist):
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
                    sim._apply_dot(p,dtype,4.0,d.damage) if dtype in ("fire","poison") else p.set_status("electric",2.4)
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
    sim.emit("enemy_shoot", self.x, self.y, pattern)\n