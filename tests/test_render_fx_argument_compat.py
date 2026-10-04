from pathlib import Path


def test_draw_world_normalizes_swapped_fx_and_time_arguments():
    source = (Path(__file__).resolve().parents[1] / "game" / "render.py").read_text(encoding="utf-8")
    assert 'if not hasattr(fx, "particles") and hasattr(t, "particles"):' in source
    assert 'fx, t = t, float(fx)' in source


def test_draw_world_has_safe_fallback_for_invalid_fx_argument():
    source = (Path(__file__).resolve().parents[1] / "game" / "render.py").read_text(encoding="utf-8")
    assert 'fx = SimpleNamespace(particles=[], texts=[], shake=0.0, flash=0.0)' in source


def test_door_frame_loop_does_not_shadow_fx_effects_object():
    source = (Path(__file__).resolve().parents[1] / "game" / "render.py").read_text(encoding="utf-8")
    draw_world = source[source.index("def draw_world"):source.index("def draw_hud")]
    assert "for fx in (x,x+TILE-8):" not in draw_world
    assert "for frame_x in (x,x+TILE-8):" in draw_world
    assert "for q in fx.particles:" in draw_world
