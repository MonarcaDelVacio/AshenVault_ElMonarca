# AshenVault — Architecture Map (Phase 1)

## Baseline

- Repository: `MonarcaDelVacio/AshenVault_ElMonarca`
- Default branch: `main`
- Baseline commit: `89edb3f5b1f261669ebcc83dd55b074ab01b01f3`
- Safety branch: `pre-refactor-baseline`
- Python runtime dependencies declared in `requirements.txt`: pygame-ce, PyAV, NumPy.
- Current test files: 41 Python files under `tests/`.
- Current data counts: 70 weapons, 29 enemies, 6 characters, 6 bosses.
- Large core modules: `main.py` (1558 lines), `game/sim.py` (1883), `game/render.py` (2968).
- Phase 0 runtime smoke test: user downloaded the current repository, launched the game, played for several minutes, and reported that it behaved correctly.

This document describes the current architecture before code movement. Phase 1 deliberately does not move gameplay code.

## 1. Runtime layers

The current runtime can be represented as:

```
main.App
  |
  +-- GameData -------------------- data/*.json
  +-- SaveData -------------------- persistent save/settings
  +-- Audio
  +-- Fx
  +-- MenuVisuals / IntroPlayer / UIAtlas
  +-- Renderer -------------------- pygame rendering + asset loading
  |
  +-- Sim ------------------------- gameplay simulation
        |
        +-- Dungeon / Arena / Room
        +-- Player / WeaponState
        +-- Enemy / Boss
        +-- ProjectilePool
        +-- Chest / Items / Statues
```

The intended separation is already partly present: simulation objects generally do not import pygame, while rendering owns most Pygame drawing and image loading. The main remaining problem is that several modules each own too many unrelated responsibilities.

## 2. `main.py` — application/state-machine layer

### Primary responsibility

`App` is the application shell and currently owns:

- Pygame initialization and window lifecycle.
- Boot splash.
- Fullscreen/window state.
- Input polling and key rebinding.
- High-level game state machine.
- Menu, hub, character selection, settings, pause, map, death, victory and score screens.
- Save/progression integration.
- Creation and lifetime of `GameData`, `Audio`, `Fx`, `Renderer`, `UIAtlas`, `IntroPlayer`, and `Sim`.
- Character portrait loading/cleanup.
- Menu rendering and score rendering.
- Logical-to-physical window presentation.

### Important finding

`App` is simultaneously an application controller, UI controller, screen renderer, input mapper, persistence coordinator and run lifecycle manager.

This is the first major architectural hotspot, but it should be split only after lower-level asset/rendering contracts are stabilized.

## 3. `game/sim.py` — gameplay orchestration layer

### Primary responsibility

`Sim` is the gameplay coordinator. It owns or coordinates:

- Current dungeon/room.
- Player.
- Enemies and bosses.
- Drones.
- Projectiles.
- Pickups/items.
- Chests.
- Shop offers.
- Statues.
- Room transitions.
- Enemy spawning.
- Prop/destructible interactions.
- Movement/collision delegation.
- Melee and ranged attacks.
- Damage/shield/status effects.
- Player and enemy lasers.
- Hazards.
- Pickups/coins.
- Run completion/death state.
- Per-frame simulation update.

### Important finding

`Sim` is not merely a simulation loop. It currently contains several distinct gameplay subsystems:

- room lifecycle
- spawning
- movement
- targeting
- combat
- projectiles
- status effects
- abilities
- loot
- shops
- interactions
- progression
- transitions

The class should remain the coordinator during refactoring. The future split should extract cohesive functions into modules without turning every function into a class.

## 4. `game/render.py` — rendering + asset interpretation layer

### Primary responsibility

`Renderer` currently owns:

- Pygame image loading and caching.
- Weapon sprites and weapon spritesheet parsing.
- Melee/ranged atlas parsing.
- Door frame parsing.
- Merchant spritesheet parsing.
- Generic component/spritesheet parsing.
- Enemy variants and visual transformations.
- Image trimming and fitting.
- Weapon grip/rotation calculations.
- World/floor/wall rendering.
- Architecture foreground/depth passes.
- Dynamic shadows.
- Lighting and line blocking.
- Bonfires/decorative lights.
- Player/enemy/drone rendering.
- Props/chests/portal rendering.
- Scene decoration rendering.
- Shop NPC rendering.
- Combat effects.
- World composition.
- Minimap.
- HUD.
- Interaction hints.
- Key display.

