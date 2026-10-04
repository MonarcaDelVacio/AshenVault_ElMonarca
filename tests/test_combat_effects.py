
import math
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from game.data import GameData
from game.sim import Sim, Input
from game.weapons import WeaponState


ROOT = Path(__file__).resolve().parents[1]


def test_effect_asset_contract_and_render_support():
    render = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    fx = (ROOT / "game" / "fx.py").read_text(encoding="utf-8")
    assert 'cortearmameleeframe' in render
    assert 'explosionframe' in render
    assert 'proyectiligneoframe' in render
    assert 'congelado.png' in render
    assert 'melee_slashes' in fx
    assert 'explosions' in fx


def test_ice_projectile_freezes_enemy():
    data = GameData()
    sim = Sim(data, "soldier", seed=7)
    sim.wave_delay = 99
    enemy = sim._new_enemy(data.enemies["grunt"], sim.player.x + 55, sim.player.y)
    enemy.spawn_delay = 0
    sim.enemies = [enemy]

    projectile = sim.spawn_projectile(
        0, sim.player.x, sim.player.y, 0.0, 300, 12, 4, 1.0,
        (130, 190, 255), "ice", 0, 0, False
    )
    for _ in range(30):
        sim.update(Input(), 1 / 60)
        if not enemy.alive or enemy.frozen > 0:
            break

    assert projectile is not None
    assert enemy.frozen > 0


def test_player_freeze_stops_movement():
    data = GameData()
    sim = Sim(data, "soldier", seed=8)
    p = sim.player
    p.frozen = 1.0
    inp = Input()
    inp.move_x = 1
    inp.aim_x, inp.aim_y = p.x + 100, p.y
    x0, y0 = p.x, p.y
    sim.update(inp, 1 / 60)
    assert (p.x, p.y) == (x0, y0)
    assert 0 < p.frozen < 1.0
