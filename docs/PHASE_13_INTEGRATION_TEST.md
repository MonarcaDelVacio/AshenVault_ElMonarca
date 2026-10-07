# Phase 13 — Integration Test

## Objective

Verify that the major AshenVault subsystems operate together through their real
public/runtime contracts without replacing any existing implementation.

Phase 13 is an integration gate between the completed architecture/data/optimization
work and the later stress/cleanup phases.

## 13-A — Integration surface audit

The current integration path is:

1. JSON data -> `GameData` -> data-graph validation.
2. `GameData` -> `AssetRegistry`.
3. `GameData` -> procedural `Dungeon` / `Arena`.
4. `Dungeon` / `Arena` -> `Sim`.
5. `Sim` -> player, enemies, bosses, projectiles, rooms, rewards, hazards,
   abilities, drones and combat systems.
6. `GameData` + pygame -> `Renderer`.
7. `main.App` imports the complete application composition without starting
   the interactive loop during import.

No subsystem was rewritten for this phase.

## 13-B — Headless application and renderer smoke coverage

Added `tests/test_phase13_integration.py`.

Coverage includes:

- importing `main.py` without launching the game loop;
- constructing `GameData` and `Renderer` together;
- loading the validated enemy/boss model catalog;
- loading playable-character animation frames;
- preserving the declared minimum arsenal size.

The renderer test uses SDL's dummy video/audio drivers so it can run without a
desktop session.

## 13-C — Simulation integration coverage

The integration suite constructs every playable character and advances each
through real `Sim.update()` frames while exercising movement/aim/fire input.

It also verifies:

- the player remains associated with the current room/arena;
- the bounded projectile pool remains intact;
- simulation time advances;
- player state remains valid.

## 13-D — Combat and ability integration

The suite crosses the real subsystem boundaries for:

- character ability activation;
- Mira drone spawning and update;
- weapon definition -> `WeaponState`;
- laser activation after its charge threshold;
- continuous laser energy consumption;
- laser shutdown when firing is released;
- projectile pool activity under load.

These tests assert integration contracts rather than duplicating individual
unit-test internals.

## 13-E — Progression / portal integration

The suite also validates the final-room lifecycle:

- final boss room can be completed;
- final portal is created;
- portal interaction increases dungeon difficulty;
- the next dungeon starts in the expected start room;
- portal state is cleared after transition.

## Verification status

Implementation: COMPLETE.

Static inspection: COMPLETE.

Automated execution: the repository-connected environment used for this phase
does not provide a local pytest executor, so the new tests are committed but
are not falsely reported as executed here.

Manual runtime verification: REQUIRED before Phase 13 can be declared fully
closed. The manual pass must cover startup/menu, a normal combat room, several
enemy types, a boss, projectile-heavy combat, laser combat, Mira drones and a
final-room portal transition.

## Safety rule

No gameplay, asset, balance, AI, rendering or generation behavior was changed
solely to satisfy these tests. If an integration test exposes a real
regression, the regression must be fixed before Phase 14 begins.
