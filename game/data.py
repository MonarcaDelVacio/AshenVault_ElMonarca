"""Carga de datos JSON. Las entidades de Fase 2 son datos, no código hardcodeado."""
import json, os, sys

def data_dir():
    base=getattr(sys,"_MEIPASS",None) or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base,"data")

def _load(name):
    with open(os.path.join(data_dir(),name+".json"),encoding="utf-8") as f:return json.load(f)

WEAPON_DEFAULTS={"name":"?","class":"pistol","rarity":"common","damage":5,"fire_interval":.3,"auto":False,"magazine":10,"reload_time":1.,"projectile_speed":400,"spread":0.,"recoil":0.,"damage_type":"physical","energy_cost":0,"pellets":1,"range":500,"pierce":0,"bounces":0,"projectile_radius":3,"max_magazines":3,"durability":1,"color":[255,255,255],"rarity_effect":"none"}
ENEMY_DEFAULTS={"ai":"melee","hp":20,"speed":80,"radius":10,"detect_range":600,"attack_range":30,"preferred_distance":200,"windup":.5,"recover":.3,"cooldown":1.,"damage":1,"hit_radius":36,"projectile_speed":200,"projectile_radius":5,"pellets":1,"fan_angle":0,"coins":1,"color":[200,80,80],"min_wave":1,"weight":1,"dodge_chance":0.10,"cover_chance":0.12,"emergency_shield_chance":0.10,"emergency_shield_duration":1.2,"stomp_interval":5.0,"stomp_radius":145.0}
BOSS_DEFAULTS={"ai":"ranged","hp":100,"speed":60,"radius":28,"detect_range":1200,"attack_range":900,"preferred_distance":250,"windup":.7,"recover":.3,"cooldown":1.2,"damage":3,"hit_radius":58,"projectile_speed":240,"projectile_radius":6,"pellets":1,"fan_angle":0,"coins":25,"color":[220,120,90]}
CHARACTER_DEFAULTS={"max_hp":6,"max_shield":5,"max_energy":100,"speed":170,"energy_regen":10,"shield_regen_delay":3.,"shield_regen_rate":.8,"damage_mult":1.,"crit_chance":.05,"radius":10,"color":[90,160,230],"dash":{"speed":480,"duration":.16,"cooldown":1.}}
RARITY_STATS={
    "common":{"damage":1.00,"fire_interval":1.00,"magazine":1.00,"projectile_speed":1.00},
    "uncommon":{"damage":1.08,"fire_interval":0.97,"magazine":1.05,"projectile_speed":1.03},
    "rare":{"damage":1.18,"fire_interval":0.94,"magazine":1.10,"projectile_speed":1.06},
    "epic":{"damage":1.30,"fire_interval":0.91,"magazine":1.15,"projectile_speed":1.10},
    "legendary":{"damage":1.45,"fire_interval":0.87,"magazine":1.20,"projectile_speed":1.15},
}
class Defn:
    def __init__(self,ident,raw,defaults):
        self.id=ident
        d=dict(defaults); d.update(raw); self.__dict__.update(d)
        if defaults is WEAPON_DEFAULTS:
            tier=RARITY_STATS.get(self.rarity,RARITY_STATS["common"])
            self.base_damage=float(self.damage)
            self.damage=round(self.damage*tier["damage"],3)
            self.fire_interval=round(max(0.04,self.fire_interval*tier["fire_interval"]),4)
            self.magazine=max(1,round(self.magazine*tier["magazine"]))
            self.projectile_speed=round(self.projectile_speed*tier["projectile_speed"],3)
            self.rarity_effect={
                "common":"none",
                "uncommon":"+8% daño / +5% cargador",
                "rare":"+18% daño / +6% velocidad de proyectil",
                "epic":"+30% daño / +15% cargador",
                "legendary":"+45% daño / +20% cargador"
            }.get(self.rarity,"none")
class GameData:
    def __init__(self):
        self.weapons={k:Defn(k,v,WEAPON_DEFAULTS) for k,v in _load("weapons").items()}
        self.enemies={k:Defn(k,v,ENEMY_DEFAULTS) for k,v in _load("enemies").items()}
        self.characters={k:Defn(k,v,CHARACTER_DEFAULTS) for k,v in _load("characters").items()}
        self.arenas=_load("arenas")
        self.biomes=_load("biomes"); self.enemy_variants=_load("enemy_variants"); self.synergies=_load("synergies"); self.biome_bosses={"ruins":"warden","forest":"thorn_matron","dungeon":"iron_judge","laboratory":"null_archon","volcanic":"pyre_colossus","final":"ashen_regent"}; self.rooms=_load("rooms"); self.chests=_load("chests"); self.modifiers=_load("modifiers"); self.items=_load("items"); self.shops=_load("shops"); self.bosses={k:Defn(k,v,BOSS_DEFAULTS) for k,v in _load("bosses").items()}
        self.validate()
    def validate(self):
        for c in self.characters.values():
            if c.start_weapon not in self.weapons:raise ValueError(f"Personaje {c.id}: arma inicial desconocida {c.start_weapon}")
            if not getattr(c, "ability", None) or not c.ability.get("name"): raise ValueError(f"Personaje {c.id}: habilidad inválida")
        for a_id,a in self.arenas.items():
            if a["biome"] not in self.biomes:raise ValueError(f"Arena {a_id}: bioma desconocido")
        missing=[]
        for biome_id,b in self.biomes.items():
            for eid in b.get("enemy_pool",[]):
                if eid not in self.enemies: missing.append(f"{biome_id}:{eid}")
        if missing: raise ValueError("Enemigos de bioma desconocidos: "+", ".join(missing))
        if len(self.weapons) < 50: raise ValueError("El arsenal debe contener al menos 50 armas")
        # Valida referencias a assets declaradas en los datos antes de iniciar una run.
        # Así un archivo renombrado/eliminado no queda como un fallo silencioso del renderer.
        root = os.path.dirname(data_dir())
        for wid, weapon in self.weapons.items():
            for field in ("weapon_sprite", "projectile_sprite"):
                asset = getattr(weapon, field, None)
                if not asset:
                    if field == "projectile_sprite" and getattr(weapon, "class", "") == "melee":
                        continue
                    raise ValueError(f"Arma {wid}: falta {field}")
                if not os.path.isfile(os.path.join(root, asset.replace("/", os.sep))):
                    raise ValueError(f"Arma {wid}: asset inexistente {asset}")
        for eid, enemy in self.enemies.items():
            sprite_set = getattr(enemy, "sprite_set", None)
            if sprite_set and not isinstance(sprite_set, str):
                raise ValueError(f"Enemigo {eid}: sprite_set inválido")
            asset = getattr(enemy, "projectile_asset_sheet", None)
            if asset and asset != "minigolem_rock" and not os.path.isfile(os.path.join(root, asset.replace("/", os.sep))):
                raise ValueError(f"Enemigo {eid}: projectile_asset_sheet inexistente {asset}")
        for biome_id, boss_id in self.biome_bosses.items():
            if biome_id not in self.biomes: raise ValueError(f"Bioma de jefe desconocido: {biome_id}")
            if boss_id not in self.bosses: raise ValueError(f"Jefe de bioma desconocido: {biome_id}:{boss_id}")
