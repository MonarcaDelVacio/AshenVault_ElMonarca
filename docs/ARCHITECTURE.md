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


The second Phase 5 extraction targets the coin pickup/magnet simulation path. Added `game/systems/pickups.py`, which owns the existing two-block coin attraction, movement toward the player, collection radius, coin/stat updates, and pickup event emission. `Sim._update_pickups()` remains as a compatibility facade and delegates to the extracted system. Focused regression tests cover attraction boundaries, collection, and the existing `coin_radius` upgrade behavior. No pickup speed, range, reward, or event semantics were intentionally changed.


The third Phase 5 extraction targets environmental hazards and expanding wave attacks. Added `game/systems/hazards.py`, which owns the existing prop-fade cleanup, hazard particle simulation, periodic player/enemy/drone damage, fire/poison DoT application, electric status application, and radial wave propagation/LOS handling. `Sim._update_hazards()` remains as a compatibility facade, so existing update-loop call sites and gameplay state remain unchanged. Focused regression tests cover fire damage/DoT, electric drone damage, single-hit wave behavior, and freeze-wave behavior. No hazard timing, damage, range, particle, or wave semantics were intentionally changed.


The fourth Phase 5 extraction targets chest and room-reward generation. Added `game/systems/rewards.py`, which owns chest spawning/opening and the existing room reward rolls for items, keys, and weapon drops. `Sim._spawn_chest()`, `_open_chest()`, and `_drop_room_reward()` remain compatibility facades. Focused tests cover chest creation, weapon reward generation, and one-time opening. No reward probabilities, inventory rules, item selection, or event semantics were intentionally changed.

The fifth Phase 5 extraction targets player interaction and floor-item inventory handling. Added `game/systems/interaction.py`, which owns the existing portal/statue/chest/shop interaction order plus weapon pickup/merge/swap logic, healing, energy, ammunition, and generic item pickup behavior. `Sim._try_interact()` remains a compatibility facade, preserving the original call site and event/return semantics. Focused regression tests cover healing, energy, ammunition, and adding a weapon to inventory. No pickup range, inventory capacity, weapon merge, replacement, or reward values were intentionally changed.

Phase 5 is now complete. The extracted simulation systems are deliberately small and dependency-safe; `Sim` remains the gameplay facade while the systems package owns isolated state transitions. Room transitions, combat orchestration, enemy lifecycle, and the main update ordering remain in `Sim` because extracting them at this stage would create higher coupling and regression risk.

## Phase 6 status — Combat systems

Phase 6 has begun with the core combat simulation extraction. Added `game/systems/combat.py`, which now owns the existing projectile spawning/update/hit pipeline, explosive impacts, melee/fist hit detection, destructible-prop damage, and player/enemy laser lifecycle and beam collision.

The legacy `Sim` methods remain compatibility facades, so the existing player/enemy/weapons call sites keep their contracts. Combat behavior, damage formulas, projectile pooling, status application, shields, melee knockback, laser travel, and event emission were preserved rather than redesigned.

Regression coverage was added in `tests/test_combat_system.py` for projectile spawning, melee hit detection, projectile damage/consumption, and laser energy/beam state. Further Phase 6 work should focus on auditing the weapon-fire and ability layers and their interaction with this extracted combat core before declaring the phase complete.


## Phase 6 — Combat Systems (enemy attack layer)

The combat refactor now also separates enemy attack execution into `game/systems/enemy_combat.py`. The extracted layer owns melee contact/effects, prop damage from enemy swings, projectile pattern generation, enemy weapon/projectile visual selection, explosive attack metadata, and combat events. `game/enemies.py` remains the AI/state owner and exposes `_attack()` as a compatibility facade.

The player weapon layer (`game/weapons.py`) and character ability layer (`game/abilities.py`) remain intentionally separate for the next audit slice because they own input/cooldown/ammunition and character-specific orchestration respectively. No balance changes were introduced by this extraction.


### Phase 6 — Mira drone combat layer

Mira's drone lifecycle has been extracted to `game/systems/drones.py`. The extracted layer owns drone spawning, safe positioning, collision/path checks, formation steering, projectile avoidance, combat positioning, ranged fire, damage and destruction. `Sim` remains the world-state owner and exposes compatibility facades for the existing callers.

The weapon firing path in `game/weapons.py` and active-character ability dispatcher in `game/abilities.py` are already standalone modules with relatively low coupling, so they are being audited rather than mechanically split again. This avoids creating indirection where no architectural boundary is gained.


### Phase 6 — ability/weapon audit follow-up

The post-extraction audit verified that Mira retains the requested 20-second ability cooldown, and completed the drone behavior contract: drones now have a finite lifetime, fire three-shot bursts with a short intra-burst interval, and preserve the existing durability cap so a single hit cannot immediately delete a healthy drone. Character upgrades continue to control drone count, damage, attack cadence, and durability.

Rook's shockwave ability now explicitly enables confusion alongside stun; the existing hazard system owns the status application and event emission, so no duplicate effect implementation was introduced.

