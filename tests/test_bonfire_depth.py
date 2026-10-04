from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_bonfires_use_shared_y_depth_pass():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert '"bonfire"' in source
    assert 'actors.append((float(light["y"]), "bonfire", light))' in source
    assert 'elif kind=="bonfire":' in source
    assert 'def _draw_world_bonfire' in source


def test_bonfire_frames_are_the_six_prop_sprites():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'hoguera{frame_index}.png' in source
    assert 'for frame_index in range(1, 7)' in source
