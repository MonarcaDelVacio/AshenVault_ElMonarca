"""Player interaction and inventory pickup helpers extracted from Sim."""

from ..weapons import WeaponState
from ..items import apply_item_bonuses


def try_interact(sim):
    """Process portal, statue, chest, shop and floor-item interactions in original order."""
    p = sim.player

    if sim.portal:
        px, py = sim.portal_position
        if sim._distance(px, py, p.x, p.y) < 78:
            sim._enter_next_dungeon()
            return True

    if sim._open_statue_menu():
        return True

    if sim.chest is not None and not sim.chest.is_open:
        if sim._distance(sim.chest.x, sim.chest.y, p.x, p.y) < 72:
            if sim._open_chest():
                return True

    if sim.room.room_type == "shop":
        for offer in sim.shop_offers:
            if sim._distance(offer.x, offer.y, p.x, p.y) < 55 and sim._buy_shop_offer(offer):
                return True

    for item in list(sim.items):
        if hasattr(item, "x"):
            ix, iy = item.x, item.y
        else:
            ix, iy = sim.arena.width / 2, sim.arena.height / 2

        if sim._distance(ix, iy, p.x, p.y) >= 48:
            continue

        if getattr(item, "kind", "item") == "weapon":
            weapon_id = item.weapon_id
            existing = next((w for w in p.inventory if w.d.id == weapon_id), None)

            if existing is not None:
                incoming = WeaponState(sim.data.weapons[weapon_id])
                if getattr(existing.d, "class", "") == "melee":
                    existing.durability = min(
                        existing.max_durability,
                        existing.durability + incoming.durability,
                    )
                else:
                    existing.ammo = min(existing.d.magazine, existing.ammo + incoming.ammo)
                    existing.reserve_magazines = min(
                        existing.max_reserve_magazines,
                        existing.reserve_magazines + incoming.reserve_magazines,
                    )
                sim.items.remove(item)
            elif len(p.inventory) < 3:
                new_weapon = WeaponState(sim.data.weapons[weapon_id])
                p.inventory.append(new_weapon)
                p.selected_slot = len(p.inventory) - 1
                p.weapon = new_weapon
                sim.items.remove(item)
            else:
                selected_index = p.inventory.index(p.weapon)
                old_weapon = p.inventory[selected_index]
                p.inventory[selected_index] = WeaponState(sim.data.weapons[weapon_id])
                p.weapon = p.inventory[selected_index]
                item.weapon_id = old_weapon.d.id
                item.id = old_weapon.d.id
                item.name = old_weapon.d.name
                item.x, item.y = sim._safe_drop_position(ix + 28, iy, 10.0)

            sim.emit("weapon_pickup", p.x, p.y, weapon_id)
            return True

        if getattr(item, "kind", None) == "heal":
            old_hp = p.hp
            p.hp = min(p.max_hp, p.hp + 2)
            if p.hp > old_hp:
                p.set_status("heal", 1.8)
                p.feedback_flash("heal", 0.26)
                sim.emit("heal_pickup", p.x, p.y, p.hp - old_hp)
            sim.items.remove(item)
            sim.emit("item_pickup", p.x, p.y, "heal")
            return True

        if getattr(item, "kind", None) == "energy":
            old_energy = p.energy
            p.energy = min(p.max_energy, p.energy + 30)
            if p.energy > old_energy:
                p.feedback_flash("energy", 0.26)
                sim.emit("energy_pickup", p.x, p.y, p.energy - old_energy)
            sim.items.remove(item)
            sim.emit("item_pickup", p.x, p.y, "energy")
            return True

        if getattr(item, "kind", None) == "ammo":
            magazines = max(1, int(getattr(item, "magazines", 1)))
            target = (
                p.weapon
                if p.weapon is not None and getattr(p.weapon.d, "class", "") != "melee"
                else next(
                    (w for w in p.inventory if getattr(w.d, "class", "") != "melee"),
                    None,
                )
            )
            if target is not None:
                target.reserve_magazines = min(
                    target.max_reserve_magazines,
                    target.reserve_magazines + magazines,
                )
                sim.items.remove(item)
                sim.emit("ammo_pickup", p.x, p.y, magazines)
                return True

        apply_item_bonuses(p, item)
        sim.items.remove(item)
        sim.emit(
            "item_pickup",
            p.x,
            p.y,
            getattr(item, "id", getattr(item, "kind", "item")),
        )
        return True

    return False