The remaining Phase 6 work is final regression/integration auditing of player weapon input, reload/ammunition semantics, special projectiles, and laser edge cases before moving to Movement/AI.


## Phase 7 status — Movement / AI

Phase 7 has started with the first cohesive AI extraction: `game/systems/enemy_movement.py` now owns the existing enemy steering primitives, including collision-aware step movement, angular escape when an enemy is blocked, and chase behavior using direct line-of-sight or the room flow-field. `game/enemies.py` retains `_step()` and `_chase()` compatibility facades, so the existing brain/state machine remains unchanged.

Regression tests cover obstacle escape and direct line-of-sight chasing. No movement speed, pathfinding, detection range, attack range, or AI decision probabilities were intentionally changed.

The next Movement/AI slice should audit target selection, confusion behavior, dodge/defensive reactions, flying movement, and flow-field edge cases before changing procedural generation or room lifecycle code.

Phase 7 movement hardening now also covers enemy congestion and physical clearance. Chase separation uses soft radial spacing before enemies overlap, with stronger lateral separation when a group is already compressed. Blocked steering candidates are rejected when the physical obstacle sweep reports no clear segment. Flow-field steps are evaluated against the enemy's collision radius, including recovery from disconnected/INF tiles, so a geometrically valid tile is not selected when the actor cannot actually occupy it. Flying enemies retain bounded movement. Door geometry remains generation-owned: active openings are exactly two perimeter blocks, while internal access corridors remain wider to provide actor clearance. Focused regression coverage was added for pre-overlap separation, blocked escape steering, flying bounds, defensive cover, and flow-step clearance.


This slice also corrected enemy separation in the extracted chase helper and completed the confusion contract: confused enemies retreat/disorient instead of initiating attacks, while stun/freeze remain immobilizing statuses. A regression test now covers separation with another enemy present.

## Phase 8 status — Procedural generation

Phase 8 begins with a non-invasive validation layer in `game/generation_validation.py`. It validates dungeon-layout invariants (start/boss presence, orthogonal main path, connectivity and duplicate rooms) and room-generation invariants (grid dimensions, valid door anchors, exact perimeter openings, player spawn and required room metadata) without loading the renderer.

Regression coverage in `tests/test_generation_validation.py` audits a seed batch across the main room types and explicitly rejects an extra perimeter opening. The generator itself remains unchanged in this slice; the goal is to establish an executable contract before modifying procedural generation behavior.

The next Phase 8 slice expanded this contract into large deterministic seed batches. Room validation now covers all 16 combinations of active door sides, verifies every door has a floor route to the player spawn, checks duplicate/out-of-floor spawns and rejects perimeter openings that do not correspond to a door. Dungeon-level validation also checks start/final room types, the six-boss structure and spacing between special/no-enemy rooms and minibosses.

The audit is intentionally validation-only at this stage: the procedural generator was not changed because no concrete generation defect was established by static inspection. The expanded tests cover 128 layout seeds, 64 seeds across all supported room types and door combinations, and 64 constructed dungeons. These tests have been added but have not been executed in the available GitHub environment.


### Phase 8/9 continuation — generation spacing, physical clearance and room topology
- Boss placement now rejects cardinally adjacent boss rooms while preserving the six-boss structure and the minimum path-index spacing between zones.
- Generation validation now treats only FLOOR (0) as walkable; pillar/torch-pillar cells remain solid, matching Arena.solid_tile().
- Room validation audits physical decoration clearance against the shared decoration collision radii for player/item/enemy spawns and immediate door volume.
- Room topology validation begins Phase 9: every dungeon-room adjacency must have symmetric doors, and every non-adjacent direction must remain closed/nonexistent.
- Regression coverage was added for boss spatial spacing, pillar solidity, room-door topology and decoration/spawn clearance.
- These tests are prepared but not runtime-executed through the available GitHub integration.


### Phase 9 — Room system, first slice
- Dungeon room transitions now require both sides of a connection to exist: the current room must have an open door and the destination room must expose the matching opposite door.
- This is a defensive runtime check in addition to the procedural topology validator; malformed room graphs cannot silently produce one-way transitions.
- Regression coverage includes symmetric room-door topology and a transition that deliberately removes the destination door.
- The next Phase 9 slices should cover room lifecycle/clear-state invariants, door locking/unlocking, and persistent room state across transitions.


### Phase 9 — Room lifecycle and persistence
- Room-local chest state is now retained when leaving and re-entering a cleared room.
- Shop offers are initialized once per room and then reused, so purchased/sold offers do not reroll when revisiting the same shop.
- Existing room item/pickup state continues to be owned by the Room object and rebound by Sim on entry.
- Combat rooms retain their cleared/enemies_spawned/doors_locked state, preventing defeated rooms from spawning a second wave when revisited.
- A persistent-room-state regression was planned, but the repository test-file write was blocked by the integration safety layer; the runtime code change itself was committed and should be manually smoke-tested.
