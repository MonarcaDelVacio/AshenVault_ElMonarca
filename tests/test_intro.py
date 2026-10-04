from pathlib import Path


def test_intro_asset_contract():
    root = Path(__file__).resolve().parents[1]
    intro_dir = root / "assets" / "intro"
    assert (intro_dir / "README.txt").is_file()
    assert "intro.mp4" in (intro_dir / "README.txt").read_text(encoding="utf-8")


def test_intro_module_has_required_flow():
    root = Path(__file__).resolve().parents[1]
    source = (root / "game" / "intro.py").read_text(encoding="utf-8")
    assert "assets" in source and "intro" in source and "intro.mp4" in source
    assert "pygame.mixer.music.play" in source
    assert "def skip" in source
    assert "self.frame_index / max(1.0, self.fps)" in source
    assert "duración declarada en el contenedor" in source


def test_boot_splash_is_separate_from_game_window():
    root = Path(__file__).resolve().parents[1]
    main_source = (root / "main.py").read_text(encoding="utf-8")
    assert "def _show_boot_splash" in main_source
    assert "NOFRAME" in main_source
    assert "pygame.display.quit()" in main_source
    assert "pygame.display.init()" in main_source
    assert "self._show_boot_splash()" in main_source


def test_intro_video_is_bundled_and_splash_is_larger_and_longer():
    root = Path(__file__).resolve().parents[1]
    assert (root / "assets" / "intro" / "intro.mp4").is_file()
    source = (root / "main.py").read_text(encoding="utf-8")
    assert "duration = 3.0" in source
    assert "max_w = int(splash_w * 0.50)" in source
    assert "_make_splash_transparent" in source


def test_intro_declares_numpy_dependency_for_pyav_frame_conversion():
    root = Path(__file__).resolve().parents[1]
    req = (root / "requirements.txt").read_text(encoding="utf-8")
    assert "numpy" in req.lower()
    source = (root / "game" / "intro.py").read_text(encoding="utf-8")
    assert "import numpy as np" in source


def test_intro_has_preflight_decoder_check():
    root = Path(__file__).resolve().parents[1]
    checker = root / "check_intro.py"
    assert checker.is_file()
    source = checker.read_text(encoding="utf-8")
    assert "av.open" in source
    assert "to_ndarray" in source
    run = (root / "run.bat").read_text(encoding="utf-8")
    build = (root / "build_exe.bat").read_text(encoding="utf-8")
    assert "check_intro.py" in run
    assert "check_intro.py" in build
