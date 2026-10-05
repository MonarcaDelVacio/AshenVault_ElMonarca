"""Guardado local y progresion permanente de Ashen Vault."""
import json, os

# Compatibilidad: las partidas existentes pueden conservar "fullscreen": False.
DEFAULT = {
    "version": 5,
    "settings": {"effects_volume": 0.6, "music_volume": 0.6, "fullscreen": True, "mouse_sensitivity": 1.0, "keys": {"up":"w","down":"s","left":"a","right":"d","dash":"space","reload":"r","pause":"escape","ability":"q","map":"m"}},
    "unlocked_characters": ["soldier","medic","vanguard","pyromancer","striker","engineer"],
    "unlocked_weapons": ["plasma_pistol"],
    "meta_currency": 0,
    "upgrades": {"vitality":0,"shield":0,"damage":0,"speed":0,"energy":0,"shield_regen":0},
    "character_progress": {
        "soldier":{"level":1,"xp":0,"upgrades":{}}, "medic":{"level":1,"xp":0,"upgrades":{}},
        "vanguard":{"level":1,"xp":0,"upgrades":{}}, "pyromancer":{"level":1,"xp":0,"upgrades":{}},
        "striker":{"level":1,"xp":0,"upgrades":{}}, "engineer":{"level":1,"xp":0,"upgrades":{}}
    },
    "stats": {"runs":0,"kills":0,"best_wave":0,"total_coins":0,"deaths":0,"purchases":0,"abilities":0,"bosses_defeated":0,"meta_earned":0},
}

# Cada personaje tiene un arbol diferente. Los niveles son permanentes y se compran
# con fragmentos; la experiencia de las partidas solo sirve para subir el nivel.
CHARACTER_UPGRADES = {
    "soldier": {
        "max_hp":{"name":"Blindaje vital","description":"+1 vida maxima","base_cost":18,"max":8},
        "shield":{"name":"Escudo reforzado","description":"+1 escudo maximo","base_cost":20,"max":8},
        "damage":{"name":"Municion militar","description":"+4% dano total","base_cost":24,"max":8},
        "ability":{"name":"Bastion mejorado","description":"+1 escudo recuperado con Bastion","base_cost":28,"max":8},
    },
    "medic": {
        "max_hp":{"name":"Resistencia medica","description":"+1 vida maxima","base_cost":18,"max":8},
        "energy":{"name":"Reserva medica","description":"+10 energia maxima","base_cost":20,"max":8},
        "speed":{"name":"Movilidad de emergencia","description":"+5 velocidad","base_cost":22,"max":8},
        "ability":{"name":"Reanimacion avanzada","description":"+1 vida recuperada con Reanimar","base_cost":28,"max":8},
    },
    "vanguard": {
        "max_hp":{"name":"Coraza","description":"+1 vida maxima","base_cost":18,"max":8},
        "shield":{"name":"Escudo pesado","description":"+1 escudo maximo","base_cost":20,"max":8},
        "ability_damage":{"name":"Onda brutal","description":"+4 dano al estallido de Impacto","base_cost":26,"max":8},
        "ability_range":{"name":"Onda expansiva","description":"+12 alcance maximo de Impacto","base_cost":28,"max":8},
        "ability_stun":{"name":"Pulso aturdidor","description":"+0.12 s de aturdimiento con Impacto","base_cost":30,"max":8},
        "ability_speed":{"name":"Carga de choque","description":"+35 velocidad de expansion de Impacto","base_cost":30,"max":8},
    },
    "pyromancer": {
        "energy":{"name":"Nucleo igneo","description":"+10 energia maxima","base_cost":20,"max":8},
        "damage":{"name":"Combustion","description":"+4% dano total","base_cost":24,"max":8},
        "speed":{"name":"Paso de brasa","description":"+5 velocidad","base_cost":22,"max":8},
        "ability":{"name":"Estasis profunda","description":"+0.35 s de congelacion","base_cost":30,"max":8},
    },
    "striker": {
        "speed":{"name":"Reflejos","description":"+6 velocidad","base_cost":18,"max":8},
        "crit":{"name":"Precision","description":"+2% probabilidad critica","base_cost":24,"max":8},
        "damage":{"name":"Sobrecarga ofensiva","description":"+4% dano total","base_cost":24,"max":8},
        "ability":{"name":"Sobremarcha extendida","description":"+0.5 s de Sobremarcha","base_cost":30,"max":8},
    },
    "engineer": {
        "drone_count":{"name":"Enjambre ampliado","description":"+1 dron desplegado","base_cost":28,"max":6},
        "drone_damage":{"name":"Municion mejorada","description":"+25% dano de los drones","base_cost":24,"max":8},
        "drone_attack_speed":{"name":"Servomotores de combate","description":"+12% velocidad de ataque de los drones","base_cost":26,"max":8},
        "drone_durability":{"name":"Blindaje de drones","description":"+5 resistencia de cada dron","base_cost":30,"max":8},
    },
}

