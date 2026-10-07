"""Hazard and expanding-wave simulation helpers extracted from Sim."""

import math


def update_hazards(sim, dt):
    for prop in sim.props:
        if prop.get("broken") and prop.get("fade", 0) > 0:
            prop["fade"] -= dt
    sim.props[:] = [p for p in sim.props if not p.get("broken") or p.get("fade", 0) > 0]

    for h in sim.hazards:
        h["life"] -= dt
        h["tick"] -= dt
        h["particle_timer"] -= dt
        if h["particle_timer"] <= 0 and h["life"] > 0.25:
            h["particle_timer"] = 0.09 if h["dtype"] == "electric" else 0.12
            angle = sim.rng.random() * math.tau
            radius = h["radius"] * math.sqrt(sim.rng.random())
            px = h["x"] + math.cos(angle) * radius
            py = h["y"] + math.sin(angle) * radius
            if h["dtype"] == "fire":
                color = sim.rng.choice([(255,75,35),(255,125,45),(255,185,70)])
            elif h["dtype"] == "poison":
                color = sim.rng.choice([(70,255,95),(110,230,75),(45,190,90)])
            else:
                color = sim.rng.choice([(110,225,255),(160,245,255),(75,185,255)])
            bolt = h["dtype"] == "electric"
            h.setdefault("particles", []).append({
                "x": px, "y": py, "dx": sim.rng.uniform(-10,10), "dy": sim.rng.uniform(-14,14),
                "life": sim.rng.uniform(0.22,0.55), "max_life": 0.55, "color": color, "bolt": bolt,
            })
        for particle in h.get("particles", []):
            particle["life"] -= dt
            particle["x"] += particle["dx"] * dt
            particle["y"] += particle["dy"] * dt
        h["particles"] = [particle for particle in h.get("particles", []) if particle["life"] > 0]
        if h["tick"] <= 0:
            h["tick"] = 0.65
            if math.hypot(sim.player.x-h["x"], sim.player.y-h["y"]) <= h["radius"]:
                if sim.player.take_damage(h["damage"], math.atan2(sim.player.y-h["y"], sim.player.x-h["x"])):
                    if h["dtype"] in ("fire", "poison"):
                        sim._apply_dot(sim.player, h["dtype"], 4.0, h["damage"])
                    else:
                        sim.player.set_status("electric", 1.3)
                    sim.on_player_hit(h["x"], h["y"], h["damage"])
            for e in sim.enemies:
                if e.alive and math.hypot(e.x-h["x"], e.y-h["y"]) <= h["radius"]:
                    e.hurt(h["damage"], math.atan2(e.y-h["y"], e.x-h["x"]))
                    if h["dtype"] in ("fire", "poison"):
                        sim._apply_dot(e, h["dtype"], 4.0, h["damage"])
            if h["dtype"] == "electric":
                for drone in list(sim.drones):
                    if math.hypot(drone["x"]-h["x"], drone["y"]-h["y"]) <= h["radius"]:
                        sim.damage_drone(drone, h["damage"], h["x"], h["y"])
    sim.hazards = [h for h in sim.hazards if h["life"] > 0]

    for wave in sim.wave_attacks:
        wave["life"] -= dt
        wave["_los_cache"] = {}
        wave["radius"] += wave["speed"] * dt
        if wave.get("max_radius") is not None and wave["radius"] >= wave["max_radius"]:
            wave["radius"] = wave["max_radius"]
            wave["life"] = min(wave["life"], 0.12)
        if wave.get("team", 1) == 0:
            for e in sim.enemies:
                if not e.alive or e.id in wave.setdefault("hit_ids", set()):
                    continue
                dist = math.hypot(e.x-wave["x"], e.y-wave["y"])
                if abs(dist-wave["radius"]) < max(12.0, e.radius+5):
                    tile = sim.arena.tile_of(e.x, e.y)
                    key = (int(tile[0]), int(tile[1]))
                    clear = wave["_los_cache"].get(key)
                    if clear is None:
                        clear = sim._wave_clear_to(wave["x"], wave["y"], e.x, e.y)
                        wave["_los_cache"][key] = clear
                    if not clear:
                        continue
                    if wave.get("effect") == "freeze":
                        sim._apply_freeze(e, wave.get("freeze_duration", 2.5))
                    else:
                        e.hurt(wave["damage"], math.atan2(e.y-wave["y"], e.x-wave["x"]))
                        if wave.get("stun", 0) > 0:
                            e.stunned = max(getattr(e, "stunned", 0.0), wave["stun"])
                            if wave.get("confusion", False):
                                e.confused = max(getattr(e, "confused", 0.0), wave["stun"])
                                sim.emit("enemy_confused", e.x, e.y, wave["stun"])
                    wave["hit_ids"].add(e.id)
                    sim.emit("enemy_hit", e.x, e.y, wave.get("color", (220,150,80)), wave.get("damage", 0), False)
        else:
            if not wave.get("hit") and abs(math.hypot(sim.player.x-wave["x"], sim.player.y-wave["y"])-wave["radius"]) < 16:
                if sim._wave_clear_to(wave["x"], wave["y"], sim.player.x, sim.player.y):
                    wave["hit"] = True
                    if sim.player.take_damage(wave["damage"], math.atan2(wave["y"]-sim.player.y, wave["x"]-sim.player.x)):
                        sim.on_player_hit(wave["x"], wave["y"], wave["damage"])
    sim.wave_attacks = [w for w in sim.wave_attacks if w["life"] > 0]
