# AshenVault — Phase 15 Cleanup

## Objective

Perform the cleanup pass after Phases 0–14 without changing gameplay behavior.

The cleanup rule is conservative:

**PRESERVE → VERIFY REFERENCES → REMOVE ONLY PROVEN-DEAD CODE**

No runtime subsystem, asset, compatibility path, test, or safety branch is removed merely because it is old-looking.

## Audit performed

Reviewed the repository tree and the current architecture around:

- application entry point and startup validation
- simulation/world/generation modules
- asset registry and bounds system
- renderer and renderer compatibility guards
- gameplay systems
- data validation
- Phase 13 integration coverage
- Phase 14 stress coverage
- test suite
- documentation
- safety branch `pre-refactor-baseline`

## Cleanup decisions

### 1. Safety branch retained

`pre-refactor-baseline` is intentionally retained.

It is explicitly documented as the rollback baseline for the architectural refactor. Deleting it would reduce reversibility without providing a runtime benefit.

### 2. Historical regression tests retained

Older regression tests such as `tests/test_v7_regressions.py` and phase-specific tests are retained.

They encode previously fixed behavior and therefore remain valuable regression coverage. Their historical names do not make them dead code.

### 3. Renderer compatibility guards retained

The renderer contains compatibility handling for previously observed argument-order and asset-loading failures. The corresponding regression test `tests/test_render_fx_argument_compat.py` proves that these guards are intentional.

They are not safe deletion candidates until the complete call graph and runtime behavior have been validated in the final manual pass.

### 4. World decoration collision fallback retained

`Arena.move(..., include_decorations=True)` still contains the legacy circular decoration-collision path, while gameplay simulation can disable it and use the alpha-derived collider path.

This fallback is retained because it is still part of the public world movement contract and removing it before a full caller audit would violate the refactor safety rules.

### 5. `game/gen.py` retained

Procedural generation is actively imported by `game/world.py` and supplies both dungeon-layout and room-generation functions. It is therefore active code, not a duplicate legacy module.

### 6. `check_intro.py` retained

`run.bat` explicitly invokes `check_intro.py` before launching the game. It is part of the startup validation path and must remain.

### 7. Generated/cache artifacts

The tracked repository tree contains no Python cache directories or generated test artifacts requiring cleanup. No source assets were removed.

## Result

No source deletion was justified during Phase 15.

This is intentional: the audit found compatibility and historical code that is still referenced or serves as regression protection. Removing it would increase regression risk rather than improve maintainability.

The repository is therefore cleaner in terms of documented ownership and deletion decisions, while preserving reversibility and runtime behavior.

## Verification status

- Repository/reference audit: complete.
- Candidate dependency review: complete.
- Safe source deletions: none identified.
- Gameplay changes: none.
- Asset changes: none.
- Automated pytest execution: not available in the current tool environment.
- Manual runtime verification: deferred to the final user test after Phase 16, as requested.

## Exit criteria

Phase 15 is complete when:

- no unreferenced critical module is removed accidentally;
- safety/regression coverage is preserved;
- cleanup decisions are documented;
- Phase 16 can begin without known cleanup regressions.
