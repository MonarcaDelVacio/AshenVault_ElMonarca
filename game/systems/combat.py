"""Combat simulation helpers extracted from Sim.

The functions intentionally retain Sim as their state owner.  This keeps the
existing combat contracts while making projectile, melee, explosive, and laser
logic independently testable.
"""
import math
from ..world import TILE

def spawn_projectile(sim,*a):return sim.pool.spawn(*a)


def _damage_props(sim, x, y, damage, explosive=False, color=None):
        for prop in sim.props:
            if prop.get("broken"): continue
            provider=getattr(sim, "decoration_collider_provider", None)
            hit=False
            if provider is not None and hasattr(provider,"prop_collider"):
                shape=provider.prop_collider(prop)
                if shape:
                    cx,cy,rx,ry=shape
                    dx=(x-cx)/max(1.0,rx+5); dy=(y-cy)/max(1.0,ry+5); hit=dx*dx+dy*dy<=1.0
                    if not hit:
                        continue
            if hit or math.hypot(x-prop["x"],y-prop["y"]) <= prop.get("radius",24)+5:
                if explosive:
                    sim._break_prop(prop,color)
                else:
                    prop["hp"]-=max(1,damage/8.0)
                    if prop["hp"]<=0: sim._break_prop(prop,color)
                return True
        return False


def perform_fist_attack(sim, p):
        reach=30.0+p.radius; arc=1.9; damage=max(1.0,1.5*p.damage_mult)
        for e in sim.enemies:
            if not e.alive: continue
            dx,dy=e.x-p.x,e.y-p.y; dist=math.hypot(dx,dy)
            if dist>reach: continue
            da=(math.atan2(dy,dx)-p.aim+math.pi)%(2*math.pi)-math.pi
            if abs(da)>arc*0.5: continue
            if sim._damage_shield(e,damage,math.atan2(p.y-e.y,p.x-e.x),"melee"): continue
            e.hurt(damage,p.aim); e.kx += math.cos(p.aim)*70.0; e.ky += math.sin(p.aim)*70.0
            sim.emit("enemy_hit",e.x,e.y,(205,205,205),damage,False)
        for prop in sim.props:
            if prop.get("broken"): continue
            dx,dy=prop["x"]-p.x,prop["y"]-p.y; dist=math.hypot(dx,dy)
            if dist<=reach+prop.get("radius",24):
                da=(math.atan2(dy,dx)-p.aim+math.pi)%(2*math.pi)-math.pi
                if abs(da)<=arc*0.55:
                    prop["hp"]-=max(1.0,damage/8.0)
                    if prop["hp"]<=0:sim._break_prop(prop,(205,205,205))


def perform_melee_attack(sim, p, d):
        # El hitbox cubre toda la zona visible del corte, con margen de seguridad.
        reach=max(float(d.range)+p.radius, float(d.range)*1.20+p.radius)
        arc=max(float(getattr(d,"melee_arc",1.2)), 1.80)
        hit=0
        for e in sim.enemies:
            if not e.alive: continue
            dx,dy=e.x-p.x,e.y-p.y; dist=math.hypot(dx,dy)
            if dist <= reach:
                da=math.atan2(dy,dx)-p.aim
                da=(da+math.pi)%(2*math.pi)-math.pi
                if abs(da) <= arc*0.5:
                    raw_damage = d.damage * getattr(getattr(p, "weapon", None), "damage_mult", 1.0) * p.damage_mult * getattr(p, "statue_melee_mult", 1.0)
                    is_boss = getattr(e, "is_boss", False) or getattr(e, "is_miniboss", False)
                    damage_cap = e.max_hp * (0.55 if not is_boss else 0.18)
                    damage = min(raw_damage, max(1.0, damage_cap))
                    if sim._damage_shield(e, damage, math.atan2(p.y - e.y, p.x - e.x), "melee"):
                        hit += 1
                        continue
                    e.hurt(damage, p.aim)
                    level = max(1, int(getattr(d, "melee_level", 1)))
                    knockback = 105.0 + level * 24.0
                    e.kx += math.cos(p.aim) * knockback
                    e.ky += math.sin(p.aim) * knockback
                    status_type = getattr(d, "damage_type", "physical")
                    status_chance = float(getattr(d, "status_chance", 0.24 if status_type in ("ice","fire","poison","electric") else 0.0))
                    if status_type == "ice" and sim.rng.random() < status_chance:
                        sim._apply_freeze(e, damage)
                    elif status_type in ("fire","poison","electric") and sim.rng.random() < status_chance:
                        sim._apply_dot(e,status_type,4.0,damage)
                    hit += 1
                    sim.emit("enemy_hit",e.x,e.y,d.color,damage,False)
        for prop in sim.props:
            if prop.get("broken"): continue
            dx,dy=prop["x"]-p.x,prop["y"]-p.y; dist=math.hypot(dx,dy)
            if dist <= reach+prop.get("radius",24):
                da=(math.atan2(dy,dx)-p.aim+math.pi)%(2*math.pi)-math.pi
                if abs(da)<=arc*0.6:
                    prop["hp"]-=max(1.0,d.damage/8.0)
                    if prop["hp"]<=0: sim._break_prop(prop,d.color)
        if hit: sim.emit("melee_hit",p.x,p.y,hit)


