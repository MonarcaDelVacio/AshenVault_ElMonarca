from game.data import GameData
from game.sim import Sim
from game.world import Dungeon


def _weapon_item(wid, x, y):
    return type("WeaponPickup", (), {
        "id": wid, "name": wid, "kind": "weapon", "weapon_id": wid,
        "x": x, "y": y,
    })()


def test_floor_items_stay_owned_by_the_room_when_player_changes_rooms():
    sim = Sim(GameData(), "soldier", seed=73)
    current = sim.room
    side = next(side for side in current.arena.doors if sim.dungeon.neighbor(current.id, side) in sim.dungeon.rooms)
    target_id = sim.dungeon.neighbor(current.id, side)
    item = _weapon_item(next(iter(sim.data.weapons)), sim.player.x, sim.player.y)
    sim.items.append(item)
    current.arena.open_doors()
    sim.room.items = sim.items
    sim.room.pickups = sim.pickups
    sim.dungeon.current = target_id
    sim._enter_room(sim.dungeon.room)
    assert item not in sim.items
    assert item in current.items


def test_floor_items_are_not_loaded_from_other_rooms():
    sim = Sim(GameData(), "soldier", seed=74)
    first = sim.room
    item = _weapon_item(next(iter(sim.data.weapons)), sim.player.x, sim.player.y)
    first.items.append(item)
    adjacent_side = next(side for side, door in first.arena.doors.items() if door.open is False)
    target = sim.dungeon.neighbor(first.id, adjacent_side)
    if target not in sim.dungeon.rooms:
        return
    sim.dungeon.current = target
    sim._enter_room(sim.dungeon.room)
    assert item not in sim.items
    assert item in first.items


def test_drop_position_is_inside_the_room_even_when_source_is_at_the_edge():
    sim = Sim(GameData(), "soldier", seed=75)
    x, y = sim._safe_drop_position(-100, -100, 10)
    assert 10 <= x <= sim.arena.width - 10
    assert 10 <= y <= sim.arena.height - 10
    assert not sim.arena.box_hits(x, y, 10)
