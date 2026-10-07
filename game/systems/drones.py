"""Mira drone combat/support system extracted from Sim.

Sim remains the owner of world state; these helpers receive the facade so
existing collision, projectile and event contracts remain unchanged.
"""
import math

def spawn_drone(sim, angle=0.0):
    a=sim.player.ability
    radius=10.0
    desired_x=sim.player.x+math.cos(angle)*62.0
    desired_y=sim.player.y+math.sin(angle)*62.0
    spawn_x,spawn_y=sim._safe_drone_position(desired_x,desired_y,radius)
    drone={"x":spawn_x,"y":spawn_y,
           "angle":float(angle),"orbit":float(angle),"hp":float(a.get("drone_hp",18)),
           "max_hp":float(a.get("drone_hp",18)),"shot_cd":1.0,"burst_left":0,
           "burst_cd":0.0,"phase":sim.rng.random()*math.tau,"radius":radius,"flash":0.0,
           "vx":0.0,"vy":0.0,"strafe_sign":(-1 if len(sim.drones)%2 else 1)}
    sim.drones.append(drone)
    sim.player.drones=sim.drones
    return drone

def drone_collision(sim, x, y, radius):
    """True when a drone position overlaps any solid map/object hitbox."""
    if sim.arena.box_hits(x, y, radius):
        return True
    return bool(sim._world_collision(x, y, radius))

def safe_drone_position(sim, x, y, radius, avoid_player=True):
    """Finds the nearest free point for a drone without crossing a hitbox."""
    margin=float(radius)+1.0
    x=max(margin,min(sim.arena.width-margin,float(x)))
    y=max(margin,min(sim.arena.height-margin,float(y)))
    occupied=list(sim.drones)
    candidates=[(0.0,x,y)]
    # Spiral probes cover blocked walls/props near the requested formation slot.
    for ring in range(1,7):
        distance=ring*18.0
        for n in range(16):
            a=math.tau*n/16.0
            qx=x+math.cos(a)*distance
            qy=y+math.sin(a)*distance
            candidates.append((distance,qx,qy))
    for _,qx,qy in candidates:
        qx=max(margin,min(sim.arena.width-margin,qx))
        qy=max(margin,min(sim.arena.height-margin,qy))
        if sim._drone_collision(qx,qy,radius):
            continue
        if avoid_player and math.hypot(qx-sim.player.x,qy-sim.player.y)<54.0:
            continue
        if any(math.hypot(qx-d["x"],qy-d["y"]) < radius+float(d.get("radius",10.0))+12.0 for d in occupied):
            continue
        return qx,qy
    # Last resort: keep the drone at the player's side rather than inside a wall.
    for n in range(16):
        a=math.tau*n/16.0
        qx=sim.player.x+math.cos(a)*68.0
        qy=sim.player.y+math.sin(a)*68.0
        qx=max(margin,min(sim.arena.width-margin,qx))
        qy=max(margin,min(sim.arena.height-margin,qy))
        if not sim._drone_collision(qx,qy,radius):
            return qx,qy
    return sim.player.x,sim.player.y

def drone_path_clear(sim, x0, y0, x1, y1, radius):
    """Checks the actual drone hitbox along a short path, not just its endpoint."""
    distance=math.hypot(x1-x0,y1-y0)
    steps=max(1,int(distance/8.0))
    for i in range(1,steps+1):
        t=i/steps
        x=x0+(x1-x0)*t
        y=y0+(y1-y0)*t
        if sim._drone_collision(x,y,radius):
            return False
    return True