def _update_projectiles(sim,dt):
        arena,p=sim.arena,sim.player
        for pr in sim.pool.items:
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
                    target = next((e for e in sim.enemies if e.id == pr.stuck_enemy_id and e.alive), None)
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
                        sim.emit("bounce",pr.x,pr.y,pr.color);continue
                    if pr.explosive:
                        sim._explode_projectile(pr)
                    else:
                        # El impacto contra geometría del escenario nunca debe dejar
                        # el proyectil pegado durante segundos. stick_on_hit se reserva
                        # para impactos contra enemigos.
                        pr.active=False
                    sim.emit("wall_hit",pr.x,pr.y,pr.color);break
                pr.x,pr.y=nx,ny
                hit_prop=sim._damage_props(pr.x,pr.y,pr.damage,pr.explosive,pr.color)
                if hit_prop:
                    if pr.explosive: sim._explode_projectile(pr)
                    else: pr.active=False
                    break
                # Las decoraciones del escenario tienen hitbox físico; un proyectil
                # no puede atravesar una roca, banco, fuente, estatua u hoguera.
                if sim._decoration_collision(pr.x,pr.y,pr.radius):
                    if pr.explosive: sim._explode_projectile(pr)
                    else: pr.active=False
                    sim.emit("decoration_hit",pr.x,pr.y,pr.color)
                    break
                if pr.team==0:
                    if pr.ally_heal > 0 and sim.allies:
                        healed=False
                        for ally in sim.allies:
                            if getattr(ally,"alive",True) and math.hypot(pr.x-ally.x,pr.y-ally.y)<pr.radius+getattr(ally,"radius",10):
                                ally.hp=min(ally.max_hp,ally.hp+pr.ally_heal)
                                sim.emit("ally_heal",ally.x,ally.y,pr.ally_heal)
                                pr.active=False; healed=True; break
                        if healed: break
                    if sim._hit_enemies(pr):break
                else:
                    w=p.weapon
                    # An empty inventory slot is a valid fists state. It cannot
                    # intercept projectiles because there is no weapon hitbox.
                    if w is None:
                        if math.hypot(pr.x-p.x,pr.y-p.y)<pr.radius+p.radius-2:
                            if pr.explosive:
                                sim._explode_projectile(pr)
                            elif p.take_damage(pr.damage, math.atan2(-pr.vy,-pr.vx)):
                                sim.on_player_hit(pr.x-pr.vx,pr.y-pr.vy,pr.damage)
                                if pr.dtype == "ice":
                                    sim._apply_freeze(p, pr.damage)
                                    p.set_status("freeze", 1.6)
                                elif pr.dtype in ("fire","poison"):
                                    sim._apply_dot(p,pr.dtype,4.0,pr.damage)
                                elif pr.dtype == "electric":
                                    p.set_status("electric",2.4)
                                pr.active=False
                        break
                    w=w.d
                    # Un arma cuerpo a cuerpo solo puede interceptar a projectile
                    # durante la ventana activa del golpe. Apuntar no tiene efecto.
                    if getattr(w,"class","") == "melee" and p.melee_attack_timer > 0:
                        dist=math.hypot(pr.x-p.x,pr.y-p.y)
                        da=math.atan2(pr.y-p.y,pr.x-p.x)-p.aim
                        da=(da+math.pi)%(2*math.pi)-math.pi
                        hit_radius=w.range
                        if dist <= hit_radius + pr.radius and abs(da) <= getattr(w,"melee_arc",1.2)*0.5:
                            pr.active=False; sim.emit("projectile_block",pr.x,pr.y,w.color); continue
                    drone_hit=next((dr for dr in sim.drones if math.hypot(pr.x-dr["x"],pr.y-dr["y"]) < pr.radius+dr["radius"]),None)
                    if drone_hit is not None:
                        sim.damage_drone(drone_hit,pr.damage,pr.x-pr.vx,pr.y-pr.vy)
                        pr.active=False
                        break
                    if math.hypot(pr.x-p.x,pr.y-p.y)<pr.radius+p.radius-2:
                        if pr.explosive:
                            sim._explode_projectile(pr)
                        elif p.take_damage(pr.damage, math.atan2(-pr.vy,-pr.vx)):
                            sim.on_player_hit(pr.x-pr.vx,pr.y-pr.vy,pr.damage)
                            if pr.dtype == "ice":
                                sim._apply_freeze(p, pr.damage)
                                p.set_status("freeze", 1.6)
                            elif pr.dtype in ("fire","poison"):
                                sim._apply_dot(p,pr.dtype,4.0,pr.damage)
                            elif pr.dtype == "electric":
                                p.set_status("electric",2.4)
                            pr.active=False
                        break

