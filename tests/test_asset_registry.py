from game.assets.registry import AssetRecord, AssetRegistry


def test_registry_resolves_stable_asset_ids():
    registry = AssetRegistry()
    record = registry.register_simple(
        "weapon:test",
        "weapon",
        source_file="assets/weapons/test.png",
        frame_index=3,
    )

    assert registry.require("weapon:test") == record
    assert registry.by_category("weapon") == (record,)


def test_registry_rejects_conflicting_duplicate_ids():
    registry = AssetRegistry()
    registry.register_simple("enemy:test", "enemy", source_file="a.png")

    try:
        registry.register_simple("enemy:test", "enemy", source_file="b.png")
    except ValueError as exc:
        assert "Asset duplicado" in str(exc)
    else:
        raise AssertionError("Se esperaba un conflicto de asset_id")


def test_registry_detects_duplicate_atlas_regions():
    registry = AssetRegistry()
    registry.register(
        AssetRecord(
            "weapon:a", "weapon", "atlas.png", frame_index=0,
            source_rect=(0, 0, 20, 20),
        )
    )
    registry.register(
        AssetRecord(
            "weapon:b", "weapon", "atlas.png", frame_index=1,
            source_rect=(0, 0, 20, 20),
        )
    )

    errors = registry.validate_unique_source_regions()
    assert len(errors) == 1
    assert "weapon:a" in errors[0]
    assert "weapon:b" in errors[0]


def test_registry_accepts_adjacent_atlas_regions():
    registry = AssetRegistry()
    registry.register(
        AssetRecord(
            "weapon:a", "weapon", "atlas.png", frame_index=0,
            source_rect=(0, 0, 20, 20),
        )
    )
    registry.register(
        AssetRecord(
            "weapon:b", "weapon", "atlas.png", frame_index=1,
            source_rect=(20, 0, 20, 20),
        )
    )

    assert registry.validate_unique_source_regions() == []


def test_registry_reports_missing_required_assets():
    registry = AssetRegistry()
    registry.register_simple("weapon:test", "weapon")

    assert registry.validate_required(["weapon:test", "weapon:missing"]) == ["weapon:missing"]


def test_registry_from_game_data_uses_declarative_sprite_sources():
    class Definition:
        def __init__(self, **values):
            self.__dict__.update(values)

    class Data:
        weapons = {
            "blade": Definition(
                weapon_sprite="assets/weapons/melee/blade.png",
                projectile_sprite="assets/projectiles/p.png",
            )
        }
        enemies = {
            "grunt": Definition(sprite_set="skeleton"),
        }
        bosses = {
            "warden": Definition(sprite_set="gargola"),
        }
        characters = {
            "soldier": Definition(start_weapon="blade"),
        }

    registry = AssetRegistry.from_game_data(Data())

    assert registry.require("weapon:blade").source_file.endswith("blade.png")
    assert registry.require("weapon-projectile:blade").category == "projectile"
    assert registry.require("enemy:grunt").metadata["sprite_set"] == "skeleton"
    assert registry.require("boss:warden").category == "boss"
    assert registry.require("character:soldier").metadata["start_weapon"] == "blade"


def test_registry_runtime_frame_preserves_sheet_region_metadata():
    registry = AssetRegistry()
    frame = object()
    record = registry.register_runtime_frame(
        "frame:sheet:assets/test.png:2",
        "sheet",
        source_file="assets/test.png",
        frame_index=2,
        source_rect=(40, 0, 20, 20),
        alpha_bounds=(3, 2, 12, 16),
        handle=frame,
    )

    assert record.source_rect == (40, 0, 20, 20)
    assert record.alpha_bounds == (3, 2, 12, 16)
    assert record.visual_bounds == (3, 2, 12, 16)
    assert record.handle is frame