### Important finding

This is the largest architectural hotspot.

It combines two fundamentally different responsibilities:

1. **Asset interpretation/loading**
2. **Frame rendering**

This is directly related to the recent model-mapping problems with weapons, merchants and other spritesheets. The Asset Registry planned for Phase 2 should therefore be introduced before splitting the renderer into many files.

## 5. `game/world.py` — world model + collision/navigation

### Responsibilities

- Tile constants and geometry.
- `Door`.
- `Arena`.
- `Room`.
- `Dungeon`.
- Door access validation/corridor carving.
- Decoration collision data.
- Bonfire placement.
- Tile collision.
- Actor movement against solid geometry.
- Line of sight.
- Flow fields and best-step navigation.
- Dungeon room transitions.

### Important finding

The world module is relatively cohesive, but `Arena` currently combines:

- static geometry
- decoration interpretation
- decoration collision
- door validation
- movement
- LOS
- pathfinding

The geometry contract should eventually be separated from decoration/asset interpretation, but this is not the first extraction.

## 6. `game/gen.py` — procedural generation

Responsibilities:

- Dungeon layout generation.
- Main path generation.
- Floor selection.
- Decoration generation.
- Room floor masks.
- Room generation.
- Layout validation.

This is already a reasonably isolated subsystem. It should remain stable while architecture changes elsewhere.

A later phase should add a dedicated validation layer capable of running large seed batches.

## 7. Entity/gameplay modules

### `game/player.py`

Owns player state, status, damage, feedback and player update. It calls weapon/ability systems.

### `game/enemies.py`

Owns enemy state, update, defensive reaction, movement/chase and attack selection.

### `game/bosses.py`

Extends `Enemy` and implements boss-specific attack patterns/phases. This is a behavior-heavy module but still reasonably isolated.

### `game/weapons.py`

Owns `WeaponState` and weapon firing logic. It directly imports `TILE` from world and invokes simulation projectile spawning.

### `game/projectiles.py`

Small, cohesive projectile data/update pool.

### `game/abilities.py`

Contains ability execution helpers. It is small and should not be over-engineered.

### `game/items.py`, `game/chests.py`, `game/statues.py`

Small domain modules with relatively clear responsibilities.

## 8. Data layer

### `game/data.py`

Loads and validates JSON definitions.

Current validation covers references such as:

- weapons
- enemies
- characters
- bosses
- sprites/projectiles
- biome-related references

This module should eventually become the authoritative consumer of Asset Registry validation, rather than independently reconstructing asset knowledge.

## 9. Presentation/support modules

### `game/ui_atlas.py`

Owns UI atlas loading, cropping and drawing helpers. This is already a separate UI asset system.

### `game/menu_visuals.py`

Owns menu background/video/logo presentation.

### `game/intro.py`

Owns intro video/audio preparation and playback.

### `game/audio.py`

Owns music/effects playback and music-state synchronization.

### `game/fx.py`

Owns transient visual effects, particles, floating text and screen shake.

### `game/save.py`

Owns persistent progression/settings and XP/upgrade operations.

These modules are comparatively well bounded and should not be unnecessarily rewritten during the core refactor.

## 10. Current dependency direction

The important dependency relationships are:

```
main
 ├─ data
 ├─ save
 ├─ audio
 ├─ fx
 ├─ render
 │   ├─ world constants
 │   └─ ui_atlas
 ├─ menu_visuals
 ├─ ui_atlas
 ├─ intro
 └─ sim
     ├─ world
     ├─ player
     │   ├─ weapons
     │   └─ abilities
     ├─ weapons
     ├─ projectiles
     ├─ enemies
     ├─ bosses
     ├─ items
     ├─ chests
     └─ statues
```

A healthy target architecture should preserve this general direction:

- Domain/simulation modules must not depend on renderer.
- Asset loading must not depend on individual gameplay entities.
- UI should consume state rather than own gameplay state.
- Procedural generation should produce data, not render objects.
- Rendering should consume already-resolved asset regions/bounds instead of rediscovering them each frame.
- Validation should happen before runtime wherever possible.

## 11. Architectural hotspots and risk ranking