# Compatibilidad: las mejoras antiguas se conservan para partidas guardadas, pero el
# nuevo menu usa CHARACTER_UPGRADES.
UPGRADES = {
    "vitality": {"name":"Vitalidad", "description":"+1 HP maximo", "base_cost":20, "max":5},
    "shield": {"name":"Blindaje", "description":"+1 escudo maximo", "base_cost":25, "max":5},
    "damage": {"name":"Potencia", "description":"+5% dano", "base_cost":35, "max":6},
    "speed": {"name":"Movilidad", "description":"+5 velocidad", "base_cost":30, "max":6},
    "energy": {"name":"Bateria", "description":"+10 energia maxima", "base_cost":25, "max":5},
    "shield_regen": {"name":"Reactor", "description":"+0.15 regen de escudo", "base_cost":30, "max":5},
}

def save_path():
    base=os.environ.get("APPDATA") or os.path.expanduser("~")
    folder=os.path.join(base,"AshenVault" if os.environ.get("APPDATA") else ".ashenvault")
    os.makedirs(folder,exist_ok=True)
    return os.path.join(folder,"save.json")

def _merge(base,over):
    out=json.loads(json.dumps(base))
    for k,v in over.items():
        if isinstance(v,dict) and isinstance(out.get(k),dict): out[k]=_merge(out[k],v)
        else: out[k]=v
    return out

def xp_to_next(level):
    level=max(1,int(level))
    return 80 + (level-1)*35 + int((level-1)**1.25*10)

class SaveData:
    def __init__(self,path=None):
        self.path=path or save_path(); self.data=json.loads(json.dumps(DEFAULT)); self.load()
    def load(self):
        try:
            with open(self.path,encoding="utf-8") as f: raw=json.load(f)
            self.data=_merge(DEFAULT,raw)
            old_settings=raw.get("settings",{}) if isinstance(raw,dict) else {}
            if "effects_volume" not in old_settings and "volume" in old_settings:
                self.data["settings"]["effects_volume"]=old_settings["volume"]
            keys=self.data["settings"]["keys"]
            if "ability" not in keys: keys["ability"]="q"
            if "map" not in keys: keys["map"]="m"
            for cid in DEFAULT["character_progress"]:
                self.data["character_progress"].setdefault(cid, {"level":1,"xp":0,"upgrades":{}})
            self.data["version"]=DEFAULT["version"]
        except (OSError,ValueError): pass
    def save(self):
        tmp=self.path+".tmp"
        try:
            with open(tmp,"w",encoding="utf-8") as f: json.dump(self.data,f,indent=2)
            os.replace(tmp,self.path)
        except OSError: pass
    def upgrade_cost(self,kind):
        u=self.data["upgrades"][kind]; return UPGRADES[kind]["base_cost"]*(u+1)
    def buy_upgrade(self,kind):
        if kind not in UPGRADES:return False
        level=self.data["upgrades"].get(kind,0)
        if level>=UPGRADES[kind]["max"]:return False
        cost=self.upgrade_cost(kind)
        if self.data["meta_currency"]<cost:return False
        self.data["meta_currency"]-=cost; self.data["upgrades"][kind]=level+1; self.save(); return True
    def character_upgrade_cost(self,cid,kind):
        tree=CHARACTER_UPGRADES.get(cid,{})
        if kind not in tree:return 999999
        level=int(self.data["character_progress"].setdefault(cid,{"level":1,"xp":0,"upgrades":{}}).setdefault("upgrades",{}).get(kind,0))
        return tree[kind]["base_cost"]*(level+1)
    def buy_character_upgrade(self,cid,kind):
        tree=CHARACTER_UPGRADES.get(cid,{})
        if kind not in tree:return False
        prog=self.data["character_progress"].setdefault(cid,{"level":1,"xp":0,"upgrades":{}})
        up=prog.setdefault("upgrades",{}); level=int(up.get(kind,0)); spec=tree[kind]
        if level>=spec["max"]:return False
        cost=self.character_upgrade_cost(cid,kind)
        if self.data["meta_currency"]<cost:return False
        self.data["meta_currency"]-=cost; up[kind]=level+1; self.save(); return True
    def set_key(self, action, key_name):
        if action not in self.data["settings"]["keys"]: return False
        self.data["settings"]["keys"][action] = key_name; self.save(); return True
    def add_character_xp(self,cid,amount):
        prog=self.data["character_progress"].setdefault(cid,{"level":1,"xp":0,"upgrades":{}})
        prog["xp"] += max(0,int(amount)); gained=0
        while prog["xp"] >= xp_to_next(prog["level"]):
            prog["xp"] -= xp_to_next(prog["level"]); prog["level"] += 1; gained += 1
        return gained
    def record_run(self,stats,victory=False,char_id=None):
        s=self.data["stats"]; s["runs"]+=1; s["deaths"]+=0 if victory else 1
        s["kills"]+=stats["kills"]; s["total_coins"]+=stats["coins"]; s["best_wave"]=max(s["best_wave"],stats["waves"])
        s["purchases"]+=stats.get("purchases",0); s["abilities"]+=stats.get("abilities",0); s["bosses_defeated"]+=stats.get("bosses_defeated",0)
        reward=stats["waves"]*2+stats["kills"]//5+(25 if victory else 0)
        self.data["meta_currency"]+=reward; s["meta_earned"]+=reward
        xp=int(stats.get("xp", stats["kills"]*3 + stats.get("rooms",1)*6 + stats.get("bosses_defeated",0)*40 + stats.get("coins",0)))
        levels=0
        if char_id: levels=self.add_character_xp(char_id,xp)
        self.last_run_xp=xp; self.last_levels_gained=levels
        self.save(); return reward
