import os,sys,tempfile,unittest
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim,Input
from game.world import Dungeon,SECRET
from game.save import SaveData

class Extra(unittest.TestCase):
    def test_content_counts(self):
        d=GameData(); self.assertGreaterEqual(len(d.weapons),50); self.assertGreaterEqual(len(d.enemies),15); self.assertEqual(len(d.biomes),6); self.assertGreaterEqual(len(d.bosses),1)
    def test_rooms_no_longer_generate_destructible_secret_walls(self):
        d=Dungeon(12)
        self.assertTrue(all(not room.arena.secrets for room in d.rooms.values()))
    def test_save_victory_does_not_count_as_death(self):
        with tempfile.TemporaryDirectory() as td:
            path=os.path.join(td,'save.json'); s=SaveData(path); before=s.data['stats']['deaths']; reward=s.record_run({'kills':10,'coins':3,'waves':5},victory=True)
            self.assertEqual(s.data['stats']['deaths'],before); self.assertGreaterEqual(reward,25); self.assertEqual(s.data['version'],5)
    def test_weapon_switch_edge_exists(self):
        s=Sim(GameData(),'soldier',seed=4); i=Input(); i.clear_edges(); self.assertFalse(i.switch_weapon_pressed)

if __name__=='__main__':unittest.main()
