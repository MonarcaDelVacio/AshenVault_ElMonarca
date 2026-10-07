from types import SimpleNamespace

import game.systems.interaction as interaction


class WeaponStateStub:
    def __init__(self, definition):
        self.d = definition
        self.ammo = 2
        self.reserve_magazines = 1
        self.max_reserve_magazines = 6
        self.durability = 4
        self.max_durability = 10


class Player:
    def __init__(self):
        self.x = self.y = 100.0
        self.hp = 5
        self.max_hp = 10
        self.energy = 10
        self.max_energy = 100
        self.inventory = []
        self.weapon = None
        self.selected_slot = 0
        self.items = []
        self.status = []
        self.flashes = []

    def set_status(self, kind, duration):
        self.status.append((kind, duration))

    def feedback_flash(self, kind, duration):
        self.flashes.append((kind, duration))


class Sim:
    def __init__(self, item):
        self.player = Player()
        self.player.items = []
        self.items = [item]
        self.portal = False
        self.portal_position = (0, 0)
        self.chest = None
        self.shop_offers = []
        self.room = SimpleNamespace(room_type="combat")
        self.arena = SimpleNamespace(width=320, height=240)
        self.data = SimpleNamespace(weapons={}, items={})
        self.events = []
        self.next_dungeon = False

    def _open_statue_menu(self):
        return False

    def _open_chest(self):
        return False

    def _buy_shop_offer(self, offer):
        return False

    def _enter_next_dungeon(self):
        self.next_dungeon = True

    def _safe_drop_position(self, x, y, radius):
        return x, y

    def emit(self, *event):
        self.events.append(event)


def test_heal_pickup_preserves_feedback_and_event():
    item = SimpleNamespace(x=100.0, y=100.0, kind="heal")
    sim = Sim(item)

    assert interaction.try_interact(sim) is True
    assert sim.player.hp == 7
    assert sim.player.status == [("heal", 1.8)]
    assert sim.player.flashes == [("heal", 0.26)]
    assert sim.items == []
    assert sim.events[-1] == ("item_pickup", 100.0, 100.0, "heal")


def test_energy_pickup_preserves_cap_and_event():
    item = SimpleNamespace(x=100.0, y=100.0, kind="energy")
    sim = Sim(item)
    sim.player.energy = 90

    assert interaction.try_interact(sim) is True
    assert sim.player.energy == 100
    assert sim.events[-1] == ("item_pickup", 100.0, 100.0, "energy")


def test_ammo_pickup_uses_first_non_melee_weapon():
    definition = SimpleNamespace(id="rifle", **{"class": "rifle"})
    weapon = WeaponStateStub(definition)
    sim = Sim(SimpleNamespace(x=100.0, y=100.0, kind="ammo", magazines=3))
    sim.player.inventory = [weapon]
    sim.player.weapon = weapon

    assert interaction.try_interact(sim) is True
    assert weapon.reserve_magazines == 4
    assert sim.events[-1] == ("ammo_pickup", 100.0, 100.0, 3)


def test_weapon_pickup_adds_and_selects_new_slot(monkeypatch):
    definition = SimpleNamespace(id="rifle", name="Rifle", **{"class": "rifle"})
    sim = Sim(SimpleNamespace(x=100.0, y=100.0, kind="weapon", weapon_id="rifle"))
    sim.data.weapons = {"rifle": definition}
    monkeypatch.setattr(interaction, "WeaponState", WeaponStateStub)

    assert interaction.try_interact(sim) is True
    assert len(sim.player.inventory) == 1
    assert sim.player.weapon is sim.player.inventory[0]
    assert sim.player.selected_slot == 0
    assert sim.events[-1] == ("weapon_pickup", 100.0, 100.0, "rifle")
