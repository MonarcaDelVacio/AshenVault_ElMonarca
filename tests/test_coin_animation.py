from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_renderer_loads_five_coin_frames_from_props_folder():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'self.coin_frames = []' in source
    assert 'prop_dir / f"moneda{frame_index}.png"' in source
    assert 'range(1, 6)' in source
    assert 'smoothscale(frame, (22, 22))' in source


def test_pickups_animate_and_keep_a_fallback_without_coin_pngs():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'int(max(0.0, t) * 8) % len(self.coin_frames)' in source
    assert 'if self.coin_frames:' in source
    assert 'pygame.draw.circle(screen, (255, 215, 60)' in source


def test_readme_documents_coin_frame_names_and_location():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/props/" in readme
    for filename in ("moneda1.png", "moneda2.png", "moneda3.png", "moneda4.png", "moneda5.png"):
        assert filename in readme
