from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_renderer_loads_destructible_prop_pngs_from_assets_props():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert 'self.asset_root / "props"' in source
    for filename in ("caja.png", "cajarota.png", "barriligneo.png", "barrilveneno.png", "barrilelectrico.png", "barrilroto.png"):
        assert filename in source

def test_readme_documents_prop_sprite_folder_and_fallback():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/props/" in readme
    assert "gráfico provisional" in readme
