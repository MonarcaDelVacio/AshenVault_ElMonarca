"""Regression coverage for the post-refactor gameplay adjustments."""
from pathlib import Path
import random
from types import SimpleNamespace

from game.bosses import Boss
from game.data import GameData
from game.gen import ROOM_W, ROOM_H, generate_room
from game.weapons import WeaponState


ROOT = Path(__file__).resolve().parents[1]


def test_flyer_uses_the_correct_three_by_four_grid():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert "flyer_frames = self._load_grid_frames(flyer_path, 3, 4)" in source


def test_new_wall_atlas_is_in_the_wall_asset_folder():
    assert (ROOT / "assets" / "walls" / "walls.png").is_file()
    assert not (ROOT / "assets" / "walls.png").exists()


def test_centered_three_tile_doors_use_the_room_axis():
    data = generate_room(14071, "combat", "ruins", {"N", "S", "W", "E"})
    cx, cy = ROOM_W // 2, ROOM_H // 2
    assert data["doors"] == [(cx, 0), (cx, ROOM_H - 1), (0, cy), (ROOM_W - 1, cy)]
    assert all(data["grid"][0][x] == 0 for x in (cx - 1, cx, cx + 1))
    assert all(data["grid"][ROOM_H - 1][x] == 0 for x in (cx - 1, cx, cx + 1))
    assert all(data["grid"][y][0] == 0 for y in (cy - 1, cy, cy + 1))
    assert all(data["grid"][y][ROOM_W - 1] == 0 for y in (cy - 1, cy, cy + 1))


def test_magic_weapons_have_uses_and_do_not_reload():
    weapon = SimpleNamespace(
        id="test_magic",
        class_="magic",
        **{"class": "magic"},
        magazine=18,
        durability=24,
        max_magazines=5,
    )
    state = WeaponState(weapon)
    assert state.durability == 24
    assert state.max_durability == 24
    assert state.start_reload() is False


def test_character_default_weapons_are_unique_and_balanced():
    data = GameData()
    defaults = [data.weapons[c.start_weapon] for c in data.characters.values()]
    assert len(defaults) == len({w.id for w in defaults})
    assert len(defaults) == len({w.name for w in defaults})
    sprites = [getattr(w, "weapon_sprite", None) for w in defaults]
    assert all(sprites)
    assert len(sprites) == len(set(sprites))
    assert all(float(w.damage) > 0 for w in defaults)
    assert data.weapons["iria_dart_pistol"].damage >= 7
    assert data.weapons["frost_orb"].durability >= 30
    assert data.weapons["arc_blade"].durability >= 30


def test_boss_phase_resets_to_a_full_bar():
    data = GameData()
    boss = Boss(data.bosses["warden"], 100.0, 100.0, random.Random(3), difficulty=1)
    phase_hp = boss.max_hp
    boss.hurt(phase_hp + 1.0, 0.0)
    assert boss.alive
    assert boss.phase == 2
    assert boss.hp == boss.max_hp == phase_hp
    boss.phase_transition_lock = 0.0
    boss.hurt(phase_hp + 1.0, 0.0)
    assert boss.alive
    assert boss.phase == 3
    assert boss.hp == boss.max_hp == phase_hp


def test_score_character_sprite_is_drawn_after_xp_panel():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    panel_pos = source.index("panel=pygame.Rect(145,105,670,365)")
    sprite_pos = source.index("score_frames = self.r.player_walk_frames.get(self.char_id, [])")
    assert sprite_pos > panel_pos


def test_intro_volume_is_independent_from_music_setting():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert "IntroPlayer((VIEW_W, VIEW_H), music_volume=1.0)" in source


def test_minimap_only_declares_boss_and_miniboss_icons():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    section = source[source.index("def draw_minimap"):source.index("def draw_hud")]
    assert 'room.room_type=="boss"' in section
    assert 'room.room_type=="miniboss"' in section
    assert 'room.room_type=="shop"' not in section
    assert 'room.room_type=="treasure"' not in section
    assert 'room.room_type=="healing"' not in section
