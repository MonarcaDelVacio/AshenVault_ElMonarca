from game.systems.shop import setup_shop, buy_shop_offer


class Player:
    def __init__(self):
        self.coins = 50
        self.inventory = []
        self.hp = 5
        self.max_hp = 10
        self.shield = 0
        self.max_shield = 10
        self.energy = 0
        self.max_energy = 10
        self.statuses = []
        self.feedback = []
    def set_status(self, kind, duration): self.statuses.append((kind, duration))
    def feedback_flash(self, kind, duration): self.feedback.append((kind, duration))

class RNG:
    def shuffle(self, values): return None

class Sim:
    def __init__(self):
        self.player = Player(); self.shop_offers=[]; self.stats={"purchases":0}; self.events=[]; self.rng=RNG()
        self.arena=type("Arena",(),{"width":320,"height":240})()
        weapon=type("Weapon",(),{"name":"Test Weapon","rarity":"common"})()
        weapon.d=type("D",(),{"id":"w1"})()
        self.data=type("Data",(),{})(); self.data.weapons={"w1":weapon,"w2":weapon}; self.data.shops={"weapon_prices":{"common":20}}
        self.data.items={"item1":{"name":"Item","effects":{"damage":1}}}; self.data.synergies={}
    def emit(self,*event): self.events.append(event)

def test_setup_shop_creates_two_weapons_and_one_item():
    sim=Sim(); setup_shop(sim)
    assert len(sim.shop_offers)==3
    assert sum(o.kind=="weapon" for o in sim.shop_offers)==2
    assert sum(o.kind=="item" for o in sim.shop_offers)==1

def test_weapon_purchase_spends_coins_and_marks_offer_sold():
    sim=Sim(); setup_shop(sim); offer=next(o for o in sim.shop_offers if o.kind=="weapon")
    assert buy_shop_offer(sim, offer) is True
    assert sim.player.coins==30
    assert len(sim.player.inventory)==1
    assert offer.sold is True
    assert sim.stats["purchases"]==1
    assert sim.events[-1][0]=="shop_purchase"

def test_purchase_fails_when_inventory_has_three_weapons():
    sim=Sim(); setup_shop(sim); offer=next(o for o in sim.shop_offers if o.kind=="weapon")
    sim.player.inventory=[type("W",(),{"d":type("D",(),{"id":str(i)})()})() for i in range(3)]
    assert buy_shop_offer(sim, offer) is False
    assert sim.player.coins==50