def _explode_projectile(sim, pr):
        """Applies explosive damage throughout the configured radius, blocked by obstacles."""
        radius=max(TILE,getattr(pr,"explosion_radius",0) or TILE*1.5)
        for prop in sim.props:
            if not prop.get("broken") and math.hypot(prop["x"]-pr.x,prop["y"]-pr.y)<=radius+prop.get("radius",24):
                sim._break_prop(prop,pr.color)
        if pr.team==1 and math.hypot(sim.player.x-pr.x,sim.player.y-pr.y)<=radius+sim.player.radius:
            if sim._obstacle_clear_to(pr.x,pr.y,sim.player.x,sim.player.y,sim.player.radius):
                if sim.player.take_damage(pr.damage,math.atan2(sim.player.y-pr.y,sim.player.x-pr.x)):
                    sim.on_player_hit(pr.x,pr.y,pr.damage)
        for enemy in sim.enemies:
            if not enemy.alive or enemy.spawn_delay>.3: continue
            if math.hypot(enemy.x-pr.x,enemy.y-pr.y)<=radius+enemy.radius and sim._obstacle_clear_to(pr.x,pr.y,enemy.x,enemy.y,enemy.radius):
                from_explosion=math.atan2(pr.y-enemy.y,pr.x-enemy.x)
                if sim._damage_shield(enemy,pr.damage,from_explosion,"projectile"): continue
                enemy.hurt(pr.damage,math.atan2(enemy.y-pr.y,enemy.x-pr.x))
                if pr.team==0 and pr.status_chance>0 and sim.rng.random()<pr.status_chance:
                    if pr.dtype=="ice": sim._apply_freeze(enemy,pr.damage)
                    elif pr.dtype in ("fire","poison"): sim._apply_dot(enemy,pr.dtype,4.0,pr.damage)
                sim.emit("enemy_hit",enemy.x,enemy.y,pr.color,pr.damage,pr.crit)
        sim.emit("explosion",pr.x,pr.y,radius,pr.color)
        pr.active=False


def _hit_enemies(sim,pr):
        for e in sim.enemies:
            if not e.alive or e.id in pr.hit_ids or e.spawn_delay>.3:continue
            if math.hypot(pr.x-e.x,pr.y-e.y)<pr.radius+e.radius:
                if getattr(e,"shield_active",False):
                    sim.emit("projectile_block",e.x,e.y,(120,190,255)); pr.active=False; return True
                incoming=math.atan2(pr.vy,pr.vx)
                from_projectile=(incoming+math.pi)%(2*math.pi)
                if sim._damage_shield(e, pr.damage, from_projectile, "projectile"):
                    pr.active=False
                    return True
                if pr.explosive:
                    sim._explode_projectile(pr)
                    return True
                e.hurt(pr.damage,math.atan2(pr.vy,pr.vx))
                if pr.status_chance > 0.0 and sim.rng.random() < pr.status_chance:
                    if pr.dtype == "ice":
                        sim._apply_freeze(e, pr.damage)
                    elif pr.dtype in ("fire","poison","electric"):
                        sim._apply_dot(e,pr.dtype,4.0,pr.damage)
                sim.emit("enemy_hit",pr.x,pr.y,pr.color,pr.damage,pr.crit);pr.hit_ids.add(e.id)
                if pr.stick_on_hit:
                    pr.stuck = True; pr.stuck_timer = 3.0; pr.stuck_angle = math.atan2(pr.vy, pr.vx)
                    pr.stuck_enemy_id = e.id; pr.stuck_offset_x = pr.x - e.x; pr.stuck_offset_y = pr.y - e.y
                    pr.vx = pr.vy = 0.0
                    return True
                if pr.pierce>0:pr.pierce-=1;return False
                pr.active=False;return True
        return False

