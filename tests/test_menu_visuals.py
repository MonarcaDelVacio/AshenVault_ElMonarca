from pathlib import Path

import game.menu_visuals as mv


def test_menu_asset_names_are_stable():
    assert mv.VIDEO_NAME == "FondoMenuPrincipal.webm"
    assert mv.LOGO_NAME == "AshenVault.png"
    assert mv.MENU_ASSET_DIR.name == "menu"


def test_menu_asset_readme_exists():
    readme = mv.MENU_ASSET_DIR / "README.txt"
    assert readme.exists()
    text = readme.read_text(encoding="utf-8")
    assert "FondoMenuPrincipal.webm" in text
    assert "AshenVault.png" in text


def test_missing_video_fails_soft(tmp_path, monkeypatch):
    asset_dir = tmp_path / "menu"
    asset_dir.mkdir()
    monkeypatch.setattr(mv, "MENU_ASSET_DIR", asset_dir)
    visuals = mv.MenuVisuals((96, 54))
    try:
        assert not visuals.video_available
        assert visuals.frame is None
    finally:
        visuals.close()


def test_missing_menu_assets_fail_soft(tmp_path, monkeypatch):
    monkeypatch.setattr(mv, "MENU_ASSET_DIR", tmp_path)
    visuals = mv.MenuVisuals((960, 540))
    try:
        assert not visuals.video_available
        assert visuals.logo is None
    finally:
        visuals.close()


def test_menu_background_api_exists_for_shared_menu_screens():
    assert hasattr(mv.MenuVisuals, "draw_background")
    assert hasattr(mv.MenuVisuals, "draw")
