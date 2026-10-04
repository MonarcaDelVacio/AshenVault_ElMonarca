import os, tempfile
from game.data import GameData
from game.sim import Sim, Input
from game.save import SaveData, CHARACTER_UPGRADES, xp_to_next


def test_character_progress_is_persistent_and_levels_gradually():
    with tempfile.TemporaryDirectory() as td:
        save=SaveData(os.path.join(td,"save.json"))
        xp=xp_to_next(1)-1
        assert save.add_character_xp("soldier", xp) == 0
        assert save.data["character_progress"]["soldier"]["level"] == 1
        assert save.add_character_xp("soldier", 2) == 1
        assert save.data["character_progress"]["soldier"]["level"] == 2


def test_character_upgrade_tree_differs_and_changes_real_stats():
    data=GameData()
    assert CHARACTER_UPGRADES["soldier"] != CHARACTER_UPGRADES["medic"]
    base=Sim(data,"soldier",seed=2,character_progress={"level":1,"xp":0,"upgrades":{}})
    boosted=Sim(data,"soldier",seed=2,character_progress={"level":1,"xp":0,"upgrades":{"max_hp":2,"ability":2}})
    assert boosted.player.max_hp == base.player.max_hp + 2
    assert boosted.player.ability["amount"] == base.player.ability["amount"] + 2


def test_final_boss_creates_interactive_portal_and_next_dungeon_is_harder():
    data=GameData(); sim=Sim(data,"soldier",seed=9)
    final=next(r for r in sim.dungeon.rooms.values() if r.room_type=="boss" and r.arena.biome=="final")
    sim.dungeon.current=final.id; sim._enter_room(final); sim.enemies=[]; final.cleared=False
    sim._complete_room()
    assert sim.portal is True
    assert sim.portal_position[0] != sim.arena.width / 2
    assert final.portal_room is True
    old=sim.difficulty
    sim.player.x,sim.player.y=sim.portal_position
    inp=Input(); inp.interact_pressed=True
    sim.update(inp,1/60)
    assert sim.difficulty == old+1
    assert sim.portal is False
    assert sim.dungeon.current == tuple(sim.dungeon.layout["start"])


def test_multiple_dungeon_portals_chain_without_stale_room_state():
    data=GameData(); sim=Sim(data,"soldier",seed=33)
    for expected_depth in (2, 3, 4):
        final=next(r for r in sim.dungeon.rooms.values() if r.room_type=="boss" and r.arena.biome=="final")
        sim.dungeon.current=final.id; sim._enter_room(final); sim.enemies=[]; final.cleared=False
        sim._complete_room()
        assert sim.portal is True
        sim.player.x,sim.player.y=sim.portal_position
        inp=Input(); inp.interact_pressed=True
        old=sim.difficulty
        sim.update(inp,1/60)
        assert sim.difficulty == old + 1 == expected_depth
        assert sim.portal is False
        assert sim.room.room_type == "start"
