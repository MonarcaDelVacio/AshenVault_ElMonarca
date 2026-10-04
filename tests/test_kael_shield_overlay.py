from pathlib import Path

from game.abilities import use_ability
from game.data import GameData
from game.sim import Sim

ROOT = Path(__file__).resolve().parents[1]


def test_kael_shield_ability_activates_dedicated_visual_timer():
    sim = Sim(GameData(), "soldier", seed=88)
    assert sim.player.ability_shield_fx == 0
    assert use_ability(sim)
    assert sim.player.ability_shield_fx > 0


def test_renderer_supports_optional_webp_shield_overlay_in_characters_folder():
    source = (ROOT / "game" / "render.py").read_text(encoding="utf-8")
    assert '"habilidadescudo.webp"' in source
    assert '"assets" / "characters"' in source
    assert "shield_ability_active" in source
    assert "shield_overlay.set_alpha" in source


def test_readme_documents_kael_shield_asset_path():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "assets/characters/habilidadescudo.webp" in readme


def test_kael_shield_ability_never_exceeds_upgrade_maximum():
    sim = Sim(GameData(), "soldier", seed=89)
    player = sim.player
    player.max_shield = 6
    player.shield = 5
    assert use_ability(sim)
    assert player.shield == 6
    assert player.shield <= player.max_shield


def test_kael_shield_ability_does_not_add_shield_when_already_full():
    sim = Sim(GameData(), "soldier", seed=90)
    player = sim.player
    player.max_shield = 6
    player.shield = 6
    assert use_ability(sim)
    assert player.shield == 6
