from pathlib import Path
import ast


ROOT = Path(__file__).resolve().parents[1]


def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


def test_phase16_required_architecture_files_exist():
    required = [
        "main.py",
        "game/data.py",
        "game/data_validation.py",
        "game/assets/registry.py",
        "game/assets/bounds.py",
        "game/render.py",
        "game/sim.py",
        "game/world.py",
        "game/gen.py",
        "game/systems/combat.py",
        "game/systems/drones.py",
        "tests/test_phase13_integration.py",
        "tests/test_phase14_stress.py",
        "docs/PHASE_15_CLEANUP.md",
    ]
    assert all((ROOT / path).is_file() for path in required)


def test_phase16_simulation_remains_renderer_independent():
    tree = ast.parse(read("game/sim.py"))
    imports = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom)
    ]
    imported = []
    for node in imports:
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        else:
            imported.append(node.module or "")
    assert not any(name == "pygame" or name.startswith("pygame.") for name in imported)


def test_phase16_renderer_keeps_runtime_model_validation():
    source = read("game/render.py")
    assert "class Renderer" in source
    assert "def draw_world" in source
    assert "def draw_hud" in source
    assert "Modelos de enemigos no cargados" in source


def test_phase16_data_validation_is_wired_into_game_data():
    source = read("game/data.py")
    assert "validate_data_graph" in source


def test_phase16_phase_13_and_14_coverage_are_present():
    integration = read("tests/test_phase13_integration.py")
    stress = read("tests/test_phase14_stress.py")
    assert "test_final_room_completion_reaches_next_dungeon" in integration
    assert "test_projectile_pool_survives_repeated_full_pressure" in stress
    assert "test_long_simulation_does_not_accumulate_unbounded_event_state" in stress


def test_phase16_no_tracked_python_cache_directories():
    for path in ROOT.rglob("__pycache__"):
        assert not path.is_dir(), f"tracked/source tree contains cache directory: {path}"
