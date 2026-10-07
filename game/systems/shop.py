"""Shop setup and purchase helpers extracted from Sim."""

from ..weapons import WeaponState
from ..items import apply_item_bonuses


def setup_shop(sim):
    sim.shop_offers = []
    cx, cy = sim.arena.width / 2, sim.arena.height / 2
    weapon_ids = list(sim.data.weapons)
    sim.rng.shuffle(weapon_ids)
    prices = sim.data.shops.get("weapon_prices", {})
    for idx, wid in enumerate(weapon_ids[:2]):
        w = sim.data.weapons[wid]
        price = prices.get(w.rarity, 20)
        sim.shop_offers.append(type("ShopOffer", (), {
            "kind":"weapon", "id":wid, "name":w.name, "price":price,
            "x":cx-72+idx*144, "y":cy-35, "sold":False,
        })())
    item_ids = list(sim.data.items)
    sim.rng.shuffle(item_ids)
    if item_ids:
        ident = item_ids[0]
        item_def = sim.data.items[ident]
        effects = item_def.get("effects", {}) if isinstance(item_def, dict) else getattr(item_def, "effects", {})
        name = item_def.get("name", ident) if isinstance(item_def, dict) else getattr(item_def, "name", ident)
        price = 18 + 4 * len(effects)
        sim.shop_offers.append(type("ShopOffer", (), {
            "kind":"item", "id":ident, "name":name, "price":price, "amount":1,
            "x":cx, "y":cy+55, "sold":False,
        })())


def buy_shop_offer(sim, offer):
    p = sim.player
    if offer.sold or p.coins < offer.price:
        return False
    if offer.kind == "weapon":
        if len(p.inventory) >= 3 or any(w.d.id == offer.id for w in p.inventory):
            return False
        p.inventory.append(WeaponState(sim.data.weapons[offer.id]))
    elif offer.kind == "heal":
        if p.hp >= p.max_hp:
            return False
        p.hp = min(p.max_hp, p.hp + offer.amount)
        p.set_status("heal", 1.8)
    elif offer.kind == "shield":
        if p.shield >= p.max_shield:
            return False
        p.shield = min(p.max_shield, p.shield + offer.amount)
        p.set_status("shield", 2.2)
    elif offer.kind == "energy":
        if p.energy >= p.max_energy:
            return False
        old_energy = p.energy
        p.energy = min(p.max_energy, p.energy + offer.amount)
        if p.energy > old_energy:
            p.feedback_flash("energy", .26)
            sim.emit("energy_pickup", offer.x, offer.y, p.energy-old_energy)
    elif offer.kind == "item":
        item_def = sim.data.items.get(offer.id)
        if item_def is None:
            return False
        apply_item_bonuses(p, item_def, sim.data.synergies)
    else:
        return False
    p.coins -= offer.price
    sim.stats["purchases"] += 1
    offer.sold = True
    sim.emit("shop_purchase", offer.x, offer.y, offer.id)
    return True
