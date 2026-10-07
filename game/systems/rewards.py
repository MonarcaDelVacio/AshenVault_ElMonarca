"""Chest and room-reward helpers extracted from Sim."""

from ..items import make_item\nfrom ..chests import Chest


def spawn_chest(sim, chest_type="common"):
    cx, cy = sim.arena.width / 2, sim.arena.height / 2
    if sim.chest is not None:
        return
    sim.chest = Chest(chest_type, cx, cy)
    sim.emit("chest_spawn", cx, cy, chest_type)


def open_chest(sim):
    if sim.chest is None or sim.chest.is_open:
        return False
    if not sim.chest.open():
        return False
    sim.emit("chest_open", sim.chest.x, sim.chest.y, sim.chest.chest_type)
    choices = [w for w in sim.data.weapons if w not in {x.d.id for x in sim.player.inventory}]
    if choices:
        wid = sim.rng.choice(choices)
        wx, wy = sim._safe_drop_position(sim.chest.x + 42, sim.chest.y, 10.0)
        it = type("WeaponPickup", (), {"id":wid, "name":sim.data.weapons[wid].name,
            "kind":"weapon", "weapon_id":wid, "x":wx, "y":wy})()
        sim.items.append(it); sim.stats["items"] += 1
        sim.emit("weapon_drop", it.x, it.y, wid)
    sim.emit("chest_coins", sim.chest.x, sim.chest.y, 0)
    return True


def drop_room_reward(sim, guaranteed=False, quality=0, position=None):
    cx, cy = position if position is not None else (sim.arena.width/2, sim.arena.height/2)
    cx, cy = sim._safe_drop_position(cx, cy, 10.0)
    chance = 1.0 if guaranteed else .65
    if sim.rng.random() < chance:
        ids = list(sim.data.items)
        if quality >= 2:
            ids = [i for i in ids if i not in ("magnetic", "swift")] or ids
        ident = sim.rng.choice(ids)
        it = make_item(sim.data.items, ident)
        it.x, it.y = cx, cy
        sim.items.append(it); sim.stats["items"] += 1
        sim.emit("item_drop", cx, cy, ident)
    if guaranteed or sim.rng.random() < .35:
        sim.keys += 1; sim.emit("key_drop", cx, cy)
    if guaranteed or sim.rng.random() < .30:
        choices = [w for w in sim.data.weapons if w not in {x.d.id for x in sim.player.inventory}]
        if choices:
            wid = sim.rng.choice(choices)
            wx, wy = sim._safe_drop_position(cx+42, cy, 10.0)
            it = type("WeaponPickup", (object,), {"id":wid, "name":sim.data.weapons[wid].name,
                "kind":"weapon", "weapon_id":wid, "x":wx, "y":wy})()
            sim.items.append(it); sim.emit("weapon_drop", it.x, it.y, wid)
