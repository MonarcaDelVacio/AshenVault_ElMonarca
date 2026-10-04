import math, os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from game.data import GameData
from game.sim import Sim, Input
from game.world import TILE


def mk(seed=1):
    return Sim(GameData(), "soldier", seed=seed)


class T(unittest.TestCase):
    def test_wall_collision(self):
        s = mk(); i = Input(); p = s.player
        p.x, p.y = 2 * TILE, 5 * TILE
        i.aim_x, i.aim_y = p.x + 50, p.y
        i.move_x = -1
        for _ in range(120):
            s.enemies.clear(); s.wave_delay = 99
            s.update(i, 1 / 60)
        self.assertGreater(p.x, TILE)

    def test_diagonal_same_speed(self):
        s = mk(); i = Input(); p = s.player
        p.x, p.y = 12 * TILE, 9 * TILE
        i.aim_x, i.aim_y = p.x, p.y - 50
        i.move_x, i.move_y = 1, -1
        s.wave_delay = 99
        x0, y0 = p.x, p.y
        s.update(i, 1 / 60)
        self.assertAlmostEqual(math.hypot(p.x - x0, p.y - y0), p.speed / 60, places=2)

    def test_shield_then_hp(self):
        p = mk().player
        p.take_damage(2); self.assertEqual((p.shield, p.hp), (3, 6))
        p.invuln = 0; p.take_damage(5)
        self.assertEqual(p.shield, 0); self.assertEqual(p.hp, 4)

    def test_ammo_reload_energy(self):
        s = mk(); i = Input(); p = s.player; s.wave_delay = 99
        i.aim_x, i.aim_y = p.x + 100, p.y
        shots = 0
        for f in range(60 * 6):
            i.fire_pressed = f % 20 == 0
            a = p.weapon.ammo
            s.update(i, 1 / 60); i.clear_edges()
            if p.weapon.ammo < a:
                shots += 1
        self.assertGreaterEqual(shots, 12)
        self.assertLess(p.energy, p.max_energy)

    def test_pool_is_bounded(self):
        s = mk(); s.wave_delay = 99
        for _ in range(2000):
            s.spawn_projectile(0, 100, 100, 0.3, 500, 1, 3, 0.5, (255,) * 3, "physical", 0, 0, False)
            s.update(Input(), 1 / 60)
        self.assertEqual(len(s.pool.items), 600)

    def test_player_can_die_and_game_over(self):
        s = mk(); i = Input(); s.wave_delay = 0
        for _ in range(60 * 120):
            s.update(i, 1 / 60)
            if s.over:
                break
        self.assertTrue(s.over)

    def test_bounce(self):
        s = mk(); s.wave_delay = 99
        pr = s.spawn_projectile(0, 100, 100, math.pi, 300, 1, 3, 2, (255,) * 3, "physical", 0, 2, False)
        for _ in range(30):
            s.update(Input(), 1 / 60)
        self.assertTrue(pr.vx > 0)

    def test_enemy_reaches_player_around_pillar(self):
        s = mk(); i = Input(); s.wave_delay = 99
        p = s.player; p.invuln = 1e9
        p.x, p.y = 16 * TILE + 16, 4 * TILE + 16   # detrás del pilar central
        from game.enemies import Enemy
        e = Enemy(s.data.enemies["grunt"], 16 * TILE + 16, 14 * TILE + 16); e.spawn_delay = 0
        s.enemies.append(e)
        i.aim_x, i.aim_y = p.x, p.y - 10
        for _ in range(60 * 12):
            s.update(i, 1 / 60)
            if math.hypot(e.x - p.x, e.y - p.y) < 40: break
        self.assertLess(math.hypot(e.x - p.x, e.y - p.y), 45)

if __name__ == "__main__":
    unittest.main()
