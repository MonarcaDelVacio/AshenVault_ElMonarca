import os,sys,tempfile,unittest,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim, Input
from game.save import SaveData
from game.fx import Fx

class Phase5(unittest.TestCase):
    def test_save_migrates_to_v5_and_rebinds(self):
        with tempfile.TemporaryDirectory() as td:
            path=os.path.join(td,"save.json")
            s=SaveData(path)
            self.assertEqual(s.data["version"],5)
            self.assertTrue(s.set_key("dash","f"))
            s2=SaveData(path)
            self.assertEqual(s2.data["settings"]["keys"]["dash"],"f")

    def test_fx_handles_phase5_events(self):
        fx=Fx()
        events=[("boss_spawn",100,100,"Boss"),("boss_phase",100,100,2),("room_clear",(0,0)),("victory_portal",200,200),("victory",),("ability_burst",100,100,50,2),("shop_purchase",100,100,"x")]
        for ev in events: fx.handle(ev)
        self.assertGreater(len(fx.particles),0)
        self.assertGreater(len(fx.texts),0)

    def test_six_biomes_have_progressive_boss_pressure(self):
        d=GameData()
        hp=[]; dmg=[]
        for bid in ["ruins","forest","dungeon","laboratory","volcanic","final"]:
            b=d.bosses[d.biome_bosses[bid]]
            hp.append(b.hp); dmg.append(b.damage)
        self.assertEqual(len(hp),6)
        self.assertGreaterEqual(hp[-1],hp[0])
        self.assertGreaterEqual(dmg[-1],dmg[0])

    def test_projectile_pool_reuses_objects(self):
        d=GameData(); s=Sim(d,"soldier",seed=4)
        p1=s.spawn_projectile(0,s.player.x,s.player.y,0,100,1,3,1,(255,255,255))
        self.assertIsNotNone(p1); p1.active=False
        s.pool._cursor=0
        p2=s.spawn_projectile(0,s.player.x,s.player.y,0,100,1,3,1,(255,255,255))
        self.assertIs(p1,p2)

if __name__=="__main__": unittest.main()
