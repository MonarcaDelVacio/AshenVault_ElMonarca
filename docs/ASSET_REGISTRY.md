# Asset Registry — Phase 2

## Purpose

Phase 2 introduces a centralized asset identity layer without replacing the
existing Pygame loaders. The current renderer remains behavior-compatible while
the registry records stable identities and declarative provenance.

The registry deliberately does not import Pygame. This keeps validation and
unit tests independent from the graphical subsystem.

## Current registry model

game/assets/registry.py provides:

- AssetRecord: asset_id, category, source_file, frame_index, source_rect,
  alpha_bounds, visual_bounds, collision_bounds, pivot, anchor, scale,
  variant, metadata, and optional runtime handle.
- AssetRegistry: deterministic registration/resolution, duplicate-ID protection,
  duplicate atlas-region detection, required-asset validation, declarative
  inventory creation from GameData, and register_runtime_frame() as the
  compatibility adapter for future loader migration.

## Declarative inventory

GameData now creates data.asset_registry after its existing validation.
The registry currently indexes:

- weapons
- weapon projectile references
- enemies
- enemy projectile references
- bosses
- playable characters

This is intentionally an inventory layer first. It does not alter weapon
selection, enemy spawning, rendering, collision, or sprite mapping yet.

## Existing renderer asset loaders

The current renderer still owns these discovery/mapping mechanisms:

1. Individual asset loading via pygame.image.load.
2. Fixed character 8-frame horizontal sheets.
3. Individual props and architecture sprites.
4. Fixed bonfire/coin/portal frame conventions.
5. Fixed wall atlas regions.
6. merchant1.png / merchant2.png regular 4x4 sheets.
7. merchant3.png regular 6x4 sheet handling.
8. Door 2-frame open/closed sheets.
9. Known-grid sheets such as the 4x2 fireball atlas and 4x4 flying enemy sheet.
10. Alpha-projection based generic sheets.
11. Connected-component based free-form atlases.
12. Enemy variant transformations.
13. Ranged weapon atlas discovery.
14. Individual weapon/projectile asset loading.
15. Effect sheets and ability atlases.
16. Alpha trimming and image fitting.

The existing loaders remain the source of runtime surfaces during Phase 2.

## Important mapping decisions preserved

### Merchant sheets

merchant3.png is treated as a 6x4 regular spritesheet. It is not passed
through connected-component discovery first. This preserves row/column identity
and prevents internal disconnected parts of a merchant model from becoming
separate models.

### Weapon atlases

The current renderer keeps the ranged atlas compatibility path and does not
re-enable the retired melee-atlas mapping merely by introducing the registry.
Individual melee PNGs remain individual assets.

The registry is therefore not allowed to silently change the current weapon
mapping.

### Bounds

Alpha/visual/collision bounds are fields in the registry, but existing
collision behavior is not migrated in this phase. Phase 3 will make those
bounds authoritative and will specifically address invisible hitboxes and
duplicate decoration colliders.

## Migration strategy

1. Register declarative identities. Done.
2. Register runtime sheet frames beside existing loaders. Done for the generic/grid/component/merchant/door/ranged loaders.
3. Compare registry regions against current loader outputs. Pending Phase 3 validation.
4. Make renderer resolve assets through the registry.
5. Only then remove duplicate loader-specific metadata.

No loader is deleted until the compatibility path and regression tests prove
that its mapping is equivalent.

## Phase 2 non-goals

This phase does not:

- change sprite appearance;
- change sprite scale;
- change weapon balance;
- change enemy behavior;
- change room generation;
- change collision geometry;
- replace the merchant/weapon atlas algorithms;
- remove legacy loaders;
- make collision bounds authoritative.

Those changes belong to later phases.
