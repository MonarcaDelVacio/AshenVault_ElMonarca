from pathlib import Path

from game.gen import generate_room

ROOT = Path(__file__).resolve().parents[1]


def test_each_generated_room_declares_exactly_one_floor_surface():
    for seed in range(120):
        for room_type, biome in (("combat", "ruins"), ("combat", "forest"), ("shop", "forest"), ("boss", "final"), ("secret", "dungeon")):
            room = generate_room(seed, room_type, biome, ["N", "S"])
            assert room["floor_surface"] in {
                "arena", "hierba", "ladrillos", "ladrillosdepiedra", "madera", "roca", "rocanegra"
            }


def test_renderer_uses_room_floor_surface_instead_of_mixing_floor_families():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'floor_name = getattr(arena, "floor_surface", None)' in source
    assert 'floor_img = self.named_floor_images.get(floor_name)' in source
    assert 'named_floor_families=' not in source
    assert 'special_floor_families=' not in source


def test_window_uses_logical_canvas_and_proportional_presentation():
    source = (ROOT / "main.py").read_text(encoding="utf-8")
    assert 'pygame.display.set_mode((VIEW_W, VIEW_H), pygame.RESIZABLE' in source
    assert 'self.screen = pygame.Surface((VIEW_W, VIEW_H)).convert()' in source
    assert 'scale = min(ww / VIEW_W, wh / VIEW_H)' in source
    assert 'pygame.transform.smoothscale(self.screen, size)' in source
    assert 'self._logical_mouse_pos(ev.pos)' in source
