import os,sys,unittest,tempfile
sys.path.insert(0,os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim,Input
from game.world import Dungeon
from game.save import SaveData

class Phase3(unittest.TestCase):
    def test_six_characters_have_distinct_abilities(self):
        d=GameData(); self.assertEqual(len(d.characters),6)
        self.assertEqual(len({c.ability["kind"] for c in d.characters.values()}),6)
        for c in d.characters.values(): self.assertIn(c.start_weapon,d.weapons)

    def test_biome_progression_uses_all_six(self):
        d=Dungeon(12345); got={r.arena.biome for r in d.rooms.values()}
        self.assertEqual(got,{"ruins","forest","dungeon","laboratory","volcanic","final"})

    def test_shop_has_purchasable_offers(self):
        d=GameData(); s=Sim(d,"soldier",seed=7)
        shop=next(r for r in s.dungeon.rooms.values() if r.room_type=="shop")
        s._enter_room(shop)
        self.assertGreaterEqual(len(s.shop_offers),2)
        offer=s.shop_offers[0]; s.player.coins=offer.price
        s.player.x,s.player.y=offer.x,offer.y
        i=Input(); i.interact_pressed=True; s.update(i,0.01)
        self.assertTrue(offer.sold); self.assertEqual(s.stats["purchases"],1)

    def test_abilities_have_real_effects(self):
        d=GameData()
        for cid in d.characters:
            s=Sim(d,cid,seed=2); s.player.ability_cd=0
            if cid=="medic": s.player.hp=2
            i=Input(); i.ability_pressed=True; i.aim_x=s.player.x+1; i.aim_y=s.player.y
            s.update(i,0.01)
            self.assertGreaterEqual(s.stats["abilities"],1,cid)

    def test_rook_burst_damages_nearby_enemies_without_crashing(self):
        from game.enemies import Enemy
        d = GameData()
        s = Sim(d, "vanguard", seed=17)
        p = s.player
        p.ability_cd = 0
        enemy_data = next(iter(d.enemies.values()))
        e = Enemy(enemy_data, p.x + 20, p.y)
        e.spawn_delay = 0
        before = e.hp
        s.enemies = [e]
        i = Input(); i.ability_pressed = True
        i.aim_x = p.x + 1; i.aim_y = p.y
        s.update(i, 0.01)
        self.assertLess(e.hp, before)
        self.assertEqual(s.stats["abilities"], 1)

    def test_save_migrates_new_stats(self):
        with tempfile.TemporaryDirectory() as td:
            p=os.path.join(td,"save.json"); s=SaveData(p); self.assertEqual(s.data["version"],5)
            self.assertIn("purchases",s.data["stats"]); s.save(); s2=SaveData(p); self.assertEqual(s2.data["version"],5)

if __name__=="__main__":unittest.main()
