from game.data import GameData
from game.sim import Sim
from game.weapons import WeaponState


def _weapon_pickup(weapon_id, x, y):
    return type("WeaponPickup", (), {
        "id": weapon_id,
        "name": weapon_id,
        "kind": "weapon",
        "weapon_id": weapon_id,
        "x": x,
        "y": y,
    })()


def test_floor_weapon_pickup_keeps_inventory_at_three_and_swaps_selected_weapon():
    data = GameData()
    sim = Sim(data, "soldier", seed=41)
    p = sim.player
    ids = list(data.weapons)
    assert len(ids) >= 4
    chosen = ids[:3]
    incoming = next(wid for wid in ids if wid not in chosen)
    p.inventory = [WeaponState(data.weapons[wid]) for wid in chosen]
    p.weapon = p.inventory[1]
    selected_id = p.weapon.d.id
    pickup = _weapon_pickup(incoming, p.x, p.y)
    sim.items = [pickup]

    sim._try_interact()

    assert len(p.inventory) == 3
    assert p.weapon is p.inventory[1]
    assert p.weapon.d.id == incoming
    assert len(sim.items) == 1
    assert sim.items[0] is pickup
    assert pickup.weapon_id == selected_id


def test_weapon_pickup_adds_slots_until_three_then_never_exceeds_limit():
    data = GameData()
    sim = Sim(data, "soldier", seed=42)
    p = sim.player
    ids = list(data.weapons)
    p.inventory = [WeaponState(data.weapons[ids[0]])]
    p.weapon = p.inventory[0]
    for wid in ids[1:3]:
        sim.items = [_weapon_pickup(wid, p.x, p.y)]
        sim._try_interact()
        assert len(p.inventory) <= 3
    assert len(p.inventory) == 3


def test_shop_weapon_purchase_does_not_overfill_inventory_or_charge_coins():
    data = GameData()
    sim = Sim(data, "soldier", seed=43)
    p = sim.player
    ids = list(data.weapons)
    p.inventory = [WeaponState(data.weapons[wid]) for wid in ids[:3]]
    p.weapon = p.inventory[0]
    p.coins = 1000
    offer = type("ShopOffer", (), {
        "kind": "weapon", "id": ids[3], "name": ids[3], "price": 20,
        "x": p.x, "y": p.y, "sold": False,
    })()
    before = p.coins

    assert sim._buy_shop_offer(offer) is False
    assert len(p.inventory) == 3
    assert p.coins == before
    assert offer.sold is False
