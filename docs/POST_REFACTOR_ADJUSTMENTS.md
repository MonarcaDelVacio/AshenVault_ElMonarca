# Post-Refactor Gameplay Adjustments

This pass is incremental and preserves the completed Phase 0-16 architecture.

Implemented:
- Corrected flying-enemy spritesheet mapping to 3 columns x 4 rows.
- Added Kamehameha-style energy spheres during laser charge for player and boss lasers.
- Boss phases now consume a complete health bar independently; each phase restores full phase HP and uses its own HUD color.
- Removed the boss-local health bar above boss sprites.
- Extended boss shockwaves to the full room while retaining line-of-sight protection from walls, props and decorations.
- Added distinct boss identity mechanics: tank barriers, mage repositioning/teleporting and colossus charges, while preserving existing summoner/commander/regent patterns.
- Merchants now wander only a small distance and show a coin speech bubble.
- Shop items display their concrete effect under the item name.
- Intro music volume is independent from the Settings music slider.
- Increased mouse-sensitivity impact while preserving the 0.25-2.00 range.
- Reduced the compact minimap panel footprint.
- Compact minimap icons are now reserved for boss and miniboss rooms.
- Player shadows are positioned beneath the character model and use transparency.
- Magic weapons now use durability/USOS instead of magazines or reloads.
- Character starting weapons are unique by name and visual model; the medic starting pistol was separated from the soldier pistol and its output was rebalanced.
- The new assets/walls/walls.png atlas is now the room-border source, tinted per biome; obsolete border PNGs were removed.
- Generated room doors are now 3 blocks wide, centered on odd-sized rooms, matching the requested 1.5-block extension on each side.
- Score EXP screen now draws the used character spritesheet after the EXP panel so it is not hidden underneath the panel.

Regression coverage added in tests/test_post_refactor_adjustments.py.

Runtime validation is still required after this implementation pass. No automated test run is claimed here unless a compatible local execution environment is available.
