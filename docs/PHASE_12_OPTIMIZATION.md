# Phase 12 — Optimization

## Objective

Improve CPU and allocation efficiency without changing gameplay behavior, asset selection, collision semantics, combat values, AI decisions, or visual presentation.

## 12-A — Hotspot audit

The runtime was audited around the main frame loop, projectile pool, enemy defensive scans, collision queries, and render asset loading. Existing object pools and cached flow-field updates were preserved rather than replaced.

### Identified hotspots

- Projectile simulation iterates the fixed projectile pool each frame. The existing pool is retained because it prevents per-shot object allocation and has a bounded cost.
- Enemy defensive AI consumes the per-frame player-projectile snapshot prepared by Sim.update(); the existing snapshot contract is preserved.
- Laser collision previously checked every enemy at every 6-pixel ray sample. This multiplied target checks by ray samples.
- Decoration collision remains based on the real PNG-derived collider provider when available; it was not simplified or replaced with rectangles.

## 12-B — Simulation optimization

The flow-field refresh remains throttled and only recomputes after the player changes tile and the refresh interval expires. No behavior change was introduced.

Laser actor intersection was moved out of the per-sample inner loop. Static world geometry keeps the previous 6-pixel sampling semantics, while actor intersections are solved analytically with _ray_circle_hit_distance() once per target.

## 12-C — Projectile / AI optimization

The existing 600-slot projectile pool and the defensive AI projectile snapshot were preserved. No pool ownership or projectile lifecycle contract was changed, avoiding regressions from direct active-state manipulation across combat systems.

## 12-D — Render / asset lookup audit

Render asset loading remains startup-oriented. The recent enemy-model contract validation is retained so optimization does not introduce silent missing-model states. No per-frame asset loading or sprite fallback behavior was removed.

## 12-E — Regression verification

Added tests/test_laser_raycast_optimization.py covering first ray/circle intersection, rejection of targets behind the ray or outside its radius, and tangent intersection.

The repository-connected toolset does not provide a local pytest execution environment, so these tests were inspected and committed but not claimed as executed here. Manual gameplay testing remains the authoritative runtime verification step.

## 12-F — Phase closure

Optimization work is intentionally conservative: preserve existing pools, collision providers, render contracts, and simulation behavior; optimize the laser target-query hotspot without changing its gameplay rules.

Status: COMPLETE.