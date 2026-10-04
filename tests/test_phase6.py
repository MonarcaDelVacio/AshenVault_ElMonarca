import unittest
from game.data import GameData
from game.sim import Sim, Input

class Phase6Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=GameData()

    def test_special_rooms_resolve_with_real_rewards(self):
        for typ in ("treasure","event","healing","secret"):
            found=None
            for seed in range(601,800):
                s=Sim(self.data,"soldier",seed=seed)
                found=next((rid for rid,r in s.dungeon.rooms.items() if r.room_type==typ),None)
                if found is not None: break
            self.assertIsNotNone(found, typ)
            s.dungeon.current=found; s.player.x,s.player.y=s.arena.player_spawn; s._enter_room(s.dungeon.room)
            self.assertTrue(s.dungeon.room.special_resolved)
            if typ in ("treasure","event","secret"):
                self.assertTrue(s.chest is not None or s.stats["items"] >= 1)

    def test_miniboss_room_has_real_miniboss(self):
        found=None
        for seed in range(602,900):
            s=Sim(self.data,"soldier",seed=seed)
            found=next((rid for rid,r in s.dungeon.rooms.items() if r.room_type=="miniboss"),None)
            if found is not None: break
        self.assertIsNotNone(found)
        s.enemies=[]; s.dungeon.current=found; s.arena=s.dungeon.rooms[found].arena; s.player.x,s.player.y=s.arena.player_spawn; s._enter_room(s.dungeon.room)
        self.assertEqual(len(s.enemies),1); self.assertTrue(getattr(s.enemies[0],"is_miniboss",False)); self.assertGreater(s.enemies[0].max_hp, 20)

    def test_enemy_projectile_patterns_spawn(self):
        for seed in range(610,616):
            s=Sim(self.data,"soldier",seed=seed); e=next(iter(self.data.enemies.values()))
            # Build a controlled ranged enemy with each supported pattern.
            for pattern in ("single","fan","burst","circle","spiral"):
                e2=next(x for x in self.data.enemies.values() if x.ai=="ranged")
                e2.projectile_pattern=pattern; e2.pellets=5; e2.cooldown=0; e2.windup=0; e2.attack_range=9999
                from game.enemies import Enemy
                x=Enemy(e2,s.player.x+100,s.player.y); x.spawn_delay=0; x.state="windup"; x.timer=0
                s.enemies=[x]; x.update(s,0.01)
                self.assertGreater(sum(1 for p in s.pool.items if p.active),0)
                s.pool.clear()

    def test_item_synergy_activates_once(self):
        s=Sim(self.data,"soldier",seed=603)
        a=type("Item",(),{"id":"incendiary","effects":{"damage_mult":0.12}})()
        b=type("Item",(),{"id":"overclock","effects":{"damage_mult":0.08}})()
        from game.items import apply_item_bonuses
        base=s.player.damage_mult; apply_item_bonuses(s.player,a,s.data.synergies); apply_item_bonuses(s.player,b,s.data.synergies)
        self.assertIn("inferno_core",s.player.synergies); self.assertGreater(s.player.damage_mult,base)


    def test_shop_allows_multiple_purchases_and_clears_on_exit(self):
        s=Sim(self.data,"soldier",seed=904)
        found=next((rid for rid,r in s.dungeon.rooms.items() if r.room_type=="shop"),None)
        self.assertIsNotNone(found)
        s.dungeon.current=found; s.arena=s.dungeon.rooms[found].arena; s._enter_room(s.dungeon.room)
        self.assertEqual(len(s.shop_offers),3)
        s.player.coins=500
        s.player.hp=max(1,s.player.max_hp-2); s.player.shield=max(0,s.player.max_shield-2); s.player.energy=max(0,s.player.max_energy-30)
        bought=0
        for offer in s.shop_offers:
            if not offer.sold and s._buy_shop_offer(offer): bought+=1
        self.assertEqual(bought,3)
        self.assertEqual(sum(not o.sold for o in s.shop_offers),0)
        other=next(rid for rid,r in s.dungeon.rooms.items() if rid!=found)
        s.dungeon.current=other; s._enter_room(s.dungeon.room)
        self.assertEqual(s.shop_offers,[])

    def test_bosses_are_spaced_and_not_fixed_to_second_room(self):
        signatures=[]
        for seed in range(100,115):
            d=Sim(self.data,"soldier",seed=seed).dungeon
            path=d.layout["path"]
            bosses=[i for i,rid in enumerate(path) if d.rooms[tuple(rid)].room_type=="boss"]
            self.assertEqual(len(bosses),6)
            self.assertGreaterEqual(bosses[0],3)
            self.assertTrue(all(b-a>=2 for a,b in zip(bosses,bosses[1:])))
            signatures.append(tuple(path))
        self.assertGreater(len(set(signatures)),1)

    def test_main_path_has_encounter_variety(self):
        seen=set()
        for seed in range(200,260):
            d=Sim(self.data,"soldier",seed=seed).dungeon
            seen.update(d.rooms[tuple(r)].room_type for r in d.layout["path"][:-1])
        self.assertIn("combat",seen)
        self.assertTrue(len(seen & {"elite","challenge","event","healing","treasure","shop"})>=2)

    def test_phase6_data_loaded(self):
        self.assertGreaterEqual(len(self.data.synergies),4)
        self.assertIn("miniboss",self.data.rooms)
        self.assertTrue(any(getattr(e,"projectile_pattern",None)=="spiral" for e in self.data.enemies.values()))

if __name__=="__main__": unittest.main()

class ChestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.data=GameData()

    def test_combat_completion_spawns_closed_chest_without_immediate_loot(self):
        s=Sim(self.data,"soldier",seed=42)
        s.room.room_type="combat"; s.room.cleared=False
        s.enemies.clear(); s._complete_room()
        self.assertIsNotNone(s.chest)
        self.assertEqual(s.chest.state, "closed")
        self.assertEqual(len(s.items), 0)

    def test_chest_opens_once_and_then_generates_reward(self):
        s=Sim(self.data,"soldier",seed=43)
        s.room.room_type="combat"; s.room.cleared=False
        s.enemies.clear(); s._complete_room()
        s.player.x,s.player.y=s.chest.x,s.chest.y
        s.inp=Input(); s.inp.interact_pressed=True; s.update(s.inp,0.01)
        self.assertTrue(s.chest.is_open)
        count_claimed=s.chest.reward_claimed
        s.player.x,s.player.y=s.chest.x+120,s.chest.y+120
        s.inp.interact_pressed=True; s.update(s.inp,0.01)
        self.assertTrue(s.chest.is_open)
        self.assertEqual(s.chest.reward_claimed,count_claimed)

    def test_chest_assets_are_present(self):
        from pathlib import Path
        root=Path(__file__).resolve().parents[1]
        self.assertTrue((root/"assets/chests/chest_closed.png").is_file())
        self.assertTrue((root/"assets/chests/chest_open.png").is_file())