def drone_move(sim, drone, dx, dy):
    """Moves a drone while respecting walls, props, decorations and map bounds."""
    radius=float(drone.get("radius",10.0))
    x,y=drone["x"],drone["y"]
    nx,ny=sim.move_actor(x,y,dx,dy,radius)

    # Never allow a collision resolver or steering correction to push a drone
    # outside the playable rectangle.
    margin=radius+1.0
    nx=max(margin,min(sim.arena.width-margin,nx))
    ny=max(margin,min(sim.arena.height-margin,ny))

    if sim._drone_collision(nx,ny,radius):
        # Try sliding along either axis before giving up the movement.
        ax,ay=sim.move_actor(x,y,dx,0.0,radius)
        bx,by=sim.move_actor(ax,ay,0.0,dy,radius)
        candidates=[(ax,ay),(bx,by)]
        # Small lateral probes prevent a drone from repeatedly pressing
        # directly into the same corner.
        length=math.hypot(dx,dy)
        if length>0.001:
            ux,uy=dx/length,dy/length
            for side in (-1,1):
                lateral=radius*1.8
                px,py=sim.move_actor(x,y,dx-uy*lateral,dy+ux*lateral,radius)
                candidates.append((px,py))
        valid=[]
        for cx,cy in candidates:
            cx=max(margin,min(sim.arena.width-margin,cx))
            cy=max(margin,min(sim.arena.height-margin,cy))
            if not sim._drone_collision(cx,cy,radius):
                progress=math.hypot(cx-x,cy-y)
                valid.append((progress,cx,cy))
        if valid:
            _,nx,ny=max(valid,key=lambda item:item[0])
        else:
            nx,ny=x,y
    drone["x"],drone["y"]=nx,ny

