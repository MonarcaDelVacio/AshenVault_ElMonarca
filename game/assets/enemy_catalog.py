"""Central catalog of enemy visual model identifiers.

The renderer owns the actual loader specifications; this module owns the stable
identifiers accepted by data validation so validation does not duplicate a
second hard-coded list inside GameData.
"""

ENEMY_SPRITE_KEYS = frozenset({
    "esbirromago",
    "gargola",
    "minigolem",
    "nomuerto",
    "nomuerto2",
    "monodehielo",
    "minotaurogigante",
    "skeleton",
    "ghost",
    "goblin",
    "orc",
    "demon",
    "slime",
    "dead_knight",
    "small_demon_assassin",
    "small_demon_ranged",
    "small_demon_melee",
    "mage2",
    "ogro",
    "new_flyer",
})
