# Bounds and Collision Notes — Phase 3

## First regression fixed

The decoration renderer and its PNG-based collision provider previously had
two independent size tables. Statue collision masks used a maximum size of
640 while the visible statue renderer used 510. This could leave a physical
area outside the visible model and present it as an invisible hitbox.

Phase 3 now uses `game/assets/bounds.py` as the single source for decoration
maximum visual size. Both decoration rendering and the PNG overlap provider
use the same value.

## Remaining collision sources

- Arena tile and door geometry.
- Arena legacy circular decoration colliders.
- Renderer PNG/mask decoration overlap used by Sim during gameplay.
- Prop collision supplied by the renderer.
- Chest interaction/collision helpers.

The legacy Arena decoration fallback remains intact for headless tests and
compatibility. It is not removed until the authoritative bounds migration is
validated.

## Next work

Next Phase 3 step is to make alpha/visual/collision/interaction bounds an
explicit shared representation rather than deriving them independently in
multiple renderer methods. Regression coverage will target missing models,
transparent margins, duplicate colliders, and collider/model scale drift.