def stop_player_laser(sim):
        sim.lasers=[l for l in sim.lasers if l.get("owner") is not sim.player]
        if sim.player.weapon is not None:
            sim.player.weapon.laser_active=False


def update_player_laser(sim, charge_time, dt):
        w=sim.player.weapon
        if w is None:
            sim.stop_player_laser()
            return
        d=w.d
        # Energy is drained only while the visible beam is active.
        drain=float(getattr(d,"laser_energy_per_second",18.0))*dt
        sim.player.energy=max(0.0,sim.player.energy-drain)
        sim.player.since_shot=0.0
        if sim.player.energy <= 0.0:
            w.laser_active=False
            sim.stop_player_laser()
            return
        existing=next((l for l in sim.lasers if l.get("owner") is sim.player),None)
        if existing is None:
            existing={"owner":sim.player,"team":0,"angle":sim.player.aim,"charge":charge_time,
                      "duration":0.0,"tick":0.0,"color":tuple(getattr(d,"color",(120,220,255))),
                      "damage":float(getattr(d,"laser_damage",13.5))*sim.player.damage_mult,
                      "width":float(getattr(d,"laser_width",2.0)),"base_width":float(getattr(d,"laser_width",2.0)),"max_width":float(getattr(d,"laser_max_width",14.0)),
                      "range":float(getattr(d,"laser_range",760.0)),"explosion_radius":float(getattr(d,"laser_explosion_radius",26.0)),"travel":0.0,"travel_speed":2600.0}
            sim.lasers.append(existing)
            sim.emit("laser_start",sim.player.x,sim.player.y,sim.player.aim,existing["color"])
        existing["angle"]=sim.player.aim; existing["charge"]=min(3.0,float(charge_time)); existing["duration"]=0.0


def start_enemy_laser(sim, owner, angle, duration=2.2, color=None, damage=14.0, width=2.0, max_width=12.0, range_=760.0, explosion_radius=24.0):
        # Todos los rayos tienen un telegráfico de carga antes de que exista el
        # hitbox del haz. Esto permite leer el ataque y buscar cobertura.
        charge_duration = 1.0
        sim.lasers.append({"owner":owner,"team":1,"angle":angle,"charge":0.0,
                            "charge_left":charge_duration,"charge_duration":charge_duration,
                            "duration":float(duration),"tick":0.0,
                            "color":tuple(color or getattr(owner.d,"color",(255,100,100))),"damage":float(damage),
                            "width":float(width),"base_width":float(width),"max_width":float(max_width),"range":float(range_),
                            "explosion_radius":float(explosion_radius),"travel":0.0,"travel_speed":620.0,
                            "turn_speed":1.65,"beam_elapsed":0.0})
        sim.emit("laser_start",owner.x,owner.y,angle,tuple(color or getattr(owner.d,"color",(255,100,100))))


def _update_lasers(sim,dt):
        active=[]
        for laser in sim.lasers:
            owner=laser.get("owner")
            if owner is None or not getattr(owner,"alive",False): continue
            if laser.get("team")==0:
                if not getattr(owner.weapon,"laser_active",False): continue
                laser["angle"]=owner.aim
                laser["charge"]=min(3.0,float(owner.weapon.charge_time))
            else:
                target_angle=getattr(owner,"facing",laser.get("angle",0.0))
                current=float(laser.get("angle",target_angle))
                delta=(target_angle-current+math.pi)%(2*math.pi)-math.pi
                max_turn=float(laser.get("turn_speed",1.65))*dt
                laser["angle"]=current+max(-max_turn,min(max_turn,delta))
                charge_left=float(laser.get("charge_left",0.0))
                if charge_left > 0.0:
                    charge_left=max(0.0,charge_left-dt)
                    laser["charge_left"]=charge_left
                    duration=float(laser.get("charge_duration",1.0))
                    laser["charge"]=min(1.0,1.0-charge_left/max(0.001,duration))
                    laser["travel"]=0.0
                    active.append(laser)
                    continue
                laser["beam_elapsed"]=float(laser.get("beam_elapsed",0.0))+dt
                laser["charge"]=min(3.0,1.0+laser["beam_elapsed"]/1.0)
                laser["duration"]-=dt
                if laser["duration"]<=0: continue
            laser["tick"]=max(0.0,laser.get("tick",0.0)-dt)
            laser["travel"]=min(float(laser.get("range",760.0)),float(laser.get("travel",0.0))+float(laser.get("travel_speed",620.0))*dt)
            charge=max(1.0,min(3.0,float(laser.get("charge",1.0))))
            base_width=laser.get("base_width",laser.get("width",2.0))
            laser["width"]=base_width+(charge-1.0)/2.0*max(0.0,laser.get("max_width",12.0)-base_width)
            sim._laser_hit_target(laser,dt)
            active.append(laser)
        sim.lasers=active