def update_drones(sim,dt):
    if not sim.drones or not sim.player.alive:
        return
    p=sim.player
    kept=[]
    attack_interval=float(p.ability.get("drone_attack_interval",1.0))
    damage=float(p.ability.get("drone_damage_mult",1.0))*4.0*p.damage_mult
    soft_leash=270.0
    hard_leash=350.0

    for i,d in enumerate(sim.drones):
        d.setdefault("orbit_speed",0.28 if i%2==0 else -0.25)
        d.setdefault("orbit_radius",82.0)
        d.setdefault("idle_phase",sim.rng.random()*math.tau)
        d.setdefault("stuck_time",0.0)
        d.setdefault("repath_time",0.0)
        d.setdefault("avoid_x",0.0)
        d.setdefault("avoid_y",0.0)

        enemies=[e for e in sim.enemies if e.alive and e.spawn_delay<=0.2]
        nearest_enemy=min(
            enemies,
            key=lambda e:math.hypot(e.x-d["x"],e.y-d["y"]),
            default=None
        )
        in_combat=nearest_enemy is not None

        if not in_combat:
            # Idle drones continuously orbit and vary their radius/phase. This
            # prevents them from freezing at one point beside Mira.
            d["orbit"] += d["orbit_speed"]*dt
            d["idle_phase"] += dt*1.15
            radius=82.0 + math.sin(d["idle_phase"])*6.0
            # Evenly distribute multiple drones around Mira while preserving
            # their individual slow orbit direction.
            slot_offset=(math.tau/max(1,len(sim.drones)))*i
            angle=d["orbit"]+slot_offset
            target_x=p.x+math.cos(angle)*radius
            target_y=p.y+math.sin(angle)*radius*0.88
        else:
            ex,ey=nearest_enemy.x-d["x"],nearest_enemy.y-d["y"]
            ed=math.hypot(ex,ey) or 1.0
            # Maintain a combat ring around the enemy. Each drone gets a
            # different lateral offset so they do not occupy the same point.
            side=-1 if i%2 else 1
            px,py=-ey/ed*52.0*side,ex/ed*52.0*side
            target_x=nearest_enemy.x-ex/ed*150.0+px
            target_y=nearest_enemy.y-ey/ed*150.0+py
            # Slowly orbit the combat point rather than locking onto one
            # coordinate when the enemy is stationary.
            d["orbit"] += d["orbit_speed"]*dt*0.65
            target_x += math.cos(d["orbit"])*18.0
            target_y += math.sin(d["orbit"])*18.0

        # Hazard avoidance has priority over the local formation target.
        electric_hazards=[
            h for h in sim.hazards
            if h.get("dtype")=="electric" and h.get("life",0)>0
            and math.hypot(h["x"]-d["x"],h["y"]-d["y"])<105
        ]
        if electric_hazards:
            h=min(electric_hazards,key=lambda q:math.hypot(q["x"]-d["x"],q["y"]-d["y"]))
            hd=math.hypot(d["x"]-h["x"],d["y"]-h["y"]) or 1.0
            target_x=d["x"]+(d["x"]-h["x"])/hd*120.0
            target_y=d["y"]+(d["y"]-h["y"])/hd*120.0

        # Keep the formation close to Mira, but never directly on top of her.
        pdx,pdy=target_x-p.x,target_y-p.y
        pd=math.hypot(pdx,pdy)
        if pd>soft_leash:
            scale=soft_leash/max(pd,1.0)
            target_x=p.x+pdx*scale
            target_y=p.y+pdy*scale

        # Drone-to-drone separation. This is applied continuously, so the
        # formation remains readable even while all drones are following the
        # same enemy.
        sep_x=sep_y=0.0
        for j,other in enumerate(sim.drones):
            if other is d:
                continue
            ox,oy=other["x"]-d["x"],other["y"]-d["y"]
            od=math.hypot(ox,oy)
            min_dist=float(d.get("radius",10.0))+float(other.get("radius",10.0))+18.0
            if 0.001<od<min_dist:
                strength=(min_dist-od)/min_dist
                sep_x-=ox/od*strength*45.0
                sep_y-=oy/od*strength*45.0
        target_x+=sep_x*0.25
        target_y+=sep_y*0.25

        # Keep a physical gap from Mira hersim.
        relx,rely=d["x"]-p.x,d["y"]-p.y
        rd=math.hypot(relx,rely) or 1.0
        if rd<54.0:
            target_x+=relx/rd*(54.0-rd)
            target_y+=rely/rd*(54.0-rd)

        desired_x,desired_y=target_x-d["x"],target_y-d["y"]
        desired_dist=math.hypot(desired_x,desired_y)
        if desired_dist>3.0:
            desired_vx=desired_x/desired_dist*185.0
            desired_vy=desired_y/desired_dist*185.0
        else:
            desired_vx=desired_vy=0.0

        # Smooth steering avoids jitter when the target changes by a few pixels.
        accel=560.0
        blend=min(1.0,accel*dt/185.0)
        d["vx"] += (desired_vx-d["vx"])*blend
        d["vy"] += (desired_vy-d["vy"])*blend

        # Projectile avoidance.
        threats=[
            pr for pr in sim.pool.items
            if pr.active and pr.team==1
            and math.hypot(pr.x-d["x"],pr.y-d["y"])<78
        ]
        if threats:
            pr=min(threats,key=lambda q:math.hypot(q.x-d["x"],q.y-d["y"]))
            pv=math.hypot(pr.vx,pr.vy) or 1.0
            side=(-1 if i%2 else 1)
            d.setdefault("avoid_x",0.0); d.setdefault("avoid_y",0.0)
            d["avoid_x"] += (-pr.vy/pv)*side*38.0*dt
            d["avoid_y"] += (pr.vx/pv)*side*38.0*dt
        else:
            d["avoid_x"] *= max(0.0,1.0-5.0*dt)
            d["avoid_y"] *= max(0.0,1.0-5.0*dt)
        d["vx"] += d.get("avoid_x",0.0)
        d["vy"] += d.get("avoid_y",0.0)

        # If the direct route is blocked, probe several headings and choose
        # the one that makes real progress without entering a hitbox.
        move_dist=math.hypot(d["vx"],d["vy"])*dt
        if move_dist>0.01:
            base=math.atan2(d["vy"],d["vx"])
            direct_dx,direct_dy=d["vx"]*dt,d["vy"]*dt
            candidates=[]
            if sim._drone_path_clear(d["x"],d["y"],d["x"]+direct_dx,d["y"]+direct_dy,d["radius"]):
                candidates.append((2.0,direct_dx,direct_dy))
            for deg in (22,-22,45,-45,68,-68,90,-90,115,-115,145,-145,180):
                a=base+math.radians(deg)
                tx=d["x"]+math.cos(a)*move_dist
                ty=d["y"]+math.sin(a)*move_dist
                if not sim._drone_path_clear(d["x"],d["y"],tx,ty,d["radius"]):
                    continue
                alignment=math.cos(a-base)
                # Prefer headings toward the desired target, but accept a
                # lateral route when the direct route is blocked.
                score=alignment*1.8
                if not in_combat:
                    score+=math.cos(a-math.atan2(target_y-d["y"],target_x-d["x"]))*0.8
                candidates.append((score,math.cos(a)*move_dist,math.sin(a)*move_dist))
            if candidates:
                _,dx,dy=max(candidates,key=lambda item:item[0])
                sim._drone_move(d,dx,dy)
            else:
                d["stuck_time"] += dt
                d["vx"] *= 0.72
                d["vy"] *= 0.72
        else:
            d["stuck_time"]=max(0.0,d.get("stuck_time",0.0)-dt)

        # Hard leash and bounds are a final safety net after collision resolution.
        pdx,pdy=d["x"]-p.x,d["y"]-p.y
        pd=math.hypot(pdx,pdy)
        if pd>hard_leash:
            scale=hard_leash/max(pd,1.0)
            nx=p.x+pdx*scale
            ny=p.y+pdy*scale
            if not sim._drone_collision(nx,ny,d["radius"]):
                d["x"],d["y"]=nx,ny
            else:
                # Si Mira está junto a una pared, no fuerces al dron contra ella.
                # Sólo corregimos la distancia cuando el trayecto de retirada es libre.
                pull=min(32.0*dt,pd-hard_leash+8.0)
                qx=d["x"]-pdx/pd*pull; qy=d["y"]-pdy/pd*pull
                if sim._drone_path_clear(d["x"],d["y"],qx,qy,d["radius"]):
                    d["x"],d["y"]=qx,qy
                else:
                    d["vx"]*=0.35; d["vy"]*=0.35; d["stuck_time"]=0.0

        margin=d["radius"]+1.0
        d["x"]=max(margin,min(sim.arena.width-margin,d["x"]))
        d["y"]=max(margin,min(sim.arena.height-margin,d["y"]))

        d["phase"] += dt*1.6
        d["flash"]=max(0.0,float(d.get("flash",0.0))-dt)
        d["shot_cd"]=max(0.0,d["shot_cd"]-dt)
        d["burst_cd"]=max(0.0,d["burst_cd"]-dt)

        target=nearest_enemy
        if target is not None and d["shot_cd"]<=0:
            ang=math.atan2(target.y-d["y"],target.x-d["x"])
            # Los drones disparan balas convencionales, usando el mismo
            # proyectil físico del arsenal en lugar de una esfera de energía.
            sim.spawn_projectile(
                0,d["x"],d["y"],ang,620.0,damage,3.0,1.1,
                (205,220,235),"physical",0,0,False,
                "assets/projectiles/projectile_06.png",False,0,False,0,
                0.85,0.0
            )
            d["shot_cd"]=attack_interval
        kept.append(d)
    sim.drones=kept
    p.drones=sim.drones

def damage_drone(sim, drone, amount, sx=0.0, sy=0.0):
    if drone not in sim.drones:
        return False
    damage=min(float(amount),max(1.0,drone["max_hp"]*0.42))
    drone["hp"]-=damage
    drone["flash"]=0.25
    sim.emit("drone_hit",drone["x"],drone["y"],damage)
    if drone["hp"]<=0:
        sim.drones.remove(drone)
        sim.emit("drone_destroy",drone["x"],drone["y"])
    return True

