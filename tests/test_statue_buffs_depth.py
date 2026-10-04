from game.data import GameData
from game.gen import generate_room
from game.sim import Sim, Input
from game.statues import STATUE_BUFFS, statue_offer


def test_secret_statues_are_centered_and_have_multiple_types():
    kinds=[]
    for seed in range(5):
        room=generate_room(seed, "secret", "ruins", ["N", "S"])
        statues=[d for d in room["decorations"] if d["kind"].startswith("statue_")]
        assert len(statues)==1
        statue=statues[0]
        assert (statue["x"], statue["y"]) == (12, 8)
        kinds.append(statue["kind"])
    assert set(kinds)==set(STATUE_BUFFS)


def test_statue_offer_scales_cost_and_value_with_difficulty():
    easy=statue_offer("statue_knight",1)
    hard=statue_offer("statue_knight",4)
    assert hard["cost"] > easy["cost"]
    assert hard["value"] > easy["value"]


def test_statue_can_be_bought_only_once_and_buff_is_run_local():
    sim=Sim(GameData(), "soldier", seed=321)
    room=next(r for r in sim.dungeon.rooms.values() if r.room_type=="secret")
    sim._enter_room(room)
    statue=next(d for d in room.arena.decorations if d["kind"].startswith("statue_"))
    sx=statue["x"]*32+16; sy=statue["y"]*32+48
    sim.player.x,sim.player.y=sx,sy
    sim.player.coins=100
    inp=Input(); inp.interact_pressed=True
    sim.update(inp,0.016)
    assert sim.statue_menu is not None
    cost=sim.statue_menu["cost"]
    assert sim.accept_statue_buff() is True
    assert sim.player.coins==100-cost
    assert len(sim.statue_buffs)==1
    sim.player.x,sim.player.y=sx,sy
    inp=Input(); inp.interact_pressed=True
    sim.update(inp,0.016)
    assert sim.statue_menu is None


def test_defensive_statue_changes_real_damage_taken():
    sim=Sim(GameData(), "soldier", seed=9)
    p=sim.player
    hp=p.hp
    p.shield=0
    assert p.take_damage(2) is True
    normal_loss=hp-p.hp
    p.hp=hp; p.shield=0; p.statue_damage_taken_mult=0.5; p.invuln=0
    assert p.take_damage(2) is True
    reduced_loss=hp-p.hp
    assert reduced_loss < normal_loss


def test_new_floor_surface_names_are_loaded_by_renderer_source():
    source=open("game/render.py",encoding="utf-8").read()
    readme=open("assets/floors/README.txt",encoding="utf-8").read()
    assert "self.named_floor_images" in source
    for name in ("arena","hierba","ladrillos","ladrillosdepiedra","madera","roca","rocanegra"):
        assert f"Superficie_{name}.png" in readme


def test_actor_depth_uses_shared_y_order_and_shop_npcs_are_depth_actors():
    source=open("game/render.py",encoding="utf-8").read()
    assert 'actors.sort(key=lambda item:item[0])' in source
    assert '"player", p' in source
    assert '"enemy", e' in source
    assert '"merchant",merchant' in source
    assert '"pet",pet' in source