def _ray_circle_hit_distance(ox, oy, ux, uy, cx, cy, radius):
        """Distance from a ray origin to the first intersection with a circle."""
        dx, dy = cx - ox, cy - oy
        projection = dx * ux + dy * uy
        if projection < 0.0:
            return None
        perpendicular_sq = dx * dx + dy * dy - projection * projection
        radius_sq = radius * radius
        if perpendicular_sq > radius_sq:
            return None
        offset = math.sqrt(max(0.0, radius_sq - perpendicular_sq))
        distance = projection - offset
        if distance < 0.0:
            distance = projection + offset
        return distance if distance >= 0.0 else None


def _laser_hit_target(sim, laser, dt):
        owner=laser["owner"]; angle=laser["angle"]; ux,uy=math.cos(angle),math.sin(angle)
        max_range=laser["range"]; width=laser["width"]
        # Geometry is still sampled at the existing 6 px resolution so wall,
        # prop and PNG-decoration collision semantics remain unchanged. Actor
        # intersection is solved analytically once per target instead of testing
        # every target at every sample point.
        length=max_range; hit_enemy=None; hit_point=None; blocked=False
        steps=max(1,int(max_range/6))
        for i in range(1,steps+1):
            d=i*max_range/steps; x=owner.x+ux*d; y=owner.y+uy*d
            if sim.arena.point_solid(x,y) or sim._crate_collision(x,y,width) or sim._decoration_collision(x,y,width):
                length=d; hit_point=(x,y); blocked=True; break
        if laser["team"]==0:
            candidates=(e for e in sim.enemies if e.alive and e.spawn_delay<=0 and e is not owner)
        else:
            candidates=(sim.player,) if sim.player.alive and sim.player is not owner else ()
        actor_length=max_range
        for target in candidates:
            hit_radius=float(getattr(target,"radius",0.0))+width*0.75
            distance=_ray_circle_hit_distance(owner.x,owner.y,ux,uy,target.x,target.y,hit_radius)
            if distance is not None and distance <= max_range and distance < actor_length:
                actor_length=distance
                hit_enemy=target
        if hit_enemy is not None and actor_length < length:
            length=actor_length
            hit_point=(owner.x+ux*length,owner.y+uy*length)
            blocked=True
        if hit_point is None:
            hit_point=(owner.x+ux*length,owner.y+uy*length)
        if blocked and laser["tick"]<=0 and dt>0.0 and float(laser.get("travel",length)) >= length-8.0:
            if hit_enemy is not None:
                if laser["team"]==0:
                    damage=min(laser["damage"],hit_enemy.max_hp*(0.24 if getattr(hit_enemy,"is_boss",False) else 0.55))
                    if not sim._damage_shield(hit_enemy,damage,math.atan2(owner.y-hit_enemy.y,owner.x-hit_enemy.x),"laser"):
                        hit_enemy.hurt(damage,angle)
                        sim.emit("enemy_hit",hit_enemy.x,hit_enemy.y,laser["color"],damage,False)
                else:
                    if sim.player.take_damage(laser["damage"], laser["angle"]+math.pi): sim.on_player_hit(owner.x,owner.y,laser["damage"])
            sim.emit("laser_impact",hit_point[0],hit_point[1],laser["color"],laser["explosion_radius"])
            laser["tick"]=0.12
        visible_length=min(length,float(laser.get("travel",length)))
        visible_point=(owner.x+ux*visible_length,owner.y+uy*visible_length)
        laser["_render_length"]=visible_length
        laser["_render_point"]=visible_point
        return visible_length,visible_point,hit_enemy
