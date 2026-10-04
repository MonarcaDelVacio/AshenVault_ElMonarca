import os,sys,tempfile,unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim, Input
from game.save import SaveData, UPGRADES

class Phase4(unittest.TestCase):
    def test_six_unique_bosses_are_loaded(self):
        d=GameData(); self.assertEqual(len(d.bosses),6)
        self.assertEqual(set(d.biome_bosses),{"ruins","forest","dungeon","laboratory","volcanic","final"})
        self.assertEqual(set(d.biome_bosses.values()),set(d.bosses))
        for b in d.bosses.values(): self.assertEqual(len(b.phases),3)
    def test_boss_selected_from_biome(self):
        d=GameData(); s=Sim(d,"soldier",seed=3)
        s.room=s.dungeon.room
        s.enemies=[]
        boss_room=next(r for r in s.dungeon.rooms.values() if r.room_type=="boss")
        s._enter_room(boss_room)
        self.assertEqual(s.enemies[0].d.id,d.biome_bosses[boss_room.arena.biome])
    def test_permanent_upgrade_is_spent_and_persists(self):
        with tempfile.TemporaryDirectory() as td:
            s=SaveData(os.path.join(td,"save.json")); s.data["meta_currency"]=100
            cost=s.upgrade_cost("vitality"); self.assertTrue(s.buy_upgrade("vitality")); self.assertEqual(s.data["meta_currency"],100-cost)
            s2=SaveData(s.path); self.assertEqual(s2.data["upgrades"]["vitality"],1)
    def test_upgrade_changes_new_run_stats(self):
        d=GameData(); base=Sim(d,"soldier",seed=8); boosted=Sim(d,"soldier",seed=8,meta_upgrades={"vitality":2,"shield":1,"damage":2,"speed":1,"energy":1,"shield_regen":1})
        self.assertEqual(boosted.player.max_hp,base.player.max_hp+2)
        self.assertEqual(boosted.player.max_shield,base.player.max_shield+1)
        self.assertGreater(boosted.player.damage_mult,base.player.damage_mult)
        self.assertGreater(boosted.player.speed,base.player.speed)
        self.assertGreater(boosted.player.max_energy,base.player.max_energy)
        self.assertGreater(boosted.player.shield_regen_rate,base.player.shield_regen_rate)
    def test_run_reward_records_bosses(self):
        with tempfile.TemporaryDirectory() as td:
            s=SaveData(os.path.join(td,"save.json")); before=s.data["stats"]["bosses_defeated"]
            reward=s.record_run({"kills":10,"coins":5,"waves":6,"bosses_defeated":1},victory=True)
            self.assertGreaterEqual(reward,25); self.assertEqual(s.data["stats"]["bosses_defeated"],before+1)

if __name__=="__main__":unittest.main()

class Phase4Regression(unittest.TestCase):
    def test_upgrade_menu_draw_uses_renderer_font(self):
        main_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),"main.py")
        with open(main_path,encoding="utf-8") as f:
            src=f.read()
        start=src.index("    def draw_hub(self):")
        end=src.index("    def draw(self):", start)
        hub_src=src[start:end]
        self.assertIn("self.r.menu_font", hub_src)
        self.assertNotIn(",self.font", hub_src)


    def test_cleared_boss_does_not_respawn_when_reentered(self):
        d=GameData()
        s=Sim(d,"soldier",seed=17)
        boss_room=next(r for r in s.dungeon.rooms.values() if r.room_type=="boss")
        s.dungeon.current=boss_room.id
        s.enemies=[]
        s._enter_room(boss_room)
        self.assertEqual(len(s.enemies),1)
        s.enemies[0].alive=False
        s.update(Input(),1/60)
        self.assertTrue(boss_room.cleared)
        self.assertEqual(len(s.enemies),0)
        self.assertTrue(all(door.open for door in boss_room.arena.doors.values()))

        # Volver a entrar en una sala de jefe ya completada no debe crear otro jefe.
        s._enter_room(boss_room)
        self.assertEqual(len(s.enemies),0)
        self.assertTrue(boss_room.cleared)
        self.assertFalse(boss_room.doors_locked)
        self.assertTrue(all(door.open for door in boss_room.arena.doors.values()))

    def test_every_boss_opens_doors_and_allows_path_transition(self):
        d=GameData()
        path_cache={}
        for seed in range(25):
            s=Sim(d,"soldier",seed=seed)
            path=[tuple(x) for x in s.dungeon.layout["path"]]
            path_index={rid:i for i,rid in enumerate(path)}
            for rid in path:
                room=s.dungeon.rooms[rid]
                if room.room_type!="boss":
                    continue
                s.dungeon.current=rid
                s.enemies=[]
                s._enter_room(room)
                self.assertEqual(len(s.enemies),1)
                s.enemies[0].alive=False
                s.update(__import__("game.sim",fromlist=["Input"]).Input(),1/60)
                self.assertTrue(room.cleared)
                self.assertTrue(all(door.open for door in room.arena.doors.values()))
                idx=path_index[rid]
                if idx >= len(path)-1:
                    self.assertTrue(room.cleared)
                    self.assertTrue(s.portal)
                    continue
                nxt=path[idx+1]
                dx,dy=nxt[0]-rid[0],nxt[1]-rid[1]
                side="E" if dx==1 else "W" if dx==-1 else "S" if dy==1 else "N"
                door=room.arena.doors.get(side)
                self.assertIsNotNone(door)
                s.player.x,s.player.y=room.arena.tile_center(door.x,door.y)
                i=__import__("game.sim",fromlist=["Input"]).Input(); i.interact_pressed=True
                i.aim_x,i.aim_y=s.player.x,s.player.y
                s.update(i,1/60)
                self.assertEqual(tuple(s.dungeon.current),nxt)

if __name__=="__main__":unittest.main()