### Critical

**A. `Renderer` asset loading + rendering are coupled**

Risk: high.

Reason: spritesheets, alpha trimming, model detection, variants, weapon rotation and actual drawing are intertwined.

Plan: introduce Asset Registry before renderer extraction.

**B. `Sim` is a large coordinator with multiple gameplay domains**

Risk: high.

Reason: combat, AI, room lifecycle, loot and transitions can regress one another.

Plan: extract one subsystem at a time behind existing `Sim` methods.

**C. `App` owns all screens and application behavior**

Risk: high.

Reason: UI changes can accidentally affect simulation lifecycle.

Plan: extract screen/UI controllers only after simulation and renderer contracts are cleaner.

### Medium

**D. Decoration collision has multiple paths**

There is a legacy circular decoration collision path in `Arena.move`, while `Sim` also has its own world/decoration collision handling and the renderer contains collider helpers.

This is directly relevant to invisible hitbox bugs.

Plan: centralize collision bounds after asset bounds are centralized.

**E. World navigation and physical collision are mixed**

Flow fields, LOS, tile collision and actor movement are in the same module.

Plan: separate navigation from static world geometry later.

### Low

**F. Small support modules**

Audio, save, FX, chests, items and statues are not currently architectural blockers.

They should remain stable unless a concrete dependency requires change.

## 12. Asset system diagnosis

The current renderer contains multiple independent asset discovery mechanisms:

- alpha bounding box trimming
- ranged weapon atlas parsing
- melee weapon atlas parsing
- door frame extraction
- merchant sheet extraction
- component frame extraction
- generic sheet extraction
- enemy variant generation
- image fitting
- weapon grip anchors
- weapon rotation

This explains why asset mapping is a recurring source of regressions.

The future registry should resolve each asset once into a stable record:

```
AssetRecord
  asset_id
  category
  source_file
  surface/frame
  source_rect
  alpha_bounds
  visual_bounds
  collision_bounds
  pivot
  grip/anchor
  scale
  variant
```

The exact data structure will be determined in Phase 2 after auditing every existing loader.

## 13. Collision diagnosis

There are currently at least three conceptual collision sources:

1. Tile/door geometry in `Arena.solid_tile` / `box_hits`.
2. Decoration colliders in `Arena.decoration_colliders`.
3. Simulation-side prop/chest/decoration collision helpers.

The recent invisible-decoration regression test confirms that disabling the legacy decoration fallback is already an explicit compatibility concern.

Target architecture:

```
Asset bounds
    ↓
Collision profile
    ↓
World collision registry
    ↓
Sim movement/combat queries
```

The renderer must never be the authoritative owner of gameplay collision.

## 14. Testing architecture

The repository has 41 test files covering:

- simulation
- combat
- bosses
- abilities
- UI behavior
- fullscreen
- intro/music
- props/decorations
- depth sorting
- weapons
- inventory
- minimap/progression
- regression compatibility

The existing suite is therefore a valuable safety net.

The refactor should add tests around new contracts rather than replacing existing tests.

Required future testing categories:

- asset registry completeness
- spritesheet region uniqueness
- alpha/visual/collision bounds
- missing asset references
- duplicate mappings
- room generation invariants
- door accessibility
- collision invariants
- seed stress testing
- full run integration

## 15. Refactoring rules established from this analysis

1. Do not rewrite `Sim`, `Renderer` or `App` wholesale.
2. Keep public compatibility methods during migration.
3. Extract only one cohesive responsibility per step.
4. Add tests before deleting the old implementation.
5. Never let renderer-only calculations become gameplay authority.
6. Never make asset mapping depend on positional guesses scattered across gameplay code.
7. Keep `Sim` as the temporary compatibility facade while simulation modules are extracted.
8. Keep `Renderer` as the temporary compatibility facade while renderer modules are extracted.
9. Commit every stable migration step.
10. If a migration creates a behavioral regression, revert the migration rather than patching around an unclear architecture.

## 16. Phase 1 conclusion

The current project does not need a wholesale rewrite.

The existing architecture has a good foundation:

- simulation is already separated from Pygame
- data is JSON-driven
- generation is isolated
- entity systems are separated
- regression tests are extensive
- the project already has compatibility fallbacks

The main architectural debt is concentrated in three areas:

