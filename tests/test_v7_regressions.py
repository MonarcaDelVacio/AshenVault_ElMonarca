import os, sys, unittest, math
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim, Input
from game.enemies import Enemy
from game.bosses import Boss


class ContentAndMechanicsV7(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = GameData()

    def test_every_biome_pool_is_valid_and_distinct(self):
        pools = [tuple(self.data.biomes[k]["enemy_pool"]) for k in self.data.biomes]
        for pool in pools:
            self.assertGreaterEqual(len(pool), 3)
            self.assertTrue(all(eid in self.data.enemies for eid in pool))
        self.assertGreaterEqual(len(set(pools)), 5)

    def test_rarity_changes_weapon_stats(self):
        common = next(w for w in self.data.weapons.values() if w.rarity == "common")
        legendary = next(w for w in self.data.weapons.values() if w.rarity == "legendary")
        self.assertGreater(legendary.damage / legendary.base_damage, common.damage / common.base_damage)
        self.assertTrue(getattr(legendary, "rarity_effect", "none") != "none")

    def test_summoner_actually_spawns_minions(self):
        s = Sim(self.data, "soldier", seed=77)
        s.enemies.clear()
        e = Enemy(self.data.enemies["summoner"], s.player.x + 160, s.player.y, s.rng)
        e.spawn_delay = 0
        e.summon_timer = 0
        s.enemies = [e]
        for _ in range(120):
            s.update(Input(), 1/60)
            if s.count_summoned() > 0:
                break
        self.assertGreater(s.count_summoned(), 0)

    def test_secret_wall_helper_no_longer_grants_wall_loot(self):
        s = Sim(self.data, "soldier", seed=101)
        before_items, before_keys = len(s.items), s.keys
        self.assertFalse(s.break_secret(3, 4))
        self.assertEqual(len(s.items), before_items)
        self.assertEqual(s.keys, before_keys)

    def test_boss_phases_change_attack_pattern(self):
        bdef = self.data.bosses["warden"]
        s = Sim(self.data, "soldier", seed=88)
        b = Boss(bdef, s.player.x + 180, s.player.y, s.rng)
        b.spawn_delay = 0
        patterns = []
        for phase in (1, 2, 3):
            b.phase = phase
            b.hp = b.max_hp * ({1:.9,2:.5,3:.2}[phase])
            b.state = "windup"; b.timer = 0
            s.pool.clear(); s.enemies = [b]
            b.update(s, 0.01)
            patterns.append(next((ev[3] for ev in s.events if ev[0] == "enemy_shoot"), None))
            s.events.clear()
        self.assertEqual(len(set(patterns)), 3)

    def test_seed_reproducibility_for_initial_combat(self):
        a = Sim(self.data, "soldier", seed=4242)
        b = Sim(self.data, "soldier", seed=4242)
        sig_a = [(e.d.id, round(e.x,2), round(e.y,2), round(e.cooldown,3), e.strafe) for e in a.enemies]
        sig_b = [(e.d.id, round(e.x,2), round(e.y,2), round(e.cooldown,3), e.strafe) for e in b.enemies]
        self.assertEqual(sig_a, sig_b)

if __name__ == "__main__":
    unittest.main()
