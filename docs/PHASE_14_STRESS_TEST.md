# Phase 14 — Stress Test

## Objective

Push the integrated AshenVault systems beyond ordinary gameplay density and
duration to expose:

- bounded-pool exhaustion;
- stale entity accumulation;
- non-finite simulation state;
- runaway event growth;
- procedural-generation instability;
- laser/combat pressure regressions;
- drone formation/collision instability.

No gameplay rules or balance values are changed by this phase.

## 14-A — Projectile pressure

Added repeated full-pressure tests against the existing 600-slot
`ProjectilePool`.

The test repeatedly fills the pool, advances simulation frames, and verifies
that:

- the pool remains exactly bounded;
- active projectiles never exceed capacity;
- the player remains valid;
- damage does not leak through the invulnerability guard.

## 14-B — High enemy density

A high-density room simulation is exercised for multiple seconds.

Every surviving enemy is checked for finite position, HP, knockback velocity,
and stable simulation state. This is intended to expose NaN/Inf propagation
from movement, targeting, collision, and combat.

## 14-C — Mira drone pressure

Multiple drones are updated for an extended period while exercising their
real steering/collision/lifetime system.

The test verifies that the number of drones remains bounded and that position,
HP and lifetime remain finite/valid.

## 14-D — Laser pressure

The laser is exercised against a large target population for an extended
period.

The test specifically checks the optimized laser path for finite charge,
angle and player energy while preserving the existing laser lifecycle.

## 14-E — Procedural generation repetition

Thirty independent dungeon seeds are generated consecutively.

Each generated dungeon must contain valid rooms and an arena with positive
dimensions. This catches state leaking between generation instances.

## 14-F — Long-running simulation

A simulated run is advanced for approximately one minute.

The test verifies:

- simulation time continues advancing;
- player position remains finite;
- player remains alive under the test's invulnerability guard;
- event history remains bounded at its existing 250-entry contract.

## Verification status

Implementation: COMPLETE.

Static inspection: COMPLETE.

Automated execution: not executed in the repository-connected environment,
because no local pytest executor is exposed here. No test result is being
fabricated.

Manual runtime verification: intentionally deferred according to the current
workflow request. Before Phase 15 cleanup, the user should run the game and
perform the combined integration/stress pass.

## Safety rule

If the eventual automated or manual stress pass exposes a regression, Phase 14
must be reopened and the underlying cause fixed before Phase 15.
