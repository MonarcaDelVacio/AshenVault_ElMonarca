import os,sys,unittest,math
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.gen import generate_layout,generate_room,validate_layout,_flood
from game.sim import Sim,Input
from game.world import TILE

class Phase2(unittest.TestCase):
    def test_500_seed_path_and_connectivity(self):
        for seed in range(500):
            layout=generate_layout(seed)
            self.assertTrue(validate_layout(layout))
            self.assertEqual(tuple(layout['path'][0]),tuple(layout['start']))
            self.assertEqual(tuple(layout['path'][-1]),tuple(layout['boss']))
            self.assertNotIn(tuple(layout['boss']),[tuple(x) for x in layout['path'][:-1]])
    def test_room_flood_fill(self):
        for seed in range(100):
            r=generate_room(seed)
            self.assertEqual(len(_flood(r['grid'],r['player_spawn'])),sum(row.count(0) for row in r['grid']))
    def test_dungeon_has_boss_and_no_branch_attached_to_boss(self):
        from game.world import Dungeon
        for seed in range(100):
            d=Dungeon(seed); boss=tuple(d.layout['boss']); rooms=set(map(tuple,d.layout['rooms']))
            self.assertIn(boss,rooms)
            path_parent=tuple(d.layout['path'][-2])
            boss_neighbors={n for n in ((boss[0]+1,boss[1]),(boss[0]-1,boss[1]),(boss[0],boss[1]+1),(boss[0],boss[1]-1)) if n in rooms}
            self.assertEqual(boss_neighbors,{path_parent})
            self.assertTrue(validate_layout(d.layout))
    def test_room_doors_close_and_open(self):
        s=Sim(GameData(),'soldier',seed=2)
        if s.room.room_type in ('start','combat','elite','challenge'):
            self.assertTrue(any(not d.open for d in s.arena.doors.values()))
            s.enemies.clear(); s._complete_room()
            self.assertTrue(all(d.open for d in s.arena.doors.values()))
    def test_items_are_sim_owned_and_bonuses_apply(self):
        s=Sim(GameData(),'soldier',seed=3)
        s.enemies.clear(); s._complete_room()
        if s.items:
            before=s.player.max_hp
            # Force a vitality item if random reward did not produce one.
            from game.items import make_item
            it=make_item(s.data.items,'vitality'); it.x,it.y=s.player.x,s.player.y
            s.items=[it]; s._try_interact()
            self.assertGreater(s.player.max_hp,before)
    def test_room_local_flow_field(self):
        s=Sim(GameData(),'soldier',seed=4)
        target=s.arena.tile_of(s.player.x,s.player.y)
        self.assertEqual(len(s.flow),s.arena.rows)
        self.assertEqual(len(s.flow[0]),s.arena.cols)
        self.assertEqual(s.flow[target[1]][target[0]],0)

if __name__=='__main__':unittest.main()
