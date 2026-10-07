from game.systems.rewards import spawn_chest, open_chest


class RNG:
    def choice(self, values): return values[0]
    def random(self): return 0.0

class Player:
    def __init__(self): self.inventory=[]

class Arena: width=320; height=240

class ChestData:
    def __init__(self): self.is_open=False; self.chest_type="common"
    def open(self):
        if self.is_open: return False
        self.is_open=True; return True

class Sim:
    def __init__(self):
        self.arena=Arena(); self.chest=None; self.rng=RNG(); self.items=[]; self.stats={"items":0}; self.player=Player(); self.events=[]
        w=type("W",(),{})(); w.name="Sword"; w.d=type("D",(),{"id":"sword"})()
        self.data=type("Data",(),{})(); self.data.weapons={"sword":w}; self.data.items={}
    def emit(self,*event): self.events.append(event)
    def _safe_drop_position(self,x,y,r): return x,y

def test_spawn_chest_creates_single_chest_and_event():
    sim=Sim(); spawn_chest(sim,"rare")
    assert sim.chest is not None
    assert sim.chest.chest_type=="rare"
    assert sim.events[-1]==("chest_spawn",160.0,120.0,"rare")

def test_open_chest_drops_available_weapon():
    sim=Sim(); spawn_chest(sim,"common")
    assert open_chest(sim) is True
    assert len(sim.items)==1
    assert sim.items[0].weapon_id=="sword"
    assert sim.stats["items"]==1
    assert sim.events[-1]==("chest_coins",160.0,120.0,0)

def test_open_chest_cannot_open_twice():
    sim=Sim(); spawn_chest(sim,"common")
    assert open_chest(sim) is True
    assert open_chest(sim) is False
