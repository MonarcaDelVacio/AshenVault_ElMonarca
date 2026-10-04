import unittest
from game.sim import Sim, Input

class RookAbilityTests(unittest.TestCase):
    def test_rook_impact_damages_nearby_enemies(self):
        sim = Sim(__import__("game.data", fromlist=["GameData"]).GameData(), "vanguard", seed=0)
        sim.enemies = []
        # Spawn two enemies manually through the normal room spawn helper.
        sim._spawn_room_enemies()
        self.assertTrue(sim.enemies)
        target = sim.enemies[0]
        target.x, target.y = sim.player.x + 20, sim.player.y
        hp_before = target.hp
        inp = Input()
        inp.ability_pressed = True
        sim.update(inp, 1/60)
        self.assertLess(target.hp, hp_before)
        self.assertEqual(sim.stats["abilities"], 1)
        self.assertGreater(sim.player.ability_cd, 0)

    def test_rook_ability_can_kill_without_crashing(self):
        sim = Sim(__import__("game.data", fromlist=["GameData"]).GameData(), "vanguard", seed=1)
        sim.enemies = []
        sim._spawn_room_enemies()
        for e in sim.enemies:
            e.x, e.y = sim.player.x + 15, sim.player.y
            e.hp = 1
        inp = Input(); inp.ability_pressed = True
        sim.update(inp, 1/60)
        self.assertEqual(sim.stats["abilities"], 1)
        self.assertTrue(all(not e.alive for e in sim.enemies))

if __name__ == "__main__":
    unittest.main()
