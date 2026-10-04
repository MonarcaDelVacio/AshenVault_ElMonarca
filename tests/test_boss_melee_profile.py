import math
from types import SimpleNamespace

from game.bosses import Boss


def test_boss_melee_profile_has_safe_hit_radius_fallback():
    d = SimpleNamespace(
        id="test_boss", hp=100, radius=28, speed=60, detect_range=1200,
        attack_range=900, preferred_distance=250, windup=.1, recover=.1,
        cooldown=1.0, damage=3, color=(255, 120, 90), phases=[{}],
        boss_style="commander", ranged_melee_profile=True,
        ranged_melee_threshold=155,
    )
    boss = Boss(d, 100, 100)

    class Player:
        x, y, radius = 110, 100, 10
        alive = True
        def take_damage(self, dmg): return True

    class Sim:
        player = Player()
        def emit(self, *args): pass
        def spawn_projectile(self, *args): return None
        def on_player_hit(self, *args): pass
        def _apply_freeze(self, *args): pass

    # The original regression crashed here because the boss Defn lacked hit_radius.
    boss._attack(Sim(), math.hypot(10, 0))
