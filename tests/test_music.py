import tempfile
from pathlib import Path
from types import SimpleNamespace

from game.audio import MUSIC_TRACKS, music_context, Audio


def test_music_context_menu_and_default():
    assert music_context(None) == "menu"
    assert music_context(SimpleNamespace(enemies=[])) == "default"


def test_music_context_battle_and_boss():
    normal = SimpleNamespace(is_boss=False, is_miniboss=False)
    boss = SimpleNamespace(is_boss=True, is_miniboss=False)
    mini = SimpleNamespace(is_boss=False, is_miniboss=True)
    assert music_context(SimpleNamespace(enemies=[normal])) == "battle"
    assert music_context(SimpleNamespace(enemies=[boss])) == "boss"
    assert music_context(SimpleNamespace(enemies=[mini])) == "boss"


def test_music_file_names_are_configured():
    assert MUSIC_TRACKS == {
        "menu": "MenuPrincipal",
        "default": "MusicaDefault no batlle",
        "battle": "Batallas (Sin Jefes)",
        "boss": "BossFight",
    }


def test_music_file_lookup_prefers_ogg():
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "BossFight.mp3").write_bytes(b"x")
        (root / "BossFight.ogg").write_bytes(b"x")
        a = Audio(music_dir=root)
        assert a._find_music_file("boss").suffix == ".ogg"