1. asset interpretation inside `Renderer`
2. multi-domain orchestration inside `Sim`
3. screen/UI orchestration inside `App`

Therefore the safest first structural change is **not** splitting `render.py` or `sim.py` directly.

The next phase is:

**Phase 2 — Asset Registry and centralized asset metadata.**

Phase 2 will first inventory every existing asset loader and mapping source, then introduce a compatibility registry without removing the existing loaders. Only after the registry is verified will consumers begin migrating to it.


## Phase 4 status

The repository already has the legacy `game/render.py` module. Python cannot
safely host a `game/render/` package beside that module without changing import
resolution, so the incremental split uses `game/rendering/` as the new package.

The first extracted component is `game/rendering/atlas_geometry.py`, a pure
helper for alpha-projection runs and regular grid-frame splitting. `game/render.py`
keeps compatibility aliases and delegates the regular grid-frame loader to the
new helper, so behavior and call sites remain unchanged.

Regression coverage now includes alpha-run behavior and row-major grid-frame
mapping, including transparent cells and invalid atlas dimensions.

The user completed the post-Phase-3/runtime smoke test after the renderer changes
and reported that the game continues to function correctly. No new crash, room
transition, door, spritesheet, merchant, ranged-weapon, or invisible-hitbox issue
was observed during that manual check.

The second extracted component is `game/rendering/sprite_geometry.py`, a pure
aspect-ratio sizing helper used by the legacy renderer. The renderer remains the
compatibility facade; only the sizing arithmetic moved, with no change to sprite
selection, trimming, scaling policy, or cache behavior.

The third extraction is `game/rendering/weapon_geometry.py`, which now owns the
existing melee grip-anchor policy and weapon maximum-dimension table. The legacy
Renderer methods remain as compatibility wrappers, so weapon selection and visual
placement behavior are unchanged. Regression tests cover the established values.

Next renderer extractions will continue to target small dependency-safe helpers
before moving any world-rendering or actor-rendering blocks.

The fourth extraction is `game/rendering/background_geometry.py`, which now owns the connected edge-background trimming algorithm used by door and melee atlas processing. `Renderer._trim_edge_background()` remains as a compatibility wrapper, preserving existing call sites and behavior. Regression coverage verifies that connected white background is removed while isolated internal white pixels are preserved.


The fifth Phase 4 extraction is `game/rendering/rotation_geometry.py`, which centralizes the existing 8-degree sprite rotation quantization and horizontal facing decision. Projectile, combat-animation, and death-sprite paths now use the helper while retaining the existing rotation cache keys and visual policy. Targeted tests cover the established buckets and facing behavior.


The sixth Phase 4 extraction is `game/rendering/atlas_background.py`, which centralizes the existing flat-color keying used by wall and cobblestone atlases. The renderer now delegates that operation without changing the configured RGB values or tolerances. Regression tests verify source immutability and selective transparency.


The seventh Phase 4 extraction is `game/rendering/animation_geometry.py`, which centralizes frame-index calculation for timed combat animations and projectile sheets. Existing durations and looping/clamping behavior are preserved; the renderer now delegates only the timing arithmetic. Targeted tests cover clamping, looping, empty animations, and invalid durations.


The eighth Phase 4 extraction is `game/rendering/wall_geometry.py`, which centralizes wall-edge/corner classification. `Renderer._wall_piece_key` remains as a compatibility wrapper so all existing world-rendering call sites keep their contract while the classification logic becomes independently testable.


## Phase 5 status — Simulation systems

The first Phase 5 extraction targets the most self-contained combat-state responsibility
inside `Sim`: status effects and defensive shield handling.

Added `game/systems/status_effects.py`, which now owns:
- freeze duration calculation and boss/miniboss caps
- freeze application/event emission
- fire/poison DoT state creation and refresh
- periodic DoT damage
- frontal shield absorption/drain and shield-break/block events

`Sim` remains the compatibility facade. Its existing private method names
(`_apply_freeze`, `_apply_dot`, `_update_dot_effects`, `_damage_shield`,
and `_freeze_duration`) now delegate to the extracted system, so existing
combat call sites remain unchanged.

Regression coverage was added in `tests/test_status_effects_system.py` for
the established freeze limits, DoT refresh/damage/expiry behavior, and status
application. No gameplay values were intentionally changed.
